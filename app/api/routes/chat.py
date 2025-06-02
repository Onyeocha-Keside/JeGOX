from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
from datetime import datetime, timedelta
import uuid
from jose import jwt, JWTError  # Import JWTError from jose
from app.api.models.chat import (
    ChatMessage, 
    ChatResponse, 
    DocumentUpload,
    DocumentProcessResponse,
    HealthCheck
)
from app.services.chat_service import chat_service
from app.utils.document_loader import document_loader
from app.services.openai_service import openai_service
from app.services.vector_store import vector_store
from app.core.security import security_manager
from app.core.logger import logger
from app.config import get_settings
import os
from typing import Dict, Any

settings = get_settings()
router = APIRouter()


# Ticket Service
class TicketService:
    def __init__(self, secret_key: str, default_expiry_minutes: int = 60, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.default_expiry_minutes = default_expiry_minutes
        self.algorithm = algorithm
    
    def generate_ticket(self, 
                       user_id: Optional[str] = None,
                       context: Optional[Dict[str, Any]] = None,
                       expires_in_minutes: Optional[int] = None) -> tuple[str, datetime]:
        """Generate a new chat ticket."""
        
        expiry_minutes = expires_in_minutes or self.default_expiry_minutes
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        payload = {
            "ticket_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "user_id": user_id,
            "context": context or {},
            "message_count": 0
        }
        
        ticket = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return ticket, expires_at
    
    def validate_and_refresh_ticket(self, ticket: str) -> tuple[str, Dict[str, Any], bool]:
        """
        Validate ticket and return refreshed version.
        Returns: (new_ticket, payload, is_valid)
        """
        try:
            payload = jwt.decode(ticket, self.secret_key, algorithms=[self.algorithm])
            
            # Check expiration
            expires_at = datetime.fromisoformat(payload["expires_at"])
            if datetime.utcnow() > expires_at:
                return None, {}, False
            
            # Increment message count and refresh expiration
            payload["message_count"] += 1
            new_expires_at = datetime.utcnow() + timedelta(minutes=self.default_expiry_minutes)
            payload["expires_at"] = new_expires_at.isoformat()
            
            new_ticket = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return new_ticket, payload, True
            
        except JWTError:  # Changed from jwt.InvalidTokenError to JWTError
            return None, {}, False

ticket_service = TicketService(
    secret_key=settings.ENCRYPTION_KEY,
    default_expiry_minutes=getattr(settings, 'TICKET_EXPIRY_MINUTES', 60),
    algorithm=getattr(settings, 'TICKET_ALGORITHM', 'HS256')
)

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    message: ChatMessage,
    request: Request
) -> ChatResponse:
    """
    Process chat messages and return responses.
    """
    try:
        # Check rate limit
        if not await security_manager.check_rate_limit(request):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )

        # Handle ticket validation and session management
        session_id = None
        is_new_session = False
        user_context = {}
        
        if message.ticket:
            # Validate existing ticket
            new_ticket, payload, is_valid = ticket_service.validate_and_refresh_ticket(message.ticket)
            
            if not is_valid:
                # Ticket expired or invalid, create new session
                is_new_session = True
                response_ticket, expires_at = ticket_service.generate_ticket()
                session_id = str(uuid.uuid4())  # Generate new session ID
            else:
                # Use existing session from ticket
                session_id = payload.get("ticket_id")  # Use ticket_id as session_id
                user_context = payload.get("context", {})
                response_ticket = new_ticket
        else:
            # No ticket provided, create new session
            is_new_session = True
            response_ticket, expires_at = ticket_service.generate_ticket()
            session_id = str(uuid.uuid4())  # Generate new session ID

        # Process message with proper session_id
        response = await chat_service.process_message(
            session_id=session_id,
            message=message.message,
            metadata=message.metadata
        )

        # Create response with the ticket
        chat_response = ChatResponse(
            **response,
            ticket=response_ticket,
            is_new_session=is_new_session
        )

        return chat_response

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/documents/process", response_model=DocumentProcessResponse)
# async def process_document(document: DocumentUpload) -> DocumentProcessResponse:
#     """
#     Process and store a document in the vector database.
#     """
#     try:
#         # Check if file exists
#         if not os.path.exists(document.file_path):
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"File not found: {document.file_path}"
#             )

#         # Process document
#         chunks = document_loader.process_document(
#             document.file_path,
#             document.metadata
#         )

#         # Create embeddings for chunks
#         texts = [chunk['text'] for chunk in chunks]
#         embeddings = await openai_service.create_embeddings(texts)

#         # Store in vector database
#         await vector_store.store_embeddings(
#             embeddings=embeddings,
#             metadata=[{
#                 'text': chunk['text'],
#                 **chunk['metadata']
#             } for chunk in chunks]
#         )

#         return DocumentProcessResponse(
#             success=True,
#             chunks_processed=len(chunks),
#             file_name=os.path.basename(document.file_path)
#         )

#     except Exception as e:
#         logger.error(f"Error processing document: {e}")
#         return DocumentProcessResponse(
#             success=False,
#             chunks_processed=0,
#             file_name=os.path.basename(document.file_path),
#             error=str(e)
#         )

# @router.get("/documents/status")
# async def get_documents_status():
#     """
#     Get status of documents in vector store.
#     """
#     try:
#         info = await vector_store.get_collection_info()
        
#         # Get sample vectors to verify search
#         sample_results = None
#         if info.get("vectors_count", 0) > 0:
#             # Try a test search
#             test_embedding = await openai_service.create_embeddings(["test query"])
#             sample_results = await vector_store.search_similar(
#                 query_embedding=test_embedding[0],
#                 limit=1
#             )

#         return {
#             "collection_info": info,
#             "vectors_count": info.get("vectors_count", 0),
#             "has_searchable_vectors": bool(sample_results),
#             "status": "ok"
#         }
#     except Exception as e:
#         logger.error(f"Error getting document status: {e}")
#         return {
#             "status": "error",
#             "error": str(e)
#         }

# @router.get("/vector-search/test")
# async def test_vector_search(query: str):
#     """
#     Test vector search functionality with a specific query.
#     """
#     try:
#         # Create embedding for query
#         query_embedding = await openai_service.create_embeddings([query])
        
#         # Search for similar documents
#         results = await vector_store.search_similar(
#             query_embedding=query_embedding[0],
#             limit=3
#         )
        
#         return {
#             "query": query,
#             "results": results,
#             "result_count": len(results),
#             "status": "ok"
#         }
#     except Exception as e:
#         logger.error(f"Error in vector search test: {e}")
#         return {
#             "status": "error",
#             "error": str(e)
#         }

# @router.post("/chat/clear/{session_id}")
# async def clear_chat_history(session_id: str) -> dict:
#     """
#     Clear chat history for a session.
#     """
#     try:
#         success = await chat_service.clear_history(session_id)
#         return {"success": success}
#     except Exception as e:
#         logger.error(f"Error clearing chat history: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """
    Check the health status of the service and its dependencies.
    """
    try:
        # Check OpenAI connection
        openai_ok = await openai_service.get_chat_completion(
            messages=[{"role": "user", "content": "test"}]
        ) is not None

        # Check vector store connection
        vector_ok = await vector_store.search_similar(
            [0] * 1536,  # dummy vector
            limit=1
        ) is not None

        return HealthCheck(
            status="healthy",
            version="1.0.0",
            openai_status=openai_ok,
            vector_store_status=vector_ok
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheck(
            status="unhealthy",
            version="1.0.0",
            openai_status=False,
            vector_store_status=False
        )