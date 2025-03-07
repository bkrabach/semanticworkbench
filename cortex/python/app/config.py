"""
Application Configuration

This module loads and manages application configuration settings from environment
variables with sensible defaults. It uses Pydantic for validation.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    EnvSettingsSource,
)
from typing import Any, Dict, Tuple, Type


class LogLevel(str, Enum):
    """Log level enum"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Environment enum"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


def _strip_comments(v: Any) -> Any:
    """
    Strip comments from string values in environment variables.
    Comments start with # and continue to the end of line.
    """
    if not isinstance(v, str):
        return v

    # If there's a # character, split on it and take only the first part
    parts = v.split("#", 1)
    if len(parts) > 1:
        return parts[0].strip()
    return v


class Settings(BaseSettings):
    """
    Application settings

    This class defines all application settings with defaults.
    Values can be overridden by environment variables.
    """

    # App info
    app_name: str = "Cortex API"
    description: str = "Cortex Core API"
    version: str = "0.1.0"

    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        validation_alias="ENVIRONMENT",
    )
    debug: bool = Field(default=True, validation_alias="DEBUG")
    reload: bool = Field(default=True, validation_alias="RELOAD")

    # Server settings
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    workers: int = Field(default=1, validation_alias="WORKERS")
    api_prefix: str = Field(default="/api", validation_alias="API_PREFIX")

    # CORS settings
    allow_origins: List[str] = Field(default=["*"], validation_alias="ALLOW_ORIGINS")
    allow_origin_regex: Optional[str] = Field(
        default=None, validation_alias="ALLOW_ORIGIN_REGEX"
    )
    allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        validation_alias="ALLOW_METHODS",
    )
    allow_headers: List[str] = Field(default=["*"], validation_alias="ALLOW_HEADERS")
    allow_credentials: bool = Field(default=True, validation_alias="ALLOW_CREDENTIALS")

    # Security settings
    secret_key: str = Field(
        default="INSECURE_CHANGE_ME_IN_PRODUCTION",
        validation_alias="SECRET_KEY",
    )
    access_token_expire_minutes: int = Field(
        default=30,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        validation_alias="REFRESH_TOKEN_EXPIRE_DAYS",
    )
    algorithm: str = Field(default="HS256", validation_alias="ALGORITHM")
    bcrypt_rounds: int = Field(default=12, validation_alias="BCRYPT_ROUNDS")

    # Database settings
    database_url: str = Field(
        default="sqlite:///./app.db",
        validation_alias="DATABASE_URL",
    )
    sql_echo: bool = Field(default=False, validation_alias="SQL_ECHO")
    db_pool_size: int = Field(default=5, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, validation_alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, validation_alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=1800, validation_alias="DB_POOL_RECYCLE")

    # Redis settings
    redis_url: Optional[str] = Field(default=None, validation_alias="REDIS_URL")
    redis_prefix: str = Field(default="cortex:", validation_alias="REDIS_PREFIX")
    redis_default_ttl: int = Field(default=3600, validation_alias="REDIS_DEFAULT_TTL")

    # Memory settings
    default_memory_ttl: int = Field(default=0, validation_alias="DEFAULT_MEMORY_TTL")

    # File storage settings
    upload_dir: str = Field(default="./uploads", validation_alias="UPLOAD_DIR")
    max_upload_size: int = Field(
        default=10 * 1024 * 1024, validation_alias="MAX_UPLOAD_SIZE"
    )
    allowed_extensions: List[str] = Field(
        default=[
            ".txt",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".csv",
            ".json",
            ".md",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
        ],
        validation_alias="ALLOWED_EXTENSIONS",
    )

    # Logging settings
    log_level: LogLevel = Field(default=LogLevel.INFO, validation_alias="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        validation_alias="LOG_FORMAT",
    )
    log_dir: str = Field(default="./logs", validation_alias="LOG_DIR")
    enable_access_log: bool = Field(default=True, validation_alias="ENABLE_ACCESS_LOG")
    enable_file_logging: bool = Field(
        default=True, validation_alias="ENABLE_FILE_LOGGING"
    )

    # Feature flags
    enable_docs: bool = Field(default=True, validation_alias="ENABLE_DOCS")

    @field_validator("database_url", mode="before")
    def validate_database_url(cls, v: str) -> str:
        """Validate and normalize database URL"""
        # Handle SQLite absolute paths
        if v.startswith("sqlite:///"):
            # Extract path part (without sqlite:///)
            sqlite_path = v[10:]

            # If path is not absolute, make it absolute
            if not os.path.isabs(sqlite_path):
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                abs_path = os.path.join(base_dir, sqlite_path)
                v = f"sqlite:///{abs_path}"

        return v

    @field_validator("upload_dir", mode="before")
    def validate_upload_dir(cls, v: str) -> str:
        """Validate and create upload directory if it doesn't exist"""
        upload_path = Path(v)

        # If path is not absolute, make it absolute
        if not upload_path.is_absolute():
            base_dir = Path(__file__).parent.parent
            upload_path = base_dir / v

        # Create directory if it doesn't exist
        upload_path.mkdir(parents=True, exist_ok=True)

        return str(upload_path)

    @field_validator("log_dir", mode="before")
    def validate_log_dir(cls, v: str) -> str:
        """Validate and create log directory if it doesn't exist"""
        log_path = Path(v)

        # If path is not absolute, make it absolute
        if not log_path.is_absolute():
            base_dir = Path(__file__).parent.parent
            log_path = base_dir / v

        # Create directory if it doesn't exist
        log_path.mkdir(parents=True, exist_ok=True)

        return str(log_path)

    @property
    def is_development(self) -> bool:
        """Check if environment is development"""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        """Check if environment is staging"""
        return self.environment == Environment.STAGING

    @property
    def is_production(self) -> bool:
        """Check if environment is production"""
        return self.environment == Environment.PRODUCTION

    @property
    def is_test(self) -> bool:
        """Check if environment is test"""
        return self.environment == Environment.TEST

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Add a field validator to strip comments from all string values
    @field_validator("*", mode="before")
    @classmethod
    def strip_comments_from_values(cls, v):
        """Global validator to strip comments from all string values"""
        return _strip_comments(v)


# Create global settings instance
settings = Settings()


# Export public symbols
__all__ = ["Settings", "LogLevel", "Environment", "settings"]
