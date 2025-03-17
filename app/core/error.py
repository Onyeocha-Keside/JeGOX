from fastapi import HTTPException
from typing import Optional, Dict, Any

class ChatbotException(Exception):
    """Base exception for chatbot related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

class DocumentProcessingError(ChatbotException):
    """Raised when there's an error processing documents."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Document processing error: {message}", details)

class OpenAIError(ChatbotException):
    """Raised when there's an error with OpenAI API."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"OpenAI error: {message}", details)

class VectorStoreError(ChatbotException):
    """Raised when there's an error with vector store operations."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Vector store error: {message}", details)

class ValidationError(ChatbotException):
    """Raised when there's a validation error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Validation error: {message}", details)

class RateLimitError(ChatbotException):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message)

class AuthenticationError(ChatbotException):
    """Raised when there's an authentication error."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)

class ConfigurationError(ChatbotException):
    """Raised when there's a configuration error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Configuration error: {message}", details)

class DatabaseError(ChatbotException):
    """Raised when there's a database error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Database error: {message}", details)

def get_error_response(error: Exception) -> Dict[str, Any]:
    """Convert exceptions to standardized error response format."""
    if isinstance(error, ChatbotException):
        status_code = 400
        if isinstance(error, OpenAIError):
            status_code = 503  # Service Unavailable
        elif isinstance(error, RateLimitError):
            status_code = 429  # Too Many Requests
        elif isinstance(error, AuthenticationError):
            status_code = 401  # Unauthorized
        
        error_response = {
            "error": {
                "type": error.__class__.__name__,
                "message": error.message,
                "details": error.details
            }
        }
    else:
        status_code = 500
        error_response = {
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred",
                "details": {"original_error": str(error)}
            }
        }
    
    return {"status_code": status_code, "content": error_response}

def raise_http_exception(error: Exception):
    """Convert exceptions to FastAPI HTTP exceptions."""
    error_info = get_error_response(error)
    raise HTTPException(
        status_code=error_info["status_code"],
        detail=error_info["content"]
    )

# Usage examples:
"""
try:
    # Some operation
    pass
except Exception as e:
    raise_http_exception(DocumentProcessinSgError("Failed to process document", {
        "document_name": "example.pdf",
        "error_details": str(e)
    }))
"""