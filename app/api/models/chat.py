from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ChatMessage(BaseModel):
    """Incoming chat message model."""
    message: str = Field(..., min_length=1, max_length=1000)
    ticket : Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    """Response model for chat messages."""
    response: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    needs_human: bool
    context_used: bool
    encrypted_history: str
    ticket: str  # Always return ticket for next message
    is_new_session: bool = False  # Indicates if this started a new session
    metadata: Optional[Dict[str, Any]] = None

class DocumentUpload(BaseModel):
    """Document upload request model."""
    file_path: str
    metadata: Optional[Dict[str, Any]] = None

class DocumentProcessResponse(BaseModel):
    """Response model for document processing."""
    success: bool
    chunks_processed: int
    file_name: str
    error: Optional[str] = None

class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    version: str
    openai_status: bool
    vector_store_status: bool