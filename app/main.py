from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import chat, analytics, conversation
from app.core.logger import logger
from app.config import get_settings
from app.core.middleware import ErrorHandlingMiddleware, RequestContextMiddleware
from app.services.cache_service import cache_service
from app.api.routes import chat, analytics, conversation, analysis  # Add analysis
from app.services.batch_service import batch_service
from app.services.conversation_manager import conversation_manager
from app.services.monitoring_service import monitoring_service
from app.core.error_handler import (
    error_handler,
    cleanup_handler,
    ErrorLogging,
    APIError
)
import asyncio
import time

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Company Chatbot API powered by OpenAI",
    version="1.0.0"
)

# Add middlewares
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(conversation.router, prefix="/api")
app.include_router(analysis.router, prefix="/api") 

# Custom response headers middleware
@app.middleware("http")
async def add_response_headers(request: Request, call_next):
    """Add security and cache control headers."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Track and log request processing time."""
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"Process Time: {process_time:.3f}s "
            f"Status: {response.status_code}"
        )
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} "
            f"Process Time: {process_time:.3f}s "
            f"Error: {str(e)}"
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    await ErrorLogging.log_error(exc, request)
    await cleanup_handler(exc)
    return await error_handler(request, exc)

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle known API errors."""
    await ErrorLogging.log_error(exc, request)
    return await error_handler(request, exc)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        logger.info("Starting up the application...")
        
        # Start monitoring service
        asyncio.create_task(monitoring_service.start_periodic_export(interval_minutes=60))
        
        # Initialize cache cleanup task
        asyncio.create_task(cache_service._periodic_cleanup())
        
        # Initialize conversation backup task
        asyncio.create_task(conversation_manager._periodic_backup())
        
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        logger.info("Shutting down the application...")
        
        # Export final metrics
        await monitoring_service.export_metrics("final_metrics.json")
        
        # Archive active conversations
        for session_id in conversation_manager.conversations.keys():
            await conversation_manager.archive_conversation(session_id)
            
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {e}")

# Development server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )