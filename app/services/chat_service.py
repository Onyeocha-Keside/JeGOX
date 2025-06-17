from typing import List, Dict, Any, Optional
import time
from app.services.openai_service import openai_service
from app.services.vector_store import vector_store
from app.services.monitoring_service import monitoring_service
from app.services.cache_service import cache_service
from app.services.interaction_analysis import interaction_analysis
from app.core.security import security_manager
from app.core.logger import logger
from app.core.error import ChatbotException

class ChatService:
    def __init__(self):
        """Initialize chat service."""
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}
        
    async def process_message(
        self,
        session_id: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and generate a response.
        """
        try:
            start_time = time.time()
            
            # Check cache first
            cached_response = await cache_service.get_cached_response(message)
            if cached_response:
                logger.info("Cache hit for message")
                
                # Analyze cached interaction
                analysis = await interaction_analysis.analyze_interaction(
                    message=message,
                    session_id=session_id,
                    response=cached_response["response"],
                    context_used=cached_response["context_used"],
                    confidence=cached_response["confidence"]
                )
                cached_response["analysis"] = analysis
                
                await monitoring_service.record_response_time(start_time, time.time())
                await monitoring_service.record_user_interaction("cache_hit")
                return cached_response
            
            # Validate input
            if not await security_manager.validate_input(message):
                raise ChatbotException("Invalid input detected")

            # Get embedding for user message
            message_embedding = (await openai_service.create_embeddings([message]))[0]

            # Get relevant context with token limit
            context = await self.get_relevant_context(message)

            # Prepare system message with better instructions
            system_message = {
                "role": "system",
                "content": (
                    "You are Ovo, a knowledgeable and confident AI assistant for JéGO. "
                    "Your responses should be direct, clear, and informative. "
                    "When using information from the provided context, be confident in your responses. "
                    "Focus on being helpful and accurate, using the context to provide specific details. "
                    "Only express uncertainty when no relevant information is found in the context. "
                    "Keep responses concise and to the point."
                )
            }

            # Add context to system message if available
            if context:
                system_message["content"] += f"\n\nContext: {context}"

            # Initialize conversation history if needed
            if session_id not in self.conversation_history:
                self.conversation_history[session_id] = []

            # Prepare messages for chat with limited history
            messages = [system_message]
            if len(self.conversation_history[session_id]) > 5:  # Keep only last 5 messages
                self.conversation_history[session_id] = self.conversation_history[session_id][-5:]
            messages.extend(self.conversation_history[session_id])
            messages.append({"role": "user", "content": message})

            # Get response from OpenAI
            response = await openai_service.get_chat_completion(
                messages=messages,
                context=context
            )

            # Update conversation history
            self.conversation_history[session_id].extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": response}
            ])

            # Calculate confidence based on context
            confidence = 0.9 if context else 0.5

            # Analyze interaction
            analysis = await interaction_analysis.analyze_interaction(
                message=message,
                session_id=session_id,
                response=response,
                context_used=bool(context),
                confidence=confidence
            )

            # Prepare response data
            response_data = {
                "response": response,
                "confidence": confidence,
                "needs_human": confidence < 0.4,
                "context_used": bool(context),
                "encrypted_history": security_manager.encrypt_conversation(str(messages)),
                "analysis": analysis
            }

            # Cache the response
            await cache_service.cache_response(message, response_data)

            # Record metrics
            end_time = time.time()
            await monitoring_service.record_response_time(start_time, end_time)
            await monitoring_service.record_confidence_score(confidence)
            await monitoring_service.record_context_usage(bool(context))
            await monitoring_service.record_user_interaction("chat_message")
            
            return response_data

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise ChatbotException(f"Failed to process message: {str(e)}")

    async def get_relevant_context(
        self,
        message: str,
        threshold: float = 0.25,
        max_context_tokens: int = 6000  # Stay well under OpenAI limit
    ) -> Optional[str]:
        """Get comprehensive context with intelligent token management."""
        try:
            # Create embedding for the main message
            message_embedding = (await openai_service.create_embeddings([message]))[0]

            # Strategy 1: Direct search with higher limit
            main_search = vector_store.search_similar(
                query_embedding=message_embedding,
                limit=20  # Get many candidates
            )

            all_results = []
            all_results.extend(main_search)

            # Strategy 2: Expand search for comprehensive queries
            expanded_queries = self._generate_expanded_queries(message)
            
            for expanded_query in expanded_queries[:3]:  # Limit expanded queries
                try:
                    expanded_embedding = (await openai_service.create_embeddings([expanded_query]))[0]
                    expanded_results = vector_store.search_similar(
                        query_embedding=expanded_embedding,
                        limit=10
                    )
                    all_results.extend(expanded_results)
                except Exception as e:
                    logger.warning(f"Expanded search failed for '{expanded_query}': {e}")
                    continue

            if not all_results:
                return None

            # Remove duplicates and filter by threshold
            unique_results = {}
            for doc in all_results:
                if doc['score'] > threshold:
                    doc_id = doc.get('chunk_hash', hash(doc.get('text', '')[:100]))
                    if doc_id not in unique_results or doc['score'] > unique_results[doc_id]['score']:
                        unique_results[doc_id] = doc

            # Sort by relevance score
            filtered_docs = sorted(unique_results.values(), key=lambda x: x['score'], reverse=True)
            
            logger.info(f"Found {len(filtered_docs)} unique relevant documents")

            # INTELLIGENT TOKEN MANAGEMENT
            return self._build_token_managed_context(filtered_docs, max_context_tokens, message)

        except Exception as e:
            logger.error(f"Error getting comprehensive context: {e}")
            return None

    def _build_token_managed_context(
        self, 
        docs: List[Dict], 
        max_tokens: int,
        original_message: str
    ) -> str:
        """Build context within token limits using intelligent prioritization."""
        
        context_parts = []
        total_tokens = 0
        products_covered = set()
        
        # Prioritize docs by relevance and diversity
        prioritized_docs = self._prioritize_documents(docs, original_message)
        
        for doc in prioritized_docs:
            text = doc.get('text', '').strip()
            if not text or len(text) < 50:
                continue
                
            # Estimate tokens (rough: 1 token ≈ 4 characters)
            estimated_tokens = len(text) // 4
            
            # Check if adding this would exceed limit
            if total_tokens + estimated_tokens > max_tokens:
                # Try to fit a truncated version for very important docs
                if doc['score'] > 0.7 and total_tokens < max_tokens * 0.8:
                    remaining_tokens = max_tokens - total_tokens - 100  # Buffer
                    max_chars = remaining_tokens * 4
                    truncated_text = text[:max_chars] + "..."
                    
                    context_parts.append(f"[High Relevance] {truncated_text}")
                    total_tokens += len(truncated_text) // 4
                break
            
            # Track product diversity
            filename = doc.get('file_name', '')
            if filename:
                products_covered.add(filename.split('[')[0])  # Get product name
            
            # Add full context
            context_parts.append(text)
            total_tokens += estimated_tokens
            
            logger.debug(f"Added context: {filename} (score: {doc['score']:.3f}, tokens: ~{estimated_tokens})")

        final_context = "\n\n---\n\n".join(context_parts)
        
        logger.info(f"Built context: {len(context_parts)} chunks, ~{total_tokens} tokens, {len(products_covered)} products")
        logger.info(f"Products covered: {', '.join(products_covered)}")
        
        return final_context

    def _prioritize_documents(self, docs: List[Dict], message: str) -> List[Dict]:
        """Prioritize documents for optimal context building."""
        
        message_lower = message.lower()
        
        # Boost scores based on query intent
        for doc in docs:
            filename = doc.get('file_name', '').lower()
            text = doc.get('text', '').lower()
            
            # Boost exact product matches
            if any(term in filename for term in message_lower.split()):
                doc['priority_score'] = doc['score'] * 1.5
            # Boost technical specifications for spec queries
            elif 'specification' in message_lower and 'specification' in text:
                doc['priority_score'] = doc['score'] * 1.3
            # Boost comprehensive content for overview queries
            elif any(word in message_lower for word in ['complete', 'all', 'overview', 'comprehensive']):
                doc['priority_score'] = doc['score'] * 1.2
            else:
                doc['priority_score'] = doc['score']
        
        # Sort by priority score, but also ensure diversity
        sorted_docs = sorted(docs, key=lambda x: x['priority_score'], reverse=True)
        
        # Ensure we get diverse products (not all chunks from same document)
        diverse_docs = []
        seen_products = set()
        
        # First pass: Get highest scoring doc from each product
        for doc in sorted_docs:
            product = doc.get('file_name', '').split('[')[0]
            if product not in seen_products:
                diverse_docs.append(doc)
                seen_products.add(product)
        
        # Second pass: Fill remaining slots with best remaining docs
        remaining_docs = [d for d in sorted_docs if d not in diverse_docs]
        diverse_docs.extend(remaining_docs)
        
        return diverse_docs

    def _generate_expanded_queries(self, message: str) -> List[str]:
        """Generate additional search queries for comprehensive results."""
        message_lower = message.lower()
        expanded_queries = []
        
        # For vehicle/car queries
        if any(word in message_lower for word in ['car', 'vehicle', 'auto', 'transport', 'list']):
            expanded_queries.extend([
                "JéGO Zero electric vehicle",
                "JéGO Skipper truck specifications", 
                "JéGO Skipper van features",
                "JéGO Zero Pro specifications",
                "JéGO Zero Carbon vehicle",
                "JéGO vehicles product catalog",
                "JéGO automotive products"
            ])
        
        # For power/energy queries  
        if any(word in message_lower for word in ['power', 'energy', 'battery', 'charger']):
            expanded_queries.extend([
                "JéGO Power Systems catalog",
                "JéGO Mega Power Pod BESS",
                "JéGO 5-Series EV Charger", 
                "JéGO Charger Systems",
                "JéGO energy storage solutions"
            ])
        
        # For smart city queries
        if any(word in message_lower for word in ['smart', 'city', 'urban']):
            expanded_queries.extend([
                "JéGO Smart Cities solutions",
                "JéGO urban transportation",
                "JéGO smart city transformation"
            ])
        
        # For comprehensive product queries
        if any(word in message_lower for word in ['product', 'all', 'complete', 'full', 'entire']):
            expanded_queries.extend([
                "JéGO product catalog",
                "JéGO complete product line",
                "JéGO all products overview",
                "JéGO product specifications"
            ])
        
        logger.info(f"Generated {len(expanded_queries)} expanded queries for: '{message}'")
        return expanded_queries[:5]  # Limit to avoid too many API calls

chat_service = ChatService()