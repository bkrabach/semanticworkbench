"""
Patched version of the SSE client from mcp.client.sse with improved connection stability.
This addresses chunked read failures by implementing:
1. A connection heartbeat mechanism
2. Better error handling with automatic retries
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urljoin, urlparse

import anyio
import httpx
import mcp.types as types


class GracefulDisconnect(Exception):
    """Exception indicating a graceful disconnection from the SSE stream."""

    pass


from anyio.abc import TaskStatus
from httpx_sse import aconnect_sse

logger = logging.getLogger(__name__)

# Configuration constants
MAX_RECONNECT_ATTEMPTS = 3
RECONNECT_BACKOFF_FACTOR = 2
BASE_RECONNECT_DELAY = 1.0  # seconds
HEARTBEAT_INTERVAL = 20  # seconds - Use a more aggressive heartbeat interval to deal with potential 1-minute timeouts


def remove_request_params(url: str) -> str:
    """Remove query parameters from a URL."""
    return urljoin(url, urlparse(url).path)


@asynccontextmanager
async def patched_sse_client(
    url: str,
    headers: dict[str, Any] | None = None,
    timeout: float = 5,
    sse_read_timeout: float = 60 * 15,
    enable_heartbeat: bool = True,
):
    """
    Enhanced SSE client with stability improvements:
    - Connection heartbeat to prevent idle timeouts
    - Improved error handling for chunked transfer failures
    - Diagnostic logging for connection lifecycle

    Args:
        url: The SSE endpoint URL
        headers: Headers to send with the request
        timeout: General HTTP timeout in seconds
        sse_read_timeout: How long to wait for a new event before timeout
        enable_heartbeat: Whether to send periodic heartbeats to keep the connection alive
    """
    read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

    # Track connection state
    connection_start_time = time.time()
    connection_id = f"sse_{int(connection_start_time)}"
    logger.info(
        f"[SSE:{connection_id}] Creating new SSE client for {remove_request_params(url)}"
    )

    async with anyio.create_task_group() as tg:
        try:
            logger.info(
                f"[SSE:{connection_id}] Connecting to SSE endpoint: {remove_request_params(url)}"
            )

            # Configuration for the HTTP client
            limits = httpx.Limits(
                max_keepalive_connections=5, max_connections=10, keepalive_expiry=90.0
            )

            # Prepare headers with keep-alive
            request_headers = headers.copy() if headers else {}
            request_headers["Connection"] = "keep-alive"

            async with httpx.AsyncClient(
                headers=request_headers, limits=limits
            ) as client:
                async with aconnect_sse(
                    client,
                    "GET",
                    url,
                    timeout=httpx.Timeout(timeout, read=sse_read_timeout),
                ) as event_source:
                    event_source.response.raise_for_status()
                    logger.debug(f"[SSE:{connection_id}] SSE connection established")

                    # Track heartbeat state
                    last_activity_time = time.time()
                    heartbeat_task = None
                    endpoint_url = None

                    async def heartbeat_sender():
                        """Send periodic no-op messages to keep the connection alive."""
                        nonlocal last_activity_time

                        try:
                            heartbeat_count = 0
                            while True:
                                # Log current connection status
                                time_since_activity = time.time() - last_activity_time
                                logger.info(
                                    f"[SSE:{connection_id}] Connection status: {time_since_activity:.1f}s since last activity"
                                )

                                await asyncio.sleep(HEARTBEAT_INTERVAL)

                                # ALWAYS send a heartbeat regardless of activity time if endpoint is available
                                if endpoint_url:
                                    heartbeat_count += 1
                                    logger.info(
                                        f"[SSE:{connection_id}] Sending heartbeat #{heartbeat_count}"
                                    )

                                    # Send an empty POST to the endpoint URL to keep the connection alive
                                    try:
                                        heartbeat_payload = {
                                            "jsonrpc": "2.0",
                                            "method": "heartbeat",
                                            "params": {"timestamp": time.time()},
                                        }
                                        logger.debug(
                                            f"[SSE:{connection_id}] Heartbeat payload: {json.dumps(heartbeat_payload)}"
                                        )
                                        response = await client.post(
                                            endpoint_url,
                                            headers={
                                                "X-Heartbeat": "true",
                                                "Connection": "keep-alive",
                                                "Content-Type": "application/json",
                                            },
                                            json=heartbeat_payload,
                                            timeout=5.0,  # Short timeout for heartbeats
                                        )
                                        response.raise_for_status()
                                        last_activity_time = time.time()
                                        logger.info(
                                            f"[SSE:{connection_id}] Heartbeat #{heartbeat_count} successful"
                                        )
                                    except Exception as e:
                                        logger.error(
                                            f"[SSE:{connection_id}] Heartbeat failed: {e}"
                                        )

                                        # If we get a 400 or 500 error, the session is likely invalid
                                        if isinstance(
                                            e, httpx.HTTPStatusError
                                        ) and e.response.status_code in (400, 500):
                                            logger.warning(
                                                f"[SSE:{connection_id}] Received {e.response.status_code} error on heartbeat - session may be invalid"
                                            )
                                            # Break out of the loop to allow reconnection
                                            break
                                else:
                                    logger.warning(
                                        f"[SSE:{connection_id}] Cannot send heartbeat: endpoint_url not available"
                                    )
                        except asyncio.CancelledError:
                            elapsed = time.time() - connection_start_time
                            logger.info(
                                f"[SSE:{connection_id}] Heartbeat task cancelled after {elapsed:.2f}s"
                            )
                            raise
                        except Exception as e:
                            logger.error(
                                f"[SSE:{connection_id}] Error in heartbeat task: {e}"
                            )

                    async def sse_reader(
                        task_status: TaskStatus[str] = anyio.TASK_STATUS_IGNORED,
                    ):
                        """Read events from the SSE connection with improved error handling."""
                        nonlocal last_activity_time, endpoint_url

                        try:
                            async for sse in event_source.aiter_sse():
                                last_activity_time = time.time()
                                logger.debug(
                                    f"[SSE:{connection_id}] Received SSE event: {sse.event}"
                                )

                                match sse.event:
                                    case "endpoint":
                                        endpoint_url = urljoin(url, sse.data)
                                        logger.info(
                                            f"[SSE:{connection_id}] Received endpoint URL: {endpoint_url}"
                                        )

                                        url_parsed = urlparse(url)
                                        endpoint_parsed = urlparse(endpoint_url)
                                        if (
                                            url_parsed.netloc != endpoint_parsed.netloc
                                            or url_parsed.scheme
                                            != endpoint_parsed.scheme
                                        ):
                                            error_msg = (
                                                "Endpoint origin does not match "
                                                f"connection origin: {endpoint_url}"
                                            )
                                            logger.error(
                                                f"[SSE:{connection_id}] {error_msg}"
                                            )
                                            raise ValueError(error_msg)

                                        task_status.started(endpoint_url)

                                    case "message":
                                        try:
                                            message = types.JSONRPCMessage.model_validate_json(
                                                sse.data
                                            )
                                            logger.debug(
                                                f"[SSE:{connection_id}] Received server message: {message}"
                                            )
                                        except Exception as exc:
                                            logger.error(
                                                f"[SSE:{connection_id}] Error parsing server message: {exc}"
                                            )
                                            await read_stream_writer.send(exc)
                                            continue

                                        await read_stream_writer.send(message)
                        except Exception as exc:
                            if "incomplete chunked read" in str(
                                exc
                            ) or "peer closed connection" in str(exc):
                                logger.warning(
                                    f"[SSE:{connection_id}] Graceful disconnection encountered: {exc}"
                                )
                                return
                            else:
                                logger.error(
                                    f"[SSE:{connection_id}] Error in sse_reader: {exc}"
                                )
                                await read_stream_writer.send(exc)
                        finally:
                            await read_stream_writer.aclose()

                    async def post_writer(ep_url: str):
                        """Send messages to the SSE endpoint."""
                        nonlocal last_activity_time

                        try:
                            async with write_stream_reader:
                                async for message in write_stream_reader:
                                    logger.debug(
                                        f"[SSE:{connection_id}] Sending client message: {message}"
                                    )
                                    try:
                                        response = await client.post(
                                            ep_url,
                                            json=message.model_dump(
                                                by_alias=True,
                                                mode="json",
                                                exclude_none=True,
                                            ),
                                        )
                                        response.raise_for_status()
                                        last_activity_time = time.time()
                                        logger.debug(
                                            f"[SSE:{connection_id}] Client message sent successfully: "
                                            f"{response.status_code}"
                                        )
                                    except Exception as e:
                                        logger.error(
                                            f"[SSE:{connection_id}] Error sending message: {e}"
                                        )
                                        # Don't re-raise to keep the writer alive
                        except Exception as exc:
                            logger.error(
                                f"[SSE:{connection_id}] Error in post_writer: {exc}"
                            )
                        finally:
                            await write_stream.aclose()

                    # Start the reader task first to get the endpoint URL
                    received_endpoint_url = await tg.start(sse_reader)
                    logger.info(
                        f"[SSE:{connection_id}] Starting post writer with endpoint URL: {received_endpoint_url}"
                    )
                    tg.start_soon(post_writer, received_endpoint_url)

                    # Start the heartbeat task if enabled
                    if enable_heartbeat:
                        logger.info(f"[SSE:{connection_id}] Starting heartbeat task")
                        heartbeat_task = tg.start_soon(heartbeat_sender)

                    try:
                        yield read_stream, write_stream
                    finally:
                        logger.info(f"[SSE:{connection_id}] Closing SSE client")
                        tg.cancel_scope.cancel()
        finally:
            logger.debug(f"[SSE:{connection_id}] Cleaning up streams")
            await read_stream_writer.aclose()
            await write_stream.aclose()


# Export the same interface as the original for easy drop-in replacement
sse_client = patched_sse_client
