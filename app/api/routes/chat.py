from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
from datetime import datetime, timedelta
import uuid
import time
from app.services.basic_monitoring import basic_monitor
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
from qdrant_client.http.models import Distance, VectorParams
import os
import asyncio
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
    start_time = time.time()
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
        #end timing
        end_time = time.time()
        response_time = end_time - start_time

        #record the conversation
        basic_monitor.record_conversation(
            user_message=message.message,
            bot_response=response["response"],
            response_time=response_time
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

@router.get("/monitoring/stats")
async def get_monitoring_stats():
    """get basic monitoring stats"""
    stats = basic_monitor.get_stats()
    return {
        "status": "success",
        "data": stats
    }
@router.post("/documents/process", response_model=DocumentProcessResponse)
async def process_document(document: DocumentUpload) -> DocumentProcessResponse:
    """Process and store a document (admin only)."""
    try:
        from app.services.batch_service import batch_service
        
        # Check if file exists
        if not os.path.exists(document.file_path):
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {document.file_path}"
            )

        logger.info(f"Admin processing document: {document.file_path}")

        # Process document into chunks
        chunks = document_loader.process_document(
            document.file_path,
            document.metadata
        )

        logger.info(f"Document split into {len(chunks)} chunks")

        # Extract texts for embedding
        texts = [chunk['text'] for chunk in chunks]
        
        # Process all texts through BatchService
        # BatchService will automatically handle token limits and split if needed
        all_embeddings = []
        
        # Process in manageable groups (your BatchService handles the smart batching)
        for i in range(0, len(texts), 50):  # 50 chunks at a time
            batch_texts = texts[i:i + 50]
            logger.info(f"Processing group {i//50 + 1}/{(len(texts)-1)//50 + 1}")
            
            # Use BatchService for each group
            batch_tasks = [batch_service.add_embedding_task(text) for text in batch_texts]
            batch_embeddings = await asyncio.gather(*batch_tasks)
            all_embeddings.extend(batch_embeddings)
        
        logger.info(f"Created {len(all_embeddings)} embeddings total")

        # Store in vector database
        await vector_store.store_embeddings(
            embeddings=all_embeddings,
            metadata=[{
                'text': chunk['text'],
                **chunk['metadata']
            } for chunk in chunks]
        )

        logger.info(f"Successfully stored {len(all_embeddings)} vectors in Qdrant")

        return DocumentProcessResponse(
            success=True,
            chunks_processed=len(chunks),
            file_name=os.path.basename(document.file_path)
        )

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        return DocumentProcessResponse(
            success=False,
            chunks_processed=0,
            file_name=os.path.basename(document.file_path),
            error=str(e)
        )

@router.get("/documents/status")
async def get_documents_status():
    """Get status of documents in vector store."""
    try:
        # Use our working get_collection_info method
        info = vector_store.get_collection_info()  # Remove await!
        
        # Get sample vectors to verify search
        sample_results = None
        if info.get("vectors_count", 0) > 0:
            # Try a test search
            test_embedding = await openai_service.create_embeddings(["test query"])
            sample_results = vector_store.search_similar(  # Remove await!
                query_embedding=test_embedding[0],
                limit=1
            )

        return {
            "collection_info": info,
            "vectors_count": info.get("vectors_count", 0),
            "has_searchable_vectors": bool(sample_results),
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Error getting document status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

@router.get("/vector-search/test")
async def test_vector_search(query: str):
    """Test vector search functionality with a specific query."""
    try:
        # Step 1: Test embedding creation
        try:
            query_embedding = await openai_service.create_embeddings([query])
            embedding_status = f"Embeddings created: {len(query_embedding)} vectors, dimension: {len(query_embedding[0])}"
        except Exception as e:
            return {
                "status": "error",
                "error": f"Embedding creation failed: {str(e)}",
                "step": "embedding_creation"
            }
        
        # Step 2: Test vector search (remove await!)
        try:
            results = vector_store.search_similar(
                query_embedding=query_embedding[0],
                limit=3
            )
            search_status = f"Search completed: {len(results)} results"
        except Exception as e:
            return {
                "status": "error", 
                "error": f"Vector search failed: {str(e)}",
                "step": "vector_search",
                "embedding_status": embedding_status
            }
        
        return {
            "query": query,
            "embedding_status": embedding_status,
            "search_status": search_status,
            "results": results,
            "result_count": len(results),
            "status": "ok"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "step": "general_error"
        }

@router.post("/chat/clear/{session_id}")
async def clear_chat_history(session_id: str) -> dict:
    """
    Clear chat history for a session.
    """
    try:
        success = await chat_service.clear_history(session_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
            [0] * 3072,  # dummy vector
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
    
@router.get("/debug/collection")
async def debug_collection():
    """Debug endpoint to check collection status."""
    try:
        # Check if collection exists
        collections = vector_store.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if settings.QDRANT_COLLECTION_NAME in collection_names:
            # Get collection info (now synchronous)
            info = vector_store.get_collection_info()  # Remove await!
            
            # Try a simple search (now synchronous)
            dummy_vector = [0.1] * 3072
            search_results = vector_store.search_similar(dummy_vector, limit=5)  # Remove await!
            
            return {
                "collection_exists": True,
                "collection_info": info,
                "sample_search_results": len(search_results),
                "collections_available": collection_names
            }
        else:
            return {
                "collection_exists": False,
                "collections_available": collection_names,
                "expected_collection": settings.QDRANT_COLLECTION_NAME
            }
    except Exception as e:
        return {"error": str(e)}
    
@router.get("/debug/settings")
async def debug_settings():
    """Check current settings."""
    try:
        return {
            "qdrant_host": settings.QDRANT_HOST,
            "collection_name": settings.QDRANT_COLLECTION_NAME,
            "has_api_key": bool(settings.QDRANT_API_KEY),
            "api_key_length": len(settings.QDRANT_API_KEY) if settings.QDRANT_API_KEY else 0
        }
    except Exception as e:
        return {"error": str(e)}
    
@router.get("/debug/qdrant-connection")
async def debug_qdrant_connection():
    """Test basic Qdrant connection."""
    try:
        # Test basic connection
        collections = vector_store.client.get_collections()
        
        return {
            "connection_status": "success",
            "available_collections": [c.name for c in collections.collections],
            "total_collections": len(collections.collections)
        }
    except Exception as e:
        return {
            "connection_status": "failed",
            "error": str(e),
            "error_type": type(e).__name__
        }
    

@router.post("/debug/create-collection")
async def create_collection_debug():
    """Manually create the Qdrant collection."""
    try:
        # First, let's see what collections exist
        collections = vector_store.client.get_collections()
        existing = [c.name for c in collections.collections]
        
        # Delete Fred collection if it exists
        if settings.QDRANT_COLLECTION_NAME in existing:
            vector_store.client.delete_collection(settings.QDRANT_COLLECTION_NAME)
        
        # Create new collection
        vector_store.client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=1536,
                distance=Distance.COSINE,
                hnsw_config={
                    "m": 16,
                    "ef_construct": 200,
                    "full_scan_threshold": 10000,
                },
                on_disk=True
            )
        )
        
        # Verify it was created
        new_collections = vector_store.client.get_collections()
        new_existing = [c.name for c in new_collections.collections]
        
        return {
            "success": True,
            "message": f"Collection '{settings.QDRANT_COLLECTION_NAME}' created",
            "collections_before": existing,
            "collections_after": new_existing,
            "collection_created": settings.QDRANT_COLLECTION_NAME in new_existing
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@router.get("/debug/settings")
async def debug_settings():
    """Check current settings."""
    return {
        "qdrant_host": settings.QDRANT_HOST,
        "collection_name": settings.QDRANT_COLLECTION_NAME,
        "has_api_key": bool(settings.QDRANT_API_KEY),
        "api_key_length": len(settings.QDRANT_API_KEY) if settings.QDRANT_API_KEY else 0
    }

@router.get("/debug/simple-test")
async def simple_test():
    """Simple test to check what's working."""
    try:
        # Test basic access
        client_test = "Can access client: " + str(type(vector_store.client))
        
        # Test get collections
        collections = vector_store.client.get_collections()
        collections_test = f"Collections: {[c.name for c in collections.collections]}"
        
        # Test if Fred collection exists
        fred_exists = settings.QDRANT_COLLECTION_NAME in [c.name for c in collections.collections]
        
        return {
            "client_test": client_test,
            "collections_test": collections_test,
            "fred_exists": fred_exists,
            "collection_name": settings.QDRANT_COLLECTION_NAME,
            "status": "basic_tests_passed"
        }
    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "status": "basic_tests_failed"
        }

@router.get("/debug/test-specific-methods")
async def test_specific_methods():
    """Test the specific methods that are failing."""
    results = {}
    
    # Test 1: get_collection_info
    try:
        info = vector_store.get_collection_info()
        results["get_collection_info"] = {
            "status": "success",
            "result": info
        }
    except Exception as e:
        results["get_collection_info"] = {
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__
        }
    
    # Test 2: search_similar with correct 3072 dimensions
    try:
        dummy_vector = [0.1] * 3072  # Changed from 1536 to 3072
        search_results = vector_store.search_similar(dummy_vector, limit=2)
        results["search_similar"] = {
            "status": "success",
            "result_count": len(search_results),
            "results": search_results
        }
    except Exception as e:
        results["search_similar"] = {
            "status": "failed", 
            "error": str(e),
            "error_type": type(e).__name__
        }
    
    # Test 3: Direct client call (will still fail due to Pydantic issue)
    try:
        direct_info = vector_store.client.get_collection(settings.QDRANT_COLLECTION_NAME)
        results["direct_client_call"] = {
            "status": "success",
            "vectors_count": direct_info.vectors_count,
            "points_count": direct_info.points_count
        }
    except Exception as e:
        results["direct_client_call"] = {
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__
        }
    
    return results


@router.post("/debug/recreate-collection")
async def recreate_collection():
    """Recreate collection with correct dimensions for text-embedding-3-large."""
    try:
        # Delete existing collection
        try:
            vector_store.client.delete_collection(settings.QDRANT_COLLECTION_NAME)
            delete_status = "Old collection deleted"
        except:
            delete_status = "No existing collection to delete"
        
        # Create new collection with 3072 dimensions for text-embedding-3-large
        vector_store.client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=3072,  # Changed from 1536 to 3072
                distance=Distance.COSINE,
                hnsw_config={
                    "m": 16,
                    "ef_construct": 200,
                    "full_scan_threshold": 10000,
                },
                on_disk=True
            )
        )
        
        # Verify creation
        collections = vector_store.client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        return {
            "success": True,
            "delete_status": delete_status,
            "collection_recreated": settings.QDRANT_COLLECTION_NAME in collection_names,
            "new_dimension": 3072,
            "message": "Collection recreated with correct dimensions for text-embedding-3-large"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/debug/vector-count")
async def check_vector_count():
    """Simple check of vector count."""
    try:
        # Try a search to see how many results we can get
        dummy_vector = [0.1] * 3072
        search_results = vector_store.search_similar(dummy_vector, limit=100)
        
        return {
            "search_result_count": len(search_results),
            "status": "success",
            "note": "This shows how many vectors are actually stored"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }

@router.post("/debug/emergency-reset")
async def emergency_reset():
    """Emergency reset of the collection."""
    try:
        # Delete collection completely
        try:
            vector_store.client.delete_collection(settings.QDRANT_COLLECTION_NAME)
            delete_status = "Collection deleted"
        except Exception as e:
            delete_status = f"Delete failed: {str(e)}"
        
        # Recreate with correct dimensions
        vector_store.client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=3072,  # Correct dimensions
                distance=Distance.COSINE,
                hnsw_config={
                    "m": 16,
                    "ef_construct": 200,
                    "full_scan_threshold": 10000,
                },
                on_disk=True
            )
        )
        
        # Test basic operations
        collections = vector_store.client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        # Test search on empty collection
        dummy_vector = [0.1] * 3072
        search_test = vector_store.search_similar(dummy_vector, limit=1)
        
        return {
            "delete_status": delete_status,
            "collection_recreated": settings.QDRANT_COLLECTION_NAME in collection_names,
            "search_test": f"Search works: {len(search_test)} results",
            "status": "reset_complete"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "reset_failed"
        }

@router.get("/debug/direct-search-test")
async def direct_search_test():
    """Direct test bypassing problematic methods."""
    try:
        # Direct client search
        dummy_vector = [0.1] * 3072
        search_result = vector_store.client.search(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=dummy_vector,
            limit=1
        )
        
        return {
            "direct_search_works": True,
            "result_count": len(search_result),
            "collection_name": settings.QDRANT_COLLECTION_NAME
        }
    except Exception as e:
        return {
            "direct_search_works": False,
            "error": str(e)
        }

@router.get("/debug/qdrant-health")
async def debug_qdrant_health():
    """Check Qdrant Cloud health and performance."""
    try:
        import time
        start_time = time.time()
        
        # Test basic connectivity
        collections = vector_store.client.get_collections()
        connection_time = time.time() - start_time
        
        # Test search performance
        start_time = time.time()
        dummy_vector = [0.1] * 3072
        search_results = vector_store.search_similar(dummy_vector, limit=1)
        search_time = time.time() - start_time
        
        # Test small write performance
        start_time = time.time()
        test_point = [models.PointStruct(
            id="health-check-test",
            vector=dummy_vector,
            payload={"test": "health_check", "timestamp": datetime.utcnow().isoformat()}
        )]
        
        vector_store.client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=test_point,
            wait=True
        )
        write_time = time.time() - start_time
        
        # Clean up test point
        vector_store.client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=models.PointIdsList(points=["health-check-test"])
        )
        
        return {
            "status": "healthy",
            "connection_time_ms": round(connection_time * 1000, 2),
            "search_time_ms": round(search_time * 1000, 2),
            "write_time_ms": round(write_time * 1000, 2),
            "collections_count": len(collections.collections),
            "performance_rating": "good" if write_time < 2 else "slow" if write_time < 10 else "poor"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "recommendation": "Check Qdrant Cloud dashboard for issues"
        }