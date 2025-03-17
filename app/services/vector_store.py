from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from typing import List, Dict, Any
import numpy as np
from app.config import get_settings
from app.core.logger import logger
from app.core.error import VectorStoreError

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
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if settings.QDRANT_COLLECTION_NAME not in collection_names:
                self.client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=1536,  # OpenAI embedding dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {settings.QDRANT_COLLECTION_NAME}")
            else:
                logger.info(f"Collection {settings.QDRANT_COLLECTION_NAME} already exists")
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise VectorStoreError("Failed to create/verify collection")

    async def store_embeddings(
        self, 
        embeddings: List[List[float]], 
        metadata: List[Dict[str, Any]]
    ) -> bool:
        """
        Store document embeddings with metadata.
        
        Args:
            embeddings: List of embedding vectors
            metadata: List of metadata dicts containing document info
            
        Returns:
            bool: True if successful
        """
        try:
            points = [
                models.PointStruct(
                    id=i,
                    vector=embedding,
                    payload=meta
                )
                for i, (embedding, meta) in enumerate(zip(embeddings, metadata))
            ]
            
            self.client.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=points
            )
            logger.info(f"Stored {len(embeddings)} embeddings in Qdrant Cloud")
            return True
        except Exception as e:
            logger.error(f"Failed to store embeddings: {e}")
            raise VectorStoreError("Failed to store embeddings")

    async def search_similar(
        self, 
        query_embedding: List[float], 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents based on query embedding.
        
        Args:
            query_embedding: Query vector
            limit: Number of results to return
            
        Returns:
            List of metadata for most similar documents
        """
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

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the current collection."""
        try:
            collection_info = self.client.get_collection(
                settings.QDRANT_COLLECTION_NAME
            )
            return {
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise VectorStoreError("Failed to get collection info")

# Create a global instance
vector_store = VectorStore()