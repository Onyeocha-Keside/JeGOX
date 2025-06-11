from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from typing import List, Dict, Any
import numpy as np
import asyncio
from app.config import get_settings
from app.core.logger import logger
from app.core.error import VectorStoreError
#from qdrant_client.http.models import HnswConfig
import uuid
import hashlib
from datetime import datetime

settings = get_settings()

class VectorStore:
    def __init__(self):
        """Initialize Qdrant client for cloud."""
        try:
            self.client = QdrantClient(
                url=settings.QDRANT_HOST,
                api_key=settings.QDRANT_API_KEY,
            )
            self._ensure_collection_exists()
            logger.info("Successfully connected to Qdrant Cloud")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            raise VectorStoreError("Vector store initialization failed")

    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist."""
        try:
            # Get existing collections
            collections_response = self.client.get_collections()
            collection_names = [c.name for c in collections_response.collections]
            
            logger.info(f"Existing collections: {collection_names}")
            logger.info(f"Looking for collection: {settings.QDRANT_COLLECTION_NAME}")
            
            if settings.QDRANT_COLLECTION_NAME not in collection_names:
                logger.info(f"Creating collection: {settings.QDRANT_COLLECTION_NAME}")
                
                self.client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=3072,
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
                collections_after = self.client.get_collections()
                names_after = [c.name for c in collections_after.collections]
                
                if settings.QDRANT_COLLECTION_NAME in names_after:
                    logger.info(f"✅ Successfully created collection: {settings.QDRANT_COLLECTION_NAME}")
                else:
                    logger.error(f"❌ Collection creation failed: {settings.QDRANT_COLLECTION_NAME}")
                    raise Exception("Collection creation verification failed")
            else:
                logger.info(f"✅ Collection {settings.QDRANT_COLLECTION_NAME} already exists")
                
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise VectorStoreError("Failed to create/verify collection")


    async def store_embeddings(
        self, 
        embeddings: List[List[float]], 
        metadata: List[Dict[str, Any]]
    ) -> bool:
        """Store document embeddings with metadata in small batches."""
        try:
            # Validate dimensions first
            if embeddings and len(embeddings[0]) != 3072:
                raise Exception(f"Embedding dimension mismatch: got {len(embeddings[0])}, expected 3072")
            
            # Use smaller batches to prevent timeouts
            batch_size = 20  # Much smaller batches for Qdrant Cloud
            total_stored = 0
            
            logger.info(f"Storing {len(embeddings)} embeddings in batches of {batch_size}")
            
            for i in range(0, len(embeddings), batch_size):
                batch_embeddings = embeddings[i:i + batch_size]
                batch_metadata = metadata[i:i + batch_size]
                
                points = [
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload={
                            **meta,
                            'chunk_hash': hashlib.sha256(meta.get('text', '').encode()).hexdigest(),
                            'created_at': datetime.utcnow().isoformat()
                        }
                    )
                    for embedding, meta in zip(batch_embeddings, batch_metadata)
                ]
                
                # Store with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        self.client.upsert(
                            collection_name=settings.QDRANT_COLLECTION_NAME,
                            points=points,
                            wait=True
                        )
                        total_stored += len(batch_embeddings)
                        logger.info(f"✅ Stored batch {i//batch_size + 1}/{(len(embeddings)-1)//batch_size + 1}: {total_stored}/{len(embeddings)} embeddings")
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"⚠️  Batch {i//batch_size + 1} failed (attempt {attempt + 1}), retrying: {str(e)}")
                            await asyncio.sleep(2)  # Wait before retry
                        else:
                            logger.error(f"❌ Batch {i//batch_size + 1} failed after {max_retries} attempts: {str(e)}")
                            raise
                
                # Small delay between batches to be nice to Qdrant Cloud
                await asyncio.sleep(0.5)
            
            logger.info(f"🎉 Successfully stored all {total_stored} embeddings in Qdrant Cloud")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store embeddings: {e}")
            raise VectorStoreError(f"Failed to store embeddings: {str(e)}")
    def search_similar(
        self, 
        query_embedding: List[float], 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar documents based on query embedding."""
        try:
            search_result = self.client.search(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query_vector=query_embedding,
                limit=limit
            )
            
            results = []
            for hit in search_result:
                result = {
                    'score': hit.score,
                    **hit.payload
                }
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Failed to search similar documents: {e}")
            raise VectorStoreError("Failed to search similar documents")

    async def delete_collection(self) -> bool:
        """Delete the entire collection."""
        try:
            self.client.delete_collection(settings.QDRANT_COLLECTION_NAME)
            logger.info(f"Deleted collection: {settings.QDRANT_COLLECTION_NAME}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise VectorStoreError("Failed to delete collection")

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the current collection using search."""
        try:
            # Instead of using get_collection (which has Pydrant issues),
            # let's use a search-based approach to get collection info
            
            # Try a simple search to see if collection has vectors
            dummy_vector = [0.0] * 3072
            search_result = self.client.search(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query_vector=dummy_vector,
                limit=1
            )
            
            # Try to get collection existence
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            collection_exists = settings.QDRANT_COLLECTION_NAME in collection_names
            
            # Estimate vectors count based on search capability
            vectors_count = len(search_result) if search_result else 0
            
            return {
                "vectors_count": vectors_count,
                "points_count": vectors_count,  # Approximation
                "status": "green" if collection_exists else "red",
                "collection_exists": collection_exists,
                "note": "Using search-based info due to client compatibility"
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise VectorStoreError("Failed to get collection info")

# Create a global instance
vector_store = VectorStore()