from loguru import logger
import sys
from app.config import get_settings
import os

settings = get_settings()

# Remove directory creation since we won't be using file logging
# os.makedirs("logs", exist_ok=True)  # Remove this line

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
    
    # Remove all file handlers for Vercel deployment
    # File handler section removed
    # Error log file section removed
    
    return logger

# Setup logger
logger = setup_logger()

# Test logging configuration on startup
if settings.ENVIRONMENT == "development":
    logger.debug("Logger initialized - Debug Mode")
    logger.info("Logger initialized - Info Mode")
    logger.warning("Logger initialized - Warning Mode")
    # logger.error("Logger initialized - Error Mode") # Uncomment to test error logging