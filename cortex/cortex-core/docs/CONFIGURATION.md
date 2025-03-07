# Configuration Guide

Cortex Core uses a hierarchical configuration system built with Pydantic, allowing for flexible configuration via environment variables and `.env` file.

## Configuration Structure

The configuration is divided into several components, each with its own set of parameters:

### Database Configuration

Settings for database connection.

| Parameter | Description             | Default Value           | Environment Variable |
| --------- | ----------------------- | ----------------------- | -------------------- |
| url       | Database connection URL | `sqlite:///./cortex.db` | `DATABASE_URL`       |

Example:

```
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cortex"
```

### Cache Configuration

Settings for Redis cache.

| Parameter | Description            | Default Value | Environment Variable |
| --------- | ---------------------- | ------------- | -------------------- |
| host      | Redis host             | `localhost`   | `REDIS_HOST`         |
| port      | Redis port             | `6379`        | `REDIS_PORT`         |
| password  | Redis password         | `None`        | `REDIS_PASSWORD`     |
| ttl       | Default TTL in seconds | `3600`        | `REDIS_TTL`          |

Example:

```
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_PASSWORD="your-redis-password"
REDIS_TTL=7200
```

### Security Configuration

Settings for authentication and encryption.

| Parameter            | Description                       | Default Value                      | Environment Variable            |
| -------------------- | --------------------------------- | ---------------------------------- | ------------------------------- |
| jwt_secret           | Secret for JWT token generation   | `default-jwt-secret-change-me`     | `SECURITY_JWT_SECRET`           |
| encryption_key       | Key for encrypting sensitive data | `default-encryption-key-change-me` | `SECURITY_ENCRYPTION_KEY`       |
| token_expiry_seconds | Token validity period in seconds  | `86400` (24 hours)                 | `SECURITY_TOKEN_EXPIRY_SECONDS` |

Example:

```
SECURITY_JWT_SECRET="your-secure-jwt-secret"
SECURITY_ENCRYPTION_KEY="your-secure-encryption-key"
SECURITY_TOKEN_EXPIRY_SECONDS=43200
```

### Server Configuration

Settings for the FastAPI server.

| Parameter | Description   | Default Value | Environment Variable |
| --------- | ------------- | ------------- | -------------------- |
| port      | Server port   | `4000`        | `SERVER_PORT`        |
| host      | Server host   | `localhost`   | `SERVER_HOST`        |
| log_level | Logging level | `info`        | `SERVER_LOG_LEVEL`   |

Example:

```
SERVER_PORT=8000
SERVER_HOST="0.0.0.0"
SERVER_LOG_LEVEL="debug"
```

### Memory Configuration

Settings for the memory system.

| Parameter      | Description                           | Default Value | Environment Variable    |
| -------------- | ------------------------------------- | ------------- | ----------------------- |
| type           | Memory system type                    | `whiteboard`  | `MEMORY_TYPE`           |
| retention_days | Number of days to retain memory items | `90`          | `MEMORY_RETENTION_DAYS` |
| max_items      | Maximum number of items to store      | `10000`       | `MEMORY_MAX_ITEMS`      |

Example:

```
MEMORY_TYPE="whiteboard"
MEMORY_RETENTION_DAYS=30
MEMORY_MAX_ITEMS=5000
```

### MCP (Model Context Protocol) Configuration

Settings for MCP integrations.

| Parameter | Description           | Default Value | Environment Variable                           |
| --------- | --------------------- | ------------- | ---------------------------------------------- |
| endpoints | List of MCP endpoints | `[]`          | `MCP_ENDPOINTS` or individual `MCP_ENDPOINT_*` |

Example using JSON format:

```
MCP_ENDPOINTS='[{"name":"vscode","endpoint":"http://localhost:5000","type":"vscode"}]'
```

Example using individual endpoints:

```
MCP_ENDPOINT_VSCODE="http://localhost:5000|vscode"
MCP_ENDPOINT_BROWSER="http://localhost:5001|browser"
```

### MSAL (Microsoft Authentication) Configuration

Optional settings for Microsoft authentication.

| Parameter     | Description        | Default Value                              | Environment Variable |
| ------------- | ------------------ | ------------------------------------------ | -------------------- |
| client_id     | MSAL client ID     | `None`                                     | `MSAL_CLIENT_ID`     |
| client_secret | MSAL client secret | `None`                                     | `MSAL_CLIENT_SECRET` |
| authority     | MSAL authority URL | `https://login.microsoftonline.com/common` | `MSAL_AUTHORITY`     |

Example:

```
MSAL_CLIENT_ID="your-client-id"
MSAL_CLIENT_SECRET="your-client-secret"
MSAL_AUTHORITY="https://login.microsoftonline.com/your-tenant-id"
```

## Configuration File Format

Cortex Core looks for configuration in a `.env` file in the project root directory. Here's a complete example:

```
# Database
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cortex"

# Redis
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_PASSWORD=""
REDIS_TTL=3600

# Security
SECURITY_JWT_SECRET="your-secure-jwt-secret"
SECURITY_ENCRYPTION_KEY="your-secure-encryption-key"
SECURITY_TOKEN_EXPIRY_SECONDS=86400

# Server
SERVER_PORT=4000
SERVER_HOST="localhost"
SERVER_LOG_LEVEL="info"

# Memory
MEMORY_TYPE="whiteboard"
MEMORY_RETENTION_DAYS=90
MEMORY_MAX_ITEMS=10000

# MCP Integration
MCP_ENDPOINT_VSCODE="http://localhost:5000|vscode"
MCP_ENDPOINT_M365="http://localhost:5001|m365"
```

## Environment Variables

All configuration parameters can be set using environment variables. These take precedence over values in the `.env` file.

Example of setting configuration via environment variables:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cortex"
export SECURITY_JWT_SECRET="your-secure-jwt-secret"
export SERVER_PORT=4000
```

## Environment-Specific Configuration

For different environments (development, testing, production), you can use different `.env` files or environment variables.

Example structure:

- `.env` - Default configuration
- `.env.development` - Development-specific settings
- `.env.test` - Test-specific settings
- `.env.production` - Production-specific settings

To load a specific environment file:

```bash
ENV=production python -m app.main
```

## Configuration in Docker

When running Cortex Core in Docker, you can pass configuration using environment variables:

```bash
docker run -p 4000:4000 \
  -e DATABASE_URL="postgresql://user:password@host:port/database" \
  -e REDIS_HOST="redis-host" \
  -e SECURITY_JWT_SECRET="your-jwt-secret" \
  -e SECURITY_ENCRYPTION_KEY="your-encryption-key" \
  cortex-core
```

Alternatively, you can mount a `.env` file:

```bash
docker run -p 4000:4000 \
  -v /path/to/.env:/app/.env \
  cortex-core
```

## Configuration Management in Code

The configuration is managed through Pydantic models in `app/config.py`:

```python
from typing import List, Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings
import os
from pathlib import Path

class DatabaseConfig(BaseSettings):
    """Database configuration"""
    url: str = "sqlite:///./cortex.db"

    class Config:
        env_prefix = "DATABASE_"

class CacheConfig(BaseSettings):
    """Redis cache configuration"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    ttl: int = 3600

    class Config:
        env_prefix = "REDIS_"

# ... other configuration classes ...

class Settings(BaseSettings):
    """Main application settings"""
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    mcp: McpConfig = Field(default_factory=McpConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize MSAL config if client_id exists
        if "MSAL_CLIENT_ID" in os.environ:
            self.security.msal_config = MsalConfig()

        # Validate production environment
        if os.environ.get("ENV") == "production":
            self._validate_production()

    def _validate_production(self):
        """Validate that secure settings are set in production"""
        if (
            self.security.jwt_secret == "default-jwt-secret-change-me"
            or self.security.encryption_key == "default-encryption-key-change-me"
        ):
            raise ValueError("Production environment requires secure JWT secret and encryption key")

# Create and export settings instance
settings = Settings()
```

You can access configuration values in your code using the `settings` instance:

```python
from app.config import settings

# Use database URL
database_url = settings.database.url

# Use Redis host
redis_host = settings.cache.host

# Use JWT secret
jwt_secret = settings.security.jwt_secret
```

## Security Considerations

- **Production Settings**: For production environments, make sure to use secure, randomly generated keys for `SECURITY_JWT_SECRET` and `SECURITY_ENCRYPTION_KEY`.
- **Environment Variables**: Sensitive configuration values should be set using environment variables, not hardcoded in the `.env` file.
- **Database Credentials**: Database credentials should be secured and not exposed in configuration files that are checked into version control.
- **Secrets Management**: Consider using a secrets management service for production environments.

## Validation

Cortex Core validates the configuration at startup. If required configuration is missing or invalid, the application will fail to start with an appropriate error message.

In production, the application also validates that secure settings are properly set, raising an error if default values are detected.
