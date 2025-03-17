from loguru import logger
import sys
from app.config import get_settings

settings = get_settings()

def setup_logger():
    """configure loguru logger"""
    #remove defualt handler
    logger.remove()

    #add custom logger
    logger.add(
        sys.stderr,
        format= "{time: YYYY-MM-DD HH:mm:ss} |{level} | {message}",
        level= settings.LOG_LEVEL,
        backtrace= True,
        diagnose= True,
    )

    #Add file handler for production environment
    if settings.ENVIRONMENT == "production":
        logger.add(
            "logs/app.log",
            rotation= "500 MB",
            retention="10 days",
            compression="zip",
            level = settings.LOG_LEVEL
        )

    return logger

logger = setup_logger()