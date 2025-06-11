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

    async def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a batch of texts using OpenAI."""
        try:
            from app.services.openai_service import openai_service
            
            logger.info(f"Processing embedding batch of {len(texts)} texts")
            
            # Simple token check for single admin use
            total_chars = sum(len(text) for text in texts)
            estimated_tokens = total_chars / 4  # Rough estimate
            
            if estimated_tokens > 250000:  # Stay under OpenAI 300k limit
                logger.warning(f"Batch too large ({estimated_tokens:.0f} tokens), splitting...")
                
                # Split and process recursively
                mid_point = len(texts) // 2
                first_half = await self._get_embeddings(texts[:mid_point])
                second_half = await self._get_embeddings(texts[mid_point:])
                
                return first_half + second_half
            
            # Process with OpenAI
            embeddings = await openai_service.create_embeddings(texts)
            
            logger.info(f"Successfully created {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Batch embedding creation failed: {e}")
            raise Exception(f"Embedding batch failed: {str(e)}")

    async def _process_single_document(
        self,
        document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single document."""
        # Implement your document processing logic here
        pass

    # async def add_embedding_task_bulk(self, texts: List[str]) -> List[List[float]]:
    # """Process multiple texts efficiently using batching."""
    # try:
    #     # For large lists, process in chunks to respect batch size limits
    #     if len(texts) <= self.embedding_processor.batch_size:
    #         # Small list - process as single batch
    #         tasks = [self.add_embedding_task(text) for text in texts]
    #         return await asyncio.gather(*tasks)
    #     else:
    #         # Large list - process in optimal chunks
    #         chunk_size = self.embedding_processor.batch_size
    #         all_embeddings = []
            
    #         for i in range(0, len(texts), chunk_size):
    #             chunk_texts = texts[i:i + chunk_size]
    #             logger.info(f"Processing chunk {i//chunk_size + 1}/{(len(texts)-1)//chunk_size + 1}")
                
    #             chunk_tasks = [self.add_embedding_task(text) for text in chunk_texts]
    #             chunk_embeddings = await asyncio.gather(*chunk_tasks)
    #             all_embeddings.extend(chunk_embeddings)
            
    #         return all_embeddings
            
    # except Exception as e:
    #     logger.error(f"Bulk embedding processing failed: {e}")
    #     raise
    
batch_service = BatchService()