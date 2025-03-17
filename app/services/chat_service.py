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
                    "You are Fred, a knowledgeable and confident AI assistant for JéGO. "
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
        threshold: float = 0.3,
        max_tokens: int = 8000
    ) -> Optional[str]:
        """
        Get relevant context from vector store with token limit.
        """
        try:
            # Create embedding for message
            message_embedding = (await openai_service.create_embeddings([message]))[0]

            # Search for similar documents
            similar_docs = await vector_store.search_similar(
                query_embedding=message_embedding,
                limit=3  # Get top 3 most relevant documents
            )

            if not similar_docs:
                return None

            # Combine relevant context with size limit
            context_parts = []
            total_length = 0
            
            for doc in similar_docs:
                if doc['score'] > threshold:
                    text = doc.get('text', '')
                    # Rough estimate of tokens (words/0.75)
                    estimated_tokens = len(text.split()) / 0.75
                    
                    if total_length + estimated_tokens > max_tokens:
                        break
                        
                    context_parts.append(text)
                    total_length += estimated_tokens

            return "\n\n".join(context_parts) if context_parts else None

        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return None

    async def clear_history(self, session_id: str) -> bool:
        """Clear conversation history for a session."""
        try:
            if session_id in self.conversation_history:
                del self.conversation_history[session_id]
            return True
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            return False

    async def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a session."""
        return self.conversation_history.get(session_id, [])

chat_service = ChatService()