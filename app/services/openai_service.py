from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.core.logger import logger
from app.core.error import OpenAIError

settings = get_settings()

class OpenAIService:
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-large",
                input=texts
            )
            return [embedding.embedding for embedding in response.data]
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e}")
            raise OpenAIError(f"Embedding creation failed: {str(e)}")

    async def get_chat_completion(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Get chat completion with robust token management."""
        try:
            # Build base system message
            base_system_content = (
                "You are Ovo, a knowledgeable AI assistant for JéGO products and services. "
                "When users ask for comprehensive information, provide detailed responses using "
                "ALL relevant information from the context. Structure responses clearly with "
                "sections, bullet points, or numbered lists when appropriate. "
                "Be thorough and technical when discussing specifications."
            )

            # Prepare messages without context first
            messages_content = "\n".join([msg.get('content', '') for msg in messages])
            base_tokens = (len(base_system_content) + len(messages_content)) // 4
            
            # Calculate available tokens for context
            max_total_tokens = 15000  # Safety buffer under 16385
            available_for_context = max_total_tokens - base_tokens - 1000  # Reserve for response
            
            logger.info(f"Base tokens: ~{base_tokens}, Available for context: ~{available_for_context}")

            # Truncate context if needed
            final_context = context
            if context and available_for_context > 0:
                context_tokens = len(context) // 4
                if context_tokens > available_for_context:
                    logger.warning(f"Context too large ({context_tokens} tokens), truncating to {available_for_context}")
                    max_context_chars = available_for_context * 4
                    final_context = context[:max_context_chars] + "\n\n[Context truncated due to length - showing most relevant information]"
                else:
                    logger.info(f"Context fits: {context_tokens} tokens")
            elif available_for_context <= 0:
                logger.error("No room for context - using minimal system message")
                final_context = None

            # Build final system message
            if final_context:
                system_content = f"{base_system_content}\n\nRelevant context:\n{final_context}"
            else:
                system_content = base_system_content

            system_message = {"role": "system", "content": system_content}
            all_messages = [system_message] + messages

            # Final token check
            total_chars = sum(len(msg.get('content', '')) for msg in all_messages)
            estimated_tokens = total_chars // 4
            
            logger.info(f"Final estimated tokens: ~{estimated_tokens}")

            # Ensure we have reasonable max_tokens
            max_tokens = max(1000, min(4000, 15000 - estimated_tokens))
            logger.info(f"Using max_tokens: {max_tokens}")

            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=all_messages,
                temperature=temperature or settings.TEMPERATURE,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to get chat completion: {e}")
            raise OpenAIError(f"Chat completion failed: {str(e)}")

    def calculate_confidence(self, response: str) -> float:
        """
        Calculate confidence score based on language markers.
        
        Args:
            response: Generated response text
            
        Returns:
            Confidence score between 0 and 1
        """
        # List of uncertainty markers
        uncertainty_markers = [
            "i'm not sure",
            "might be",
            "possibly",
            "perhaps",
            "may",
            "could be",
            "uncertain",
            "unclear",
            "don't know",
            "not confident"
        ]
        
        # Convert to lowercase for comparison
        response_lower = response.lower()
        
        # Count uncertainty markers
        uncertainty_count = sum(
            1 for marker in uncertainty_markers 
            if marker in response_lower
        )
        
        # Calculate base confidence score
        base_confidence = max(0, 1 - (uncertainty_count * 0.1))
        
        # Adjust for response length (shorter responses might be less certain)
        length_factor = min(1, len(response) / 100)  # Normalize by typical length
        
        # Combine factors
        final_confidence = base_confidence * length_factor
        
        return round(final_confidence, 2)

openai_service = OpenAIService()