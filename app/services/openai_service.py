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
                model="text-embedding-3-small",
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
        """
        Get chat completion from OpenAI.
        
        Args:
            messages: List of message dictionaries
            context: Additional context from similar documents
            temperature: Optional temperature override
            
        Returns:
            Generated response text
        """
        try:
            # Create system message with Fred's personality and context
            system_message = {
                "role": "system",
                "content": (
                    "You are Fred, a professionally-casual and calm AI assistant. "
                    "You provide concise, accurate responses while maintaining a friendly tone. "
                    "You must:\n"
                    "1. Keep responses short and relevant\n"
                    "2. Express uncertainty when confidence is below 90%\n"
                    "3. Suggest human support when uncertainty is high\n"
                    "4. Never discuss competitor information or make promises\n"
                    "5. Never share internal company information\n"
                    "6. Never process sensitive customer data\n\n"
                )
            }

            # Add context if provided
            if context:
                system_message["content"] += f"\nRelevant context:\n{context}"

            # Combine system message with conversation history
            all_messages = [system_message] + messages

            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=all_messages,
                temperature=temperature or settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS
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