from loguru import logger
import sys
from app.config import get_settings
import os

settings = get_settings()

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

def setup_logger():
    """Configure Loguru logger."""
    # Remove default handler
    logger.remove()
    
    # Add console handler with specified format
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level=settings.LOG_LEVEL,
        backtrace=True,
        diagnose=True,
    )
    
    # Add file handler for persistent logging
    logger.add(
        "logs/app.log",
        rotation="500 MB",  # Create new file when current one reaches 500MB
        retention="10 days",  # Keep logs for 10 days
        compression="zip",  # Compress rotated logs
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        backtrace=True,
        diagnose=True
    )
    
    # Add error-specific log file
    logger.add(
        "logs/error.log",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}\n{exception}",
        backtrace=True,
        diagnose=True,
        filter=lambda record: record["level"].name == "ERROR"
    )
    
    return logger

# Setup logger
logger = setup_logger()

# Test logging configuration on startup
if settings.ENVIRONMENT == "development":
    logger.debug("Logger initialized - Debug Mode")
    logger.info("Logger initialized - Info Mode")
    logger.warning("Logger initialized - Warning Mode")
    # logger.error("Logger initialized - Error Mode") # Uncomment to test error logging