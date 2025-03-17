from typing import List, Dict, Any, Callable, Awaitable
import asyncio
from app.core.logger import logger
from datetime import datetime
import time

class BatchProcessor:
    """Handles batch processing of tasks."""
    
    def __init__(
        self,
        batch_size: int = 10,
        max_wait_time: float = 0.5
    ):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.current_batch: List[Dict[str, Any]] = []
        self.last_process_time = time.time()
        self._lock = asyncio.Lock()

    async def add_to_batch(
        self,
        item: Dict[str, Any],
        processor: Callable[[List[Dict[str, Any]]], Awaitable[List[Any]]]
    ) -> Any:
        """
        Add item to batch and process if batch is ready.
        
        Args:
            item: Item to process
            processor: Async function to process batch
            
        Returns:
            Processed result for the item
        """
        async with self._lock:
            self.current_batch.append(item)
            current_time = time.time()
            
            should_process = (
                len(self.current_batch) >= self.batch_size or
                current_time - self.last_process_time >= self.max_wait_time
            )
            
            if should_process:
                batch_to_process = self.current_batch
                self.current_batch = []
                self.last_process_time = current_time
                
                try:
                    results = await processor(batch_to_process)
                    # Return result corresponding to this item
                    item_index = batch_to_process.index(item)
                    return results[item_index]
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    raise
            
            # If batch is not ready, wait for results
            future = asyncio.Future()
            item['future'] = future
            return await future

class BatchService:
    """Service for managing different types of batch processing."""
    
    def __init__(self):
        # Batch processor for embeddings
        self.embedding_processor = BatchProcessor(
            batch_size=50,  # Process up to 50 embeddings at once
            max_wait_time=0.1  # Wait max 100ms for batch to fill
        )
        
        # Batch processor for document chunks
        self.document_processor = BatchProcessor(
            batch_size=20,  # Process up to 20 documents at once
            max_wait_time=0.5  # Wait max 500ms for batch to fill
        )
        
        # Initialize processing tasks
        self.processing_tasks: List[asyncio.Task] = []

    async def process_embedding_batch(
        self,
        batch: List[Dict[str, Any]]
    ) -> List[Any]:
        """Process a batch of embedding requests."""
        try:
            # Extract texts from batch
            texts = [item['text'] for item in batch]
            
            # Get embeddings (implement your embedding logic here)
            results = await self._get_embeddings(texts)
            
            # Resolve futures for waiting items
            for item, result in zip(batch, results):
                if 'future' in item:
                    item['future'].set_result(result)
            
            return results
        except Exception as e:
            logger.error(f"Error processing embedding batch: {e}")
            # Reject all futures in case of error
            for item in batch:
                if 'future' in item:
                    item['future'].set_exception(e)
            raise

    async def process_document_batch(
        self,
        batch: List[Dict[str, Any]]
    ) -> List[Any]:
        """Process a batch of document processing requests."""
        try:
            results = []
            # Process documents in parallel
            tasks = [
                self._process_single_document(item['document'])
                for item in batch
            ]
            results = await asyncio.gather(*tasks)
            
            # Resolve futures for waiting items
            for item, result in zip(batch, results):
                if 'future' in item:
                    item['future'].set_result(result)
            
            return results
        except Exception as e:
            logger.error(f"Error processing document batch: {e}")
            for item in batch:
                if 'future' in item:
                    item['future'].set_exception(e)
            raise

    async def add_embedding_task(
        self,
        text: str
    ) -> List[float]:
        """Add text to embedding batch."""
        return await self.embedding_processor.add_to_batch(
            {'text': text},
            self.process_embedding_batch
        )

    async def add_document_task(
        self,
        document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add document to processing batch."""
        return await self.document_processor.add_to_batch(
            {'document': document},
            self.process_document_batch
        )

    async def _get_embeddings(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """Get embeddings for a batch of texts."""
        # Implement your embedding logic here
        pass

    async def _process_single_document(
        self,
        document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single document."""
        # Implement your document processing logic here
        pass

batch_service = BatchService()