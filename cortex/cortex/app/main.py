import logging
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.endpoints import router as api_router
from app.core.config import get_settings
from app.db.database import engine, Base, get_db
from app.core.mcp_client import mcp_client_manager
from app.core.conversation import conversation_handler
from app.core.memory import memory_adapter
from app.core.auth import user_session_manager
from app.core.sse import sse_manager
from app.core.router import message_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For PoC, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"An unexpected error occurred: {str(exc)}"}
    )

# Include API routes
app.include_router(api_router, prefix="/api")

# Add startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize components on application startup."""
    logger.info("Starting up Cortex Core PoC")
    
    # Initialize the message router first (other components depend on it)
    await message_router.initialize()
    logger.info("Message Router initialized")
    
    # Initialize memory adapter
    await memory_adapter.initialize()
    logger.info("Memory Adapter initialized")
    
    # Initialize MCP client manager and register demo servers
    await mcp_client_manager.initialize()
    logger.info("MCP Client Manager initialized")
    
    # Register demo MCP server for testing
    from app.models.schemas import MCPServer
    demo_server = MCPServer(
        name="Demo MCP Server",
        url="http://localhost:8001",  # Replace with actual MCP server URL
    )
    await mcp_client_manager.register_server(demo_server)
    logger.info(f"Registered demo MCP server: {demo_server.name}")
    
    # Initialize user session manager
    await user_session_manager.initialize()
    logger.info("User Session Manager initialized")
    
    # Initialize conversation handler
    await conversation_handler.initialize()
    logger.info("Conversation Handler initialized")
    
    # SSE Manager is initialized when imported
    logger.info("SSE Manager initialized")
    
    logger.info("All components initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    logger.info("Shutting down Cortex Core PoC")
    
    # Clean up in reverse order of initialization
    logger.info("Cleaning up SSE Manager")
    await sse_manager.cleanup()
    
    logger.info("Cleaning up Conversation Handler")
    await conversation_handler.cleanup()
    
    logger.info("Cleaning up User Session Manager")
    await user_session_manager.cleanup()
    
    logger.info("Cleaning up MCP Client Manager")
    await mcp_client_manager.close()
    
    logger.info("Cleaning up Memory Adapter")
    await memory_adapter.cleanup()
    
    logger.info("Cleaning up Message Router")
    await message_router.cleanup()
    
    logger.info("All components cleaned up successfully")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

# Root endpoint redirects to docs
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": f"Welcome to {settings.APP_NAME} {settings.APP_VERSION}. See /docs for API documentation."}

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )