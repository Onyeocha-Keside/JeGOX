import pytest
from app.services.openai_service import OpenAIService
from app.services.vector_store import VectorStore
from app.services.chat_service import ChatService
from app.core.error import OpenAIError, VectorStoreError, ChatbotException
from unittest.mock import AsyncMock, patch

class TestOpenAIService:
    """Test suite for OpenAI service."""

    @pytest.mark.asyncio
    async def test_create_embeddings(self, mock_openai_service):
        """Test embedding creation."""
        texts = ["Test text 1", "Test text 2"]
        embeddings = await mock_openai_service.create_embeddings(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) > 0
        assert len(embeddings[0]) == 1536  # OpenAI embedding dimension

    @pytest.mark.asyncio
    async def test_chat_completion(self, mock_openai_service):
        """Test chat completion."""
        messages = [{"role": "user", "content": "Test message"}]
        response = await mock_openai_service.get_chat_completion(messages)
        
        assert isinstance(response, str)
        assert len(response) > 0

    def test_confidence_calculation(self, mock_openai_service):
        """Test confidence score calculation."""
        # Test high confidence response
        high_conf = mock_openai_service.calculate_confidence(
            "This is a definitive answer."
        )
        assert high_conf > 0.8
        
        # Test low confidence response
        low_conf = mock_openai_service.calculate_confidence(
            "I'm not sure, but maybe..."
        )
        assert low_conf < 0.8

class TestVectorStore:
    """Test suite for vector store."""

    @pytest.mark.asyncio
    async def test_store_embeddings(self, mock_vector_store):
        """Test storing embeddings."""
        embeddings = [[0.1] * 1536]
        metadata = [{"text": "Test", "source": "test.pdf"}]
        
        result = await mock_vector_store.store_embeddings(embeddings, metadata)
        assert result is True

    @pytest.mark.asyncio
    async def test_search_similar(self, mock_vector_store):
        """Test similarity search."""
        query_embedding = [0.1] * 1536
        results = await mock_vector_store.search_similar(query_embedding)
        
        assert isinstance(results, list)
        assert len(results) > 0
        assert "text" in results[0]
        assert "score" in results[0]

class TestChatService:
    """Test suite for chat service."""

    @pytest.fixture
    def chat_service(self, mock_openai_service, mock_vector_store):
        """Create chat service instance with mocked dependencies."""
        return ChatService()

    @pytest.mark.asyncio
    async def test_process_message(
        self,
        chat_service,
        mock_chat_service
    ):
        """Test message processing."""
        result = await mock_chat_service.process_message(
            "test_session",
            "Test message"
        )
        
        assert isinstance(result, dict)
        assert "response" in result
        assert "confidence" in result
        assert "needs_human" in result
        assert "context_used" in result
        assert "encrypted_history" in result