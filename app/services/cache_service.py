from typing import Any, Optional, Dict
import time
from app.core.logger import logger
import hashlib
import json
import asyncio
from collections import OrderedDict

class CacheItem:
    def __init__(self, value: Any, expire_time: float):
        self.value = value
        self.expire_time = expire_time
        self.hits = 0

class LRUCache:
    """LRU Cache implementation with expiration."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheItem] = OrderedDict()
        self._cleanup_lock = asyncio.Lock()
        
    def _generate_key(self, key_data: Any) -> str:
        """Generate consistent cache key."""
        if isinstance(key_data, str):
            data = key_data
        else:
            data = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    async def get(self, key_data: Any) -> Optional[Any]:
        """Get item from cache."""
        key = self._generate_key(key_data)
        now = time.time()
        
        if key in self.cache:
            item = self.cache[key]
            if item.expire_time > now:
                # Update LRU order and hit count
                self.cache.move_to_end(key)
                item.hits += 1
                return item.value
            else:
                # Remove expired item
                del self.cache[key]
        
        return None

    async def set(
        self,
        key_data: Any,
        value: Any,
        expire_seconds: int = 3600
    ) -> None:
        """Set item in cache."""
        key = self._generate_key(key_data)
        now = time.time()
        
        # Create new cache item
        self.cache[key] = CacheItem(value, now + expire_seconds)
        self.cache.move_to_end(key)
        
        # Remove oldest items if cache is too large
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    async def cleanup(self) -> None:
        """Remove expired items."""
        async with self._cleanup_lock:
            now = time.time()
            expired_keys = [
                key for key, item in self.cache.items()
                if item.expire_time <= now
            ]
            for key in expired_keys:
                del self.cache[key]

class CacheService:
    """Service for managing different types of caches."""
    
    def __init__(self):
        # Cache for frequent questions/responses
        self.response_cache = LRUCache(max_size=1000)
        
        # Cache for embeddings
        self.embedding_cache = LRUCache(max_size=5000)
        
        # Cache for document chunks
        self.document_cache = LRUCache(max_size=2000)
        
        # Remove the automatic task creation since there's no event loop
        # asyncio.create_task(self._periodic_cleanup())
        
        # Track last cleanup time to do periodic cleanup during regular operations
        self.last_cleanup_time = time.time()
        self.cleanup_interval = 300  # 5 minutes in seconds
    
    async def check_cleanup(self):
        """Check if cleanup is needed and perform it if necessary."""
        current_time = time.time()
        if current_time - self.last_cleanup_time > self.cleanup_interval:
            try:
                await self.response_cache.cleanup()
                await self.embedding_cache.cleanup()
                await self.document_cache.cleanup()
                logger.debug("Cache cleanup completed")
                self.last_cleanup_time = current_time
            except Exception as e:
                logger.error(f"Error during cache cleanup: {e}")
    
    async def cache_response(
        self,
        query: str,
        response: Dict[str, Any],
        expire_seconds: int = 3600
    ) -> None:
        """Cache a query response."""
        try:
            # Normalize query by removing extra whitespace and converting to lowercase
            normalized_query = " ".join(query.lower().split())
            await self.response_cache.set(normalized_query, response, expire_seconds)
            await self.check_cleanup()  # Check if cleanup needed
        except Exception as e:
            logger.error(f"Error caching response: {e}")

    async def get_cached_response(
        self,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached response for a query."""
        try:
            normalized_query = " ".join(query.lower().split())
            result = await self.response_cache.get(normalized_query)
            await self.check_cleanup()  # Check if cleanup needed
            return result
        except Exception as e:
            logger.error(f"Error retrieving cached response: {e}")
            return None

    # Same pattern for other methods - add await self.check_cleanup() to each
    
    async def cache_embedding(
        self,
        text: str,
        embedding: list,
        expire_seconds: int = 86400
    ) -> None:
        """Cache text embedding."""
        try:
            await self.embedding_cache.set(text, embedding, expire_seconds)
            await self.check_cleanup()
        except Exception as e:
            logger.error(f"Error caching embedding: {e}")

    async def get_cached_embedding(
        self,
        text: str
    ) -> Optional[list]:
        """Get cached embedding for text."""
        try:
            result = await self.embedding_cache.get(text)
            await self.check_cleanup()
            return result
        except Exception as e:
            logger.error(f"Error retrieving cached embedding: {e}")
            return None

    async def cache_document_chunk(
        self,
        chunk_id: str,
        chunk_data: Dict[str, Any],
        expire_seconds: int = 86400
    ) -> None:
        """Cache document chunk data."""
        try:
            await self.document_cache.set(chunk_id, chunk_data, expire_seconds)
            await self.check_cleanup()
        except Exception as e:
            logger.error(f"Error caching document chunk: {e}")

    async def get_cached_document_chunk(
        self,
        chunk_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached document chunk."""
        try:
            result = await self.document_cache.get(chunk_id)
            await self.check_cleanup()
            return result
        except Exception as e:
            logger.error(f"Error retrieving cached document chunk: {e}")
            return None

    # Keep this method for potential future use, but it won't be called automatically
    async def _periodic_cleanup(self, interval_seconds: int = 300):
        """Periodically clean up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                await self.response_cache.cleanup()
                await self.embedding_cache.cleanup()
                await self.document_cache.cleanup()
                logger.debug("Cache cleanup completed")
            except Exception as e:
                logger.error(f"Error during cache cleanup: {e}")

# Don't forget to import time if it's not already imported
# import time

cache_service = CacheService()