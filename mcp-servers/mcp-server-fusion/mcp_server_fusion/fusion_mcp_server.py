import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import Optional, Any
import threading
import socket
import time

from .vendor.mcp.server.fastmcp import FastMCP
from .vendor.anyio import BrokenResourceError
from .mcp_tools import (
    Fusion3DOperationTools,
    FusionGeometryTools,
    FusionPatternTools,
    FusionSketchTools,
)


class FusionMCPServer:
    def __init__(self, port: int):
        self.port = port
        self.running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.shutdown_event = threading.Event()
        self.server_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)

        # Initialize MCP server with custom lifespan handler
        self.mcp = FastMCP(name="Fusion MCP Server", log_level="DEBUG", lifespan=self.server_lifespan)
        self.mcp.settings.port = port

        # Register tools
        self._register_tools()

    @asynccontextmanager
    async def server_lifespan(self, app: FastMCP) -> Any:
        """Custom lifespan manager for the FastMCP server

        This handles proper setup and cleanup of resources when the server starts and stops
        """
        self.logger.info(f"Starting Fusion MCP Server on port {self.port}")

        # Setup code runs before server starts
        try:
            # Yield control back to the server - it will run until context exits
            yield {"status": "running"}

        finally:
            # Cleanup code runs when server is shutting down
            self.logger.info("Server lifespan context exiting, performing cleanup")
            self.running = False

            # Any specific cleanup logic can go here
            # The socket will be automatically closed by FastMCP

    def wait_for_port_available(self, timeout=30):
        """Wait for the port to become available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try to bind to the port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("0.0.0.0", self.port))
                    return True
            except OSError:
                time.sleep(0.5)
        return False

    def _register_tools(self):
        """Register all tool handlers"""
        try:
            Fusion3DOperationTools().register_tools(self.mcp)
            FusionGeometryTools().register_tools(self.mcp)
            FusionPatternTools().register_tools(self.mcp)
            FusionSketchTools().register_tools(self.mcp)
        except Exception as e:
            self.logger.error(f"Error registering tools: {e}")
            raise

    def start(self):
        """Start the server in the current thread"""
        if self.running:
            return

        try:
            # Wait for port to become available
            if not self.wait_for_port_available():
                raise RuntimeError(f"Port {self.port} did not become available")

            # Create new event loop
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Set up exception handler
            def handle_exception(loop, context):
                exception = context.get("exception")
                if isinstance(exception, (asyncio.CancelledError, GeneratorExit)):
                    return
                self.logger.error(f"Caught unhandled exception: {context}")
                if not self.shutdown_event.is_set():
                    self.shutdown()

            self.loop.set_exception_handler(handle_exception)

            # Run the server
            try:
                self.running = True
                self.logger.info(f"Starting FastMCP SSE server on port {self.port}")
                # Using run() directly which handles the asyncio event loop internally
                # This simplifies our code compared to the previous implementation
                self.loop.run_until_complete(self.mcp.run_sse_async())
            except BrokenResourceError:
                self.logger.warning("Client disconnected during SSE, ignoring BrokenResourceError")
            except KeyboardInterrupt:
                pass
            except Exception as e:
                if not self.shutdown_event.is_set():  # Don't log during normal shutdown
                    self.logger.error(f"Error in server loop: {e}")
            finally:
                self._cleanup()

        except Exception as e:
            self.logger.error(f"Error starting server: {e}")
            raise

    def _cleanup(self):
        """Clean up resources"""
        try:
            if self.loop and self.loop.is_running():
                # Cancel all tasks
                tasks = [t for t in asyncio.all_tasks(self.loop) if not t.done()]

                if tasks:
                    # Cancel tasks
                    for task in tasks:
                        task.cancel()

                    # Wait for tasks to finish with timeout
                    try:
                        self.loop.run_until_complete(asyncio.wait(tasks, timeout=5))
                    except Exception as e:
                        self.logger.error(f"Error waiting for tasks to cancel: {e}")

            # Close the loop
            if self.loop and not self.loop.is_closed():
                self.loop.close()

            self.running = False

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def shutdown(self):
        """Shutdown the server safely"""
        if not self.running:
            return

        try:
            self.logger.info("Shutting down server...")
            self.shutdown_event.set()
            self.running = False

            if self.loop and self.loop.is_running():

                def stop_loop():
                    # Stop the loop
                    self.loop.stop()
                    # Cancel any pending tasks
                    for task in asyncio.all_tasks(self.loop):
                        task.cancel()

                self.loop.call_soon_threadsafe(stop_loop)

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            raise
