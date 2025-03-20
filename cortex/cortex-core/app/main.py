import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from app.api.auth import router as auth_router
from app.api.input import router as input_router
from app.api.output import router as output_router
from app.api.config import router as config_router
from app.core.event_bus import event_bus

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    yield
    # Shutdown
    logger.info("Application shutting down")
    await event_bus.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Cortex Core",
    description="Cortex Core API for input and output processing",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint for health checks
@app.get("/", tags=["status"])
async def root():
    """API status endpoint."""
    return {"status": "online", "service": "Cortex Core"}

# Include routers
app.include_router(auth_router)
app.include_router(input_router)
app.include_router(output_router)
app.include_router(config_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)