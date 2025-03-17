import pytest
from fastapi.testclient import TestClient
from app.core.error import ChatbotException
import json

class TestChatEndpoints:
    """Test suite for chat-related endpoints."""

    def test_chat_endpoint_success(
        self,
        test_client: TestClient,
        test_message: dict,
        mock_chat_service
    ):
        """Test successful chat message processing."""
        response = test_client.post(
            "/api/chat",
            json=test_message
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "confidence" in data
        assert "needs_human" in data
        assert isinstance(data["confidence"], float)
        assert isinstance(data["needs_human"], bool)

    def test_chat_endpoint_invalid_input(
        self,
        test_client: TestClient
    ):
        """Test chat endpoint with invalid input."""
        # Test with empty message
        response = test_client.post(
            "/api/chat",
            json={"message": "", "session_id": "test"}
        )
        assert response.status_code == 422

        # Test with missing session_id
        response = test_client.post(
            "/api/chat",
            json={"message": "test"}
        )
        assert response.status_code == 422

        # Test with message too long
        response = test_client.post(
            "/api/chat",
            json={"message": "x" * 1001, "session_id": "test"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_service_error(
        self,
        test_client: TestClient,
        test_message: dict,
        mock_chat_service
    ):
        """Test chat endpoint when service throws error."""
        mock_chat_service.process_message.side_effect = ChatbotException(
            "Test error"
        )
        
        response = test_client.post(
            "/api/chat",
            json=test_message
        )
        
        assert response.status_code == 500
        assert "detail" in response.json()

    def test_clear_history_success(
        self,
        test_client: TestClient,
        mock_chat_service
    ):
        """Test successful history clearing."""
        response = test_client.post(
            "/api/chat/clear/test_session"
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_clear_history_error(
        self,
        test_client: TestClient,
        mock_chat_service
    ):
        """Test history clearing when error occurs."""
        mock_chat_service.clear_history.side_effect = Exception("Test error")
        
        response = test_client.post(
            "/api/chat/clear/test_session"
        )
        
        assert response.status_code == 500

    def test_health_check(
        self,
        test_client: TestClient,
        mock_openai_service,
        mock_vector_store
    ):
        """Test health check endpoint."""
        response = test_client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "openai_status" in data
        assert "vector_store_status" in data