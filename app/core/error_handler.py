from fastapi import Request, status
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from app.core.logger import logger
from app.services.monitoring_service import monitoring_service

class ErrorCode:
    """Error codes for different types of errors."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    OPENAI_ERROR = "OPENAI_ERROR"
    VECTOR_STORE_ERROR = "VECTOR_STORE_ERROR"
    DOCUMENT_ERROR = "DOCUMENT_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class APIError(Exception):
    """Base API Error class."""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class ValidationError(APIError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class RateLimitError(APIError):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            code=ErrorCode.RATE_LIMIT_ERROR,
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )

class OpenAIServiceError(APIError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=ErrorCode.OPENAI_ERROR,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )

class VectorStoreError(APIError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=ErrorCode.VECTOR_STORE_ERROR,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )

class DocumentProcessingError(APIError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=ErrorCode.DOCUMENT_ERROR,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )

async def error_handler(request: Request, error: Exception) -> JSONResponse:
    """Global error handler for all exceptions."""
    
    error_response = {
        "success": False,
        "error": {
            "code": ErrorCode.INTERNAL_ERROR,
            "message": "An unexpected error occurred",
            "details": {}
        }
    }
    status_code = 500

    if isinstance(error, APIError):
        error_response["error"]["code"] = error.code
        error_response["error"]["message"] = error.message
        error_response["error"]["details"] = error.details
        status_code = error.status_code
    else:
        # Log unexpected errors
        logger.exception("Unexpected error occurred:", exc_info=error)

    # Record error in monitoring
    await monitoring_service.record_error(error_response["error"]["code"])

    # Add request information for debugging
    error_response["error"]["details"]["request_id"] = request.headers.get("X-Request-ID")
    error_response["error"]["details"]["path"] = str(request.url)
    error_response["error"]["details"]["method"] = request.method

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )

async def cleanup_handler(error: Exception) -> None:
    """Handle cleanup after error occurs."""
    try:
        # Implement cleanup logic here
        # For example: close connections, rollback transactions, etc.
        pass
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

class ErrorLogging:
    """Error logging utility."""
    
    @staticmethod
    async def log_error(
        error: Exception,
        request: Optional[Request] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log error with context."""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": monitoring_service.current_hour,
            "context": context or {}
        }

        if request:
            error_data.update({
                "request_path": str(request.url),
                "request_method": request.method,
                "request_headers": dict(request.headers),
                "client_ip": request.client.host
            })

        if isinstance(error, APIError):
            error_data.update({
                "error_code": error.code,
                "error_details": error.details
            })

        logger.error("Error occurred:", extra=error_data)