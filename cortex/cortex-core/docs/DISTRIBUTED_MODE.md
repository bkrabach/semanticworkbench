# Distributed Mode

This document explains how to run Cortex Core in distributed mode, with Memory and Cognition services running as separate processes.

## Architecture Overview

In distributed mode, Cortex Core consists of three separate services:

1. **Core Application**: Main FastAPI application that handles HTTP requests and SSE connections from clients
2. **Memory Service**: Standalone service for storing and retrieving data
3. **Cognition Service**: Standalone service for context retrieval and analysis

Services communicate with each other using HTTP and Server-Sent Events (SSE), implementing the Model Context Protocol (MCP) over the network.

```
+---------------+          +----------------+
|               |          |                |
|  Core App     |<-------->|  Memory        |
|  (FastAPI)    |          |  Service       |
|               |          |                |
+---------------+          +----------------+
        ^                          ^
        |                          |
        v                          v
+---------------+          +----------------+
|               |          |                |
|  Clients      |          |  Cognition     |
|  (Web/API)    |          |  Service       |
|               |          |                |
+---------------+          +----------------+
```

## Running in Distributed Mode

### Using Docker Compose

The simplest way to run Cortex Core in distributed mode is using Docker Compose:

```bash
docker compose up
```

This will start all three services:
- Core Application on port 8000
- Memory Service on port 9000
- Cognition Service on port 9100

### Using the Run Script

For development, you can use the provided script:

```bash
python scripts/run_distributed.py
```

This script starts all three services as separate processes on your local machine.

### Manual Service Launch

You can also start each service manually:

1. Start Memory Service:
```bash
python -m app.services.standalone_memory_service
```

2. Start Cognition Service:
```bash
MEMORY_SERVICE_URL=http://localhost:9000 python -m app.services.standalone_cognition_service
```

3. Start Core Application:
```bash
CORTEX_DISTRIBUTED_MODE=true MEMORY_SERVICE_URL=http://localhost:9000 COGNITION_SERVICE_URL=http://localhost:9100 python -m app.main
```

## Configuration

The distributed architecture is configured using environment variables:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| CORTEX_DISTRIBUTED_MODE | Enable distributed mode | false |
| MEMORY_SERVICE_URL | URL of Memory Service | http://localhost:9000 |
| COGNITION_SERVICE_URL | URL of Cognition Service | http://localhost:9100 |
| MEMORY_SERVICE_PORT | Port for Memory Service | 9000 |
| COGNITION_SERVICE_PORT | Port for Cognition Service | 9100 |

## Network Protocol

### Tool Calls

Tool calls are made as HTTP POST requests to the tool endpoint:

```
POST /tool/{tool_name}
Content-Type: application/json

{
  "arguments": {
    "arg1": "value1",
    "arg2": "value2"
  }
}
```

The response is a JSON object containing the tool result:

```json
{
  "result": {
    "key1": "value1",
    "key2": "value2"
  }
}
```

### Resource Streams

Resources are accessed via Server-Sent Events (SSE) connections:

```
GET /resource/{resource_path}
Accept: text/event-stream
```

The server responds with an SSE stream:

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Transfer-Encoding: chunked

data: {"key1":"value1","key2":"value2"}

data: {"key1":"updated1","key2":"updated2"}
```

## Health Checks

Each service exposes a health check endpoint:

```
GET /health
```

Returns a JSON response:

```json
{
  "status": "healthy"
}
```

Services monitor each other's health, enabling circuit breaking and fallback strategies.

## Network Resilience

The network MCP client includes:

1. **Connection Pooling**: Efficient reuse of HTTP connections
2. **Circuit Breaking**: Prevents calls to failing services
3. **Retry Logic**: Automatically retries failed operations with backoff
4. **Error Handling**: Detailed error responses for debugging

## Security

In production, you should secure the communication between services:

1. **Network Isolation**: Run services in a private network
2. **Authentication**: Add service-to-service authentication
3. **TLS**: Use HTTPS for all communication
4. **Access Control**: Restrict access to service endpoints

## Monitoring and Metrics

Each service logs operations with the standard logging framework. In production, consider:

1. **Centralized Logging**: Aggregate logs from all services
2. **Metrics Collection**: Track response times, error rates, etc.
3. **Alerting**: Set up alerts for service failures

## Testing

The distributed mode is tested in `tests/core/test_distributed_mode.py`, which verifies:

1. Service discovery
2. Connection management
3. Circuit breaking
4. Network resilience

## Troubleshooting

### Common Issues

1. **Service Not Found**: Check service URLs in environment variables
2. **Connection Refused**: Ensure services are running and ports are accessible
3. **Circuit Open**: Service health check is failing, check service logs
4. **Slow Responses**: Monitor network latency between services

### Debugging

1. Check service logs for errors
2. Verify health endpoints are returning 200 status
3. Use `httpie` or `curl` to directly test service endpoints
4. Enable debug logging with `LOG_LEVEL=DEBUG`