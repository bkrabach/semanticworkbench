# Cortex Core Configuration

This document describes the configuration options for the Cortex Core service, which provides the central orchestration between client applications and specialized backend services.

## Environment Variables

Cortex Core uses environment variables for configuration. All variables have sensible defaults, allowing the application to run with minimal setup in development environments.

### Server Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SERVER_HOST` | The hostname or IP address the server binds to | `0.0.0.0` | `127.0.0.1` |
| `SERVER_PORT` | The port number the server listens on | `8000` | `9000` |
| `DEBUG` | Enable debug mode (more verbose output) | `false` | `true` |
| `ENVIRONMENT` | Environment name (development, production, etc.) | `development` | `production` |
| `APP_VERSION` | Application version shown in health checks | `1.0.0` | `2.1.3` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |

### Authentication Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `USE_AUTH0` | Whether to use Auth0 for authentication | `false` | `true` |
| `AUTH0_DOMAIN` | Auth0 domain for JWT verification | `your-auth0-domain.auth0.com` | `your-tenant.us.auth0.com` |
| `AUTH0_AUDIENCE` | Auth0 audience (API identifier) | `https://api.example.com` | `https://api.yourcompany.com` |
| `DEV_SECRET` | Secret for development JWT creation and verification | `development_secret_key_do_not_use_in_production` | A strong random string |

> **Warning:** The default `DEV_SECRET` is not secure for production use. Always set a strong, unique value in production environments.

### Service URLs

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MEMORY_SERVICE_URL` | URL for the Memory service SSE endpoint | `http://localhost:5001/sse` | `http://memory-service:5001/sse` |
| `COGNITION_SERVICE_URL` | URL for the Cognition service SSE endpoint | `http://localhost:5000/sse` | `http://cognition-service:5000/sse` |

## Configuration Validation

Cortex Core validates critical configuration values at startup. If configuration is invalid, warnings will be logged, but the application will still attempt to start to allow for development flexibility. In production environments, you should monitor logs for configuration warnings.

Critical validation checks include:
- When `USE_AUTH0` is true, `AUTH0_DOMAIN` and `AUTH0_AUDIENCE` must be properly configured
- Service URLs must be non-empty

## Configuration Example

Here's an example of setting configuration variables in a development environment:

```bash
# Server settings
export SERVER_PORT=8080
export LOG_LEVEL=DEBUG

# Auth settings
export USE_AUTH0=false
export DEV_SECRET="your-secret-key-for-development"

# Service URLs
export MEMORY_SERVICE_URL="http://localhost:5001/sse"
export COGNITION_SERVICE_URL="http://localhost:5000/sse"

# Start the application
python -m app.main
```

For production, you would typically set these in your deployment platform's environment configuration (Docker, Kubernetes, etc.).

## Docker Environment File

You can use a `.env` file for Docker deployments:

```
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
ENVIRONMENT=production
USE_AUTH0=true
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://api.yourcompany.com
MEMORY_SERVICE_URL=http://memory-service:5001/sse
COGNITION_SERVICE_URL=http://cognition-service:5000/sse
LOG_LEVEL=INFO
```

Then run with:
```bash
docker run --env-file .env cortex-core
```

## Code Usage

In the application code, you can access configuration values directly from the `app.core.config` module:

```python
from app.core.config import MEMORY_SERVICE_URL, SERVER_PORT, USE_AUTH0

# Use configuration values in your code
print(f"Running on port {SERVER_PORT}")
print(f"Using memory service at {MEMORY_SERVICE_URL}")
print(f"Auth0 enabled: {USE_AUTH0}")
```

For debugging purposes, you can also retrieve all configuration settings as a dictionary:

```python
from app.core.config import get_settings

settings = get_settings()
print(settings)
```