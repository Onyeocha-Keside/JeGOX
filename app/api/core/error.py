from fastapi import HTTPException

class ChatbotException(Exception):
    """base exception for all chatbot related errors"""
    pass

class DocumentProcessingError(ChatbotException):
    """raised when there is an error processing the documents"""
    pass

class OpenAiError(ChatbotException):
    """Raised when there is an error with openai api"""
    pass

class VectorStoreError(ChatbotException):
    """Raise when there is an error with vector store operation"""
    pass

def get_error_response(error_msg: str, status_code: int = 400):
    """convert exceptions to FastAPI Http exception"""
    raise HTTPException(
        status_code= status_code,
        detail= error_msg
    )