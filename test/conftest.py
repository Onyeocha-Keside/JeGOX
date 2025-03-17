import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.openai_service import OpenAIService
from app.services.vector_store import VectorStore
from app.services.chat_service import ChatService
from unittest.mock import AsyncMock, patch

@pytest.fixture
def test_client():
    """Create a test client for our FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service for testing."""
    with patch('app.services.openai_service.OpenAIService') as mock:
        service = mock.return_value
        
        # Mock embeddings creation
        service.create_embeddings = AsyncMock(return_value=[[0.1] * 1536])
        
        # Mock chat completion
        service.get_chat_completion = AsyncMock(
            return_value="This is a test response"
        )
        
        # Mock confidence calculation
        service.calculate_confidence = AsyncMock(return_value=0.9)
        
        yield service

@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    with patch('app.services.vector_store.VectorStore') as mock:
        store = mock.return_value
        
        # Mock search
        store.search_similar = AsyncMock(
            return_value=[{
                'text': 'Test context',
                'score': 0.9,
                'metadata': {'source': 'test_doc.pdf'}
            }]
        )
        
        # Mock storage
        store.store_embeddings = AsyncMock(return_value=True)
        
        yield store

@pytest.fixture
def mock_chat_service(mock_openai_service, mock_vector_store):
    """Mock chat service for testing."""
    with patch('app.services.chat_service.ChatService') as mock:
        service = mock.return_value
        
        # Mock message processing
        service.process_message = AsyncMock(
            return_value={
                'response': 'Test response',
                'confidence': 0.9,
                'needs_human': False,
                'context_used': True,
                'encrypted_history': 'encrypted_data'
            }
        )
        
        # Mock history clearing
        service.clear_history = AsyncMock(return_value=True)
        
        yield service

@pytest.fixture
def test_message():
    """Sample test message."""
    return {
        "message": "test message",
        "session_id": "test_session",
        "metadata": {"test": True}
    }

@pytest.fixture
def test_document():
    """Sample test document data."""
    return {
        "file_path": "tests/test_files/test_doc.pdf",
        "metadata": {"category": "test"}
    }