"""
Configuration management for Cortex Core using Pydantic
"""

from typing import List, Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings
import os
from pathlib import Path


class MsalConfig(BaseSettings):
    """Microsoft Authentication Library configuration"""

    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    authority: str = "https://login.microsoftonline.com/common"

    class Config:
        env_prefix = "MSAL_"


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
    ttl: int = 3600  # Default TTL in seconds

    class Config:
        env_prefix = "REDIS_"
        env_nested_delimiter = None


class SecurityConfig(BaseSettings):
    """Security configuration"""

    jwt_secret: str = "default-jwt-secret-change-me"
    encryption_key: str = "default-encryption-key-change-me"
    token_expiry_seconds: int = 86400
    msal_config: Optional[MsalConfig] = None

    class Config:
        env_prefix = "SECURITY_"


class ServerConfig(BaseSettings):
    """Server configuration"""

    port: int = 4000
    host: str = "localhost"
    log_level: str = "info"

    class Config:
        env_prefix = "SERVER_"


class MemoryConfig(BaseSettings):
    """Memory system configuration"""

    type: str = "whiteboard"  # Options: "whiteboard", "jake"
    retention_days: int = 90
    max_items: int = 10000

    class Config:
        env_prefix = "MEMORY_"


class McpEndpoint(BaseSettings):
    """MCP endpoint configuration"""

    name: str
    endpoint: str
    type: str


class McpConfig(BaseSettings):
    """MCP configuration - for internal service-to-service communication only"""

    # Flag to explicitly indicate that MCP is for internal use only
    internal_only: bool = True

    # List of MCP endpoints (internal services)
    endpoints: List[Dict[str, str]] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Load MCP endpoints from environment variables
        mcp_endpoints_json = os.environ.get("MCP_ENDPOINTS")
        if mcp_endpoints_json:
            import json

            try:
                self.endpoints = json.loads(mcp_endpoints_json)
            except json.JSONDecodeError:
                pass

        # Add individual MCP endpoints
        # Format: MCP_ENDPOINT_name=endpoint_url|type
        for key, value in os.environ.items():
            if key.startswith("MCP_ENDPOINT_"):
                name = key.replace("MCP_ENDPOINT_", "")
                if "|" in value:
                    endpoint, type_ = value.split("|", 1)
                    self.endpoints.append({"name": name, "endpoint": endpoint, "type": type_})


class SseConfig(BaseSettings):
    """Server-Sent Events configuration"""

    # Maximum number of open connections per client
    max_connections_per_client: int = 5

    # Heartbeat interval in seconds
    heartbeat_interval: int = 30

    # Enable/disable SSE debugging
    debug: bool = False

    class Config:
        env_prefix = "SSE_"


class Settings(BaseSettings):
    """Main application settings"""

    database: DatabaseConfig = DatabaseConfig()
    cache: CacheConfig = CacheConfig()
    security: SecurityConfig = SecurityConfig()
    server: ServerConfig = ServerConfig()
    memory: MemoryConfig = MemoryConfig()
    mcp: McpConfig = McpConfig()
    sse: SseConfig = SseConfig()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

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
