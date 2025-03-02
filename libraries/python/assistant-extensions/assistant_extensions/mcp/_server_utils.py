import asyncio
import logging
import pathlib
import time
from asyncio import CancelledError, create_task
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, AsyncIterator, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import pydantic
from mcp import ClientSession, types
from mcp.client.session import SamplingFnT
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.context import RequestContext

from ._model import (
    MCPErrorHandler,
    MCPSamplingMessageHandler,
    MCPServerConfig,
    MCPSession,
    MCPToolsConfigModel,
)

# Use our patched SSE client instead of the original one
from .patched_sse import sse_client

logger = logging.getLogger(__name__)


def get_env_dict(server_config: MCPServerConfig) -> dict[str, str] | None:
    """Get the environment variables as a dictionary."""
    env_dict = {env.key: env.value for env in server_config.env}
    if len(env_dict) == 0:
        return None
    return env_dict


@asynccontextmanager
async def connect_to_mcp_server(
    server_config: MCPServerConfig,
    sampling_callback: Optional[SamplingFnT] = None,
) -> AsyncIterator[Optional[ClientSession]]:
    """Connect to a single MCP server defined in the config."""
    if server_config.command.startswith("http"):
        async with connect_to_mcp_server_sse(
            server_config, sampling_callback
        ) as client_session:
            yield client_session
    else:
        async with connect_to_mcp_server_stdio(
            server_config, sampling_callback
        ) as client_session:
            yield client_session


def list_roots_callback_for(server_config: MCPServerConfig):
    """
    Provides a callback to return the list of "roots" for a given server config.
    """

    def root_to_uri(root: str) -> pydantic.AnyUrl | pydantic.FileUrl:
        # if the root is a URL, return it as is
        if "://" in root:
            return pydantic.AnyUrl(root)

        # otherwise, assume it is a file path, and convert to a file URL
        path = pathlib.Path(root)
        match path:
            case pathlib.WindowsPath():
                return pydantic.FileUrl(f"file:///{path.as_posix()}")
            case _:
                return pydantic.FileUrl(f"file://{path.as_posix()}")

    async def cb(
        context: RequestContext[ClientSession, Any],
    ) -> types.ListRootsResult | types.ErrorData:
        roots = server_config.roots
        return types.ListRootsResult(
            roots=[
                # mcp sdk is currently typed to FileUrl, but the MCP spec allows for any URL
                # the mcp sdk doesn't call any of the FileUrl methods, so this is safe for now
                types.Root(uri=root_to_uri(root))  # type: ignore
                for root in roots
            ]
        )

    return cb


@asynccontextmanager
async def connect_to_mcp_server_stdio(
    server_config: MCPServerConfig,
    sampling_callback: Optional[SamplingFnT] = None,
) -> AsyncIterator[Optional[ClientSession]]:
    """Connect to a single MCP server defined in the config."""

    server_params = StdioServerParameters(
        command=server_config.command,
        args=server_config.args,
        env=get_env_dict(server_config),
    )
    logger.debug(
        f"Attempting to connect to {server_config.key} with command: {server_config.command} {' '.join(server_config.args)}"
    )
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(
                read_stream,
                write_stream,
                list_roots_callback=list_roots_callback_for(server_config),
                sampling_callback=sampling_callback,
            ) as client_session:
                await client_session.initialize()
                yield client_session  # Yield the session for use

    except Exception as e:
        logger.exception(f"Error connecting to {server_config.key}: {e}")
        raise


def add_params_to_url(url: str, params: dict[str, str]) -> str:
    """Add parameters to a URL."""
    parsed_url = urlparse(url)
    query_params = dict()
    if parsed_url.query:
        for key, value_list in parse_qs(parsed_url.query).items():
            if value_list:
                query_params[key] = value_list[0]
    query_params.update(params)
    url_parts = list(parsed_url)
    url_parts[4] = urlencode(query_params)  # 4 is the query part
    return urlunparse(url_parts)


@asynccontextmanager
async def connect_to_mcp_server_sse(
    server_config: MCPServerConfig,
    sampling_callback: Optional[SamplingFnT] = None,
) -> AsyncIterator[Optional[ClientSession]]:
    """Connect to a single MCP server defined in the config using SSE transport."""

    start_time = time.time()
    connection_id = f"{server_config.key}_{int(start_time)}"
    logger.info(
        f"[MCP-CONN:{connection_id}] Starting connection attempt to {server_config.key}"
    )

    # Start a background task to monitor connection status
    # This will help us understand if the connection is stalling
    heartbeat_task = None

    async def connection_heartbeat():
        heartbeat_count = 0
        try:
            while True:
                heartbeat_count += 1
                elapsed = time.time() - start_time
                logger.debug(
                    f"[MCP-CONN:{connection_id}] Heartbeat #{heartbeat_count} at {elapsed:.2f}s"
                )
                await asyncio.sleep(
                    30
                )  # Send heartbeat every 30 seconds - check connection health
        except CancelledError:
            elapsed = time.time() - start_time
            logger.debug(
                f"[MCP-CONN:{connection_id}] Heartbeat task cancelled after {elapsed:.2f}s"
            )
            raise
        except Exception as e:
            logger.error(f"[MCP-CONN:{connection_id}] Heartbeat task error: {e}")

    try:
        headers = get_env_dict(server_config)
        url = server_config.command

        # Process args to add URL parameters
        # All args are joined into a single comma-separated list
        if server_config.args and len(server_config.args) >= 1:
            # Join all args with commas
            args_value = ",".join(server_config.args)

            # Add to URL with 'args' as the parameter name
            url_params = {"args": args_value}
            url = add_params_to_url(url, url_params)
            logger.debug(
                f"[MCP-CONN:{connection_id}] Added parameter args={args_value} to URL"
            )

        # Define timeout values and log them
        connect_timeout = 60 * 5  # 5 minutes
        read_timeout = 60 * 15  # 15 minutes
        logger.info(
            f"[MCP-CONN:{connection_id}] Attempting to connect to {server_config.key} with SSE transport: {url} "
            f"(connect_timeout={connect_timeout}s, read_timeout={read_timeout}s)"
        )

        # Start heartbeat task
        heartbeat_task = create_task(connection_heartbeat())

        # FIXME: Bumping sse_read_timeout to 15 minutes and timeout to 5 minutes, but this should be configurable
        async with sse_client(
            url=url,
            headers=headers,
            timeout=connect_timeout,
            sse_read_timeout=read_timeout,
        ) as (
            read_stream,
            write_stream,
        ):
            connection_time = time.time() - start_time
            logger.info(
                f"[MCP-CONN:{connection_id}] SSE client connected after {connection_time:.2f}s"
            )

            async with ClientSession(
                read_stream,
                write_stream,
                list_roots_callback=list_roots_callback_for(server_config),
                sampling_callback=sampling_callback,
            ) as client_session:
                session_creation_time = time.time() - start_time
                logger.info(
                    f"[MCP-CONN:{connection_id}] Client session created after {session_creation_time:.2f}s"
                )

                await client_session.initialize()
                init_time = time.time() - start_time
                logger.info(
                    f"[MCP-CONN:{connection_id}] Session initialized after {init_time:.2f}s"
                )

                yield client_session  # Yield the session for use

                end_use_time = time.time() - start_time
                logger.info(
                    f"[MCP-CONN:{connection_id}] Session use completed after {end_use_time:.2f}s"
                )

    except ExceptionGroup as e:
        logger.exception(
            f"[MCP-CONN:{connection_id}] TaskGroup failed in SSE client for {server_config.key}: {e}"
        )
        for sub in e.exceptions:
            logger.error(
                f"[MCP-CONN:{connection_id}] Sub-exception: {server_config.key}: {sub}"
            )
        # If there's exactly one underlying exception, re-raise it
        if len(e.exceptions) == 1:
            raise e.exceptions[0]
        else:
            raise
    except CancelledError as e:
        logger.exception(
            f"[MCP-CONN:{connection_id}] Task was cancelled in SSE client for {server_config.key}: {e}"
        )
        raise
    except RuntimeError as e:
        logger.exception(
            f"[MCP-CONN:{connection_id}] Runtime error in SSE client for {server_config.key}: {e}"
        )
        raise
    except Exception as e:
        logger.exception(
            f"[MCP-CONN:{connection_id}] Error connecting to {server_config.key}: {e}"
        )
        raise
    finally:
        # Ensure the heartbeat task is cancelled when the connection exits
        if heartbeat_task is not None and not heartbeat_task.done():
            logger.debug(f"[MCP-CONN:{connection_id}] Cancelling heartbeat task")
            heartbeat_task.cancel()


async def refresh_mcp_sessions(mcp_sessions: list[MCPSession]) -> list[MCPSession]:
    """
    Check each MCP session for connectivity. If a session is marked as disconnected,
    attempt to reconnect it using reconnect_mcp_session.
    """
    refresh_id = int(time.time())
    logger.info(
        f"[MCP-REFRESH:{refresh_id}] Refreshing {len(mcp_sessions)} MCP sessions"
    )

    active_sessions = []
    for idx, session in enumerate(mcp_sessions):
        session_key = session.config.key if session else "unknown"

        # Add a delay between session checks to avoid overwhelming the system
        if idx > 0:
            await asyncio.sleep(0.1)

        # Log session state
        logger.debug(
            f"[MCP-REFRESH:{refresh_id}] Checking session {idx + 1}/{len(mcp_sessions)}: "
            f"{session_key}, connected: {session.is_connected}"
        )

        # Perform a health check on the session
        start_time = time.time()
        if not session.is_connected:
            logger.info(
                f"[MCP-REFRESH:{refresh_id}] Session {session_key} is disconnected. "
                f"Attempting to reconnect..."
            )
            new_session = await reconnect_mcp_session(session.config)
            if new_session:
                active_sessions.append(new_session)
                logger.info(
                    f"[MCP-REFRESH:{refresh_id}] Successfully reconnected to {session_key} "
                    f"in {time.time() - start_time:.2f}s"
                )
            else:
                logger.error(
                    f"[MCP-REFRESH:{refresh_id}] Failed to reconnect MCP server {session_key} "
                    f"after {time.time() - start_time:.2f}s"
                )
        else:
            # Even if the session says it's connected, do a basic health check if possible
            active_sessions.append(session)
            logger.debug(
                f"[MCP-REFRESH:{refresh_id}] Session {session_key} is marked as connected"
            )

    logger.info(
        f"[MCP-REFRESH:{refresh_id}] Session refresh complete. "
        f"{len(active_sessions)}/{len(mcp_sessions)} sessions active"
    )
    return active_sessions


async def reconnect_mcp_session(server_config: MCPServerConfig) -> MCPSession | None:
    """
    Attempt to reconnect to the MCP server using the provided configuration.
    Returns a new MCPSession if successful, or None otherwise.
    This version relies directly on the existing connection context manager
    to avoid interfering with cancel scopes.
    """
    try:
        async with connect_to_mcp_server(server_config) as client_session:
            if client_session is None:
                logger.error(
                    f"Reconnection returned no client session for {server_config.key}"
                )
                return None

            new_session = MCPSession(
                config=server_config, client_session=client_session
            )
            await new_session.initialize()
            new_session.is_connected = True
            logger.info(f"Successfully reconnected to MCP server {server_config.key}")
            return new_session
    except Exception as e:
        logger.exception(f"Error reconnecting MCP server {server_config.key}: {e}")
        return None


async def establish_mcp_sessions(
    tools_config: MCPToolsConfigModel,
    stack: AsyncExitStack,
    error_handler: Optional[MCPErrorHandler] = None,
    sampling_handler: Optional[MCPSamplingMessageHandler] = None,
) -> List[MCPSession]:
    mcp_sessions: List[MCPSession] = []
    for server_config in tools_config.mcp_servers:
        if not server_config.enabled:
            logger.debug(f"Skipping disabled server: {server_config.key}")
            continue
        try:
            client_session: ClientSession | None = await stack.enter_async_context(
                connect_to_mcp_server(
                    server_config,
                    sampling_callback=sampling_handler,
                )
            )
        except Exception as e:
            # Log a cleaner error message for this specific server
            logger.error(f"Failed to connect to MCP server {server_config.key}: {e}")
            # Also notify the user about this server failure here.
            if error_handler:
                await error_handler(server_config, e)
            # Abort the connection attempt for the servers to avoid only partial server connections
            # This could lead to assistant creatively trying to use the other tools to compensate
            # for the missing tools, which can sometimes be very problematic.
            return []

        if client_session:
            mcp_session = MCPSession(
                config=server_config, client_session=client_session
            )
            await mcp_session.initialize()
            mcp_sessions.append(mcp_session)
        else:
            logger.warning(f"Could not establish session with {server_config.key}")
    return mcp_sessions


def get_mcp_server_prompts(tools_config: MCPToolsConfigModel) -> List[str]:
    """Get the prompts for all MCP servers."""
    return [
        mcp_server.prompt
        for mcp_server in tools_config.mcp_servers
        if mcp_server.prompt
    ]
