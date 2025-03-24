# config.py for memory service
import os


class MemoryServiceConfig:
    HOST: str = os.environ.get("MEMORY_SERVICE_HOST", "localhost")
    PORT: int = int(os.environ.get("MEMORY_SERVICE_PORT", "5001"))
    MCP_BASE_ROUTE: str = "/mcp"
    STORAGE_DIR: str = os.environ.get("MEMORY_STORAGE_DIR", "./memory_data")

    # LLM Configuration
    LLM_MODEL: str = os.environ.get("MEMORY_LLM_MODEL", "claude-3-sonnet-20240229")
    LLM_TEMPERATURE: float = float(os.environ.get("MEMORY_LLM_TEMPERATURE", "0.0"))

    # Memory updating parameters
    MAX_MEMORY_LENGTH: int = int(os.environ.get("MAX_MEMORY_LENGTH", "2000"))

    @property
    def service_url(self) -> str:
        return f"http://{self.HOST}:{self.PORT}{self.MCP_BASE_ROUTE}"


config = MemoryServiceConfig()
