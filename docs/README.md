# Company Chatbot Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Installation Guide](#installation-guide)
3. [API Documentation](#api-documentation)
4. [Architecture](#architecture)
5. [Configuration](#configuration)
6. [Security Features](#security-features)
7. [Monitoring and Analytics](#monitoring-and-analytics)
8. [Troubleshooting](#troubleshooting)

## System Overview

The Company Chatbot is an AI-powered chatbot system built using FastAPI and OpenAI. It provides intelligent responses to customer queries using company documentation as context.

### Key Features
- Context-aware responses using company documentation
- Conversation management and history
- Performance optimizations with caching
- Security features and input validation
- Monitoring and analytics
- Error handling and recovery
- Batch processing capabilities

### Technology Stack
- **Backend Framework**: FastAPI
- **AI Model**: OpenAI GPT-3.5 Turbo
- **Vector Database**: Qdrant
- **Document Processing**: PyPDF2, python-docx
- **Monitoring**: Custom monitoring service
- **Security**: Custom security implementation
- **Caching**: Custom LRU cache implementation

## Installation Guide

### Prerequisites
```bash
- Python 3.8+
- pip
- Virtual environment (recommended)
```

### Setup Steps

1. Clone the repository:
```bash
git clone <repository-url>
cd company-chatbot
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Start the application:
```bash
uvicorn app.main:app --reload
```

## API Documentation

### Chat Endpoints

#### Send Message
```http
POST /api/chat
Content-Type: application/json

{
    "message": "string",
    "session_id": "string",
    "metadata": {
        "user_id": "string",
        "custom_data": {}
    }
}
```

#### Clear Chat History
```http
POST /api/chat/clear/{session_id}
```

### Document Processing

#### Process Document
```http
POST /api/documents/process
Content-Type: application/json

{
    "file_path": "string",
    "metadata": {}
}
```

### Conversation Management

#### Create Conversation
```http
POST /api/conversations/create
Content-Type: application/json

{
    "metadata": {
        "user_id": "string",
        "user_type": "string"
    }
}
```

#### Export Conversation
```http
GET /api/conversations/{session_id}/export?format=json
```

### Analytics Endpoints

#### Get Analytics Summary
```http
GET /api/analytics/summary
```

## Architecture

### Component Overview
```
app/
├── api/             # API routes and endpoints
├── core/            # Core functionality
├── services/        # Business logic services
└── utils/           # Utility functions

services/
├── openai_service.py      # OpenAI integration
├── vector_store.py        # Vector database operations
├── chat_service.py        # Chat processing
├── monitoring_service.py  # System monitoring
├── cache_service.py       # Caching
└── batch_service.py       # Batch processing
```

### Data Flow
1. User sends message through API
2. Message is validated and processed
3. Relevant context is retrieved from vector store
4. OpenAI generates response
5. Response is cached and returned
6. Conversation is updated and managed

## Configuration

### Environment Variables
```env
# OpenAI Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
MAX_TOKENS=150
TEMPERATURE=0.7

# Vector Database Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=company_docs

# App Configuration
APP_NAME="Fred - Company Assistant"
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## Security Features

### Implemented Security Measures
1. Input validation
2. Rate limiting
3. Content security
4. Conversation encryption
5. Error handling
6. Request validation

### Best Practices
- Keep API keys secure
- Update dependencies regularly
- Monitor error logs
- Implement proper authentication
- Regular security audits

## Monitoring and Analytics

### Available Metrics
- Response times
- Token usage
- Confidence scores
- Error rates
- Request volumes
- Cache hit rates

### Monitoring Endpoints
- `/api/analytics/summary`
- `/api/analytics/response-times`
- `/api/analytics/confidence`
- `/api/analytics/errors`
- `/api/analytics/usage`

## Troubleshooting

### Common Issues

1. OpenAI API Issues
```python
# Check OpenAI API key
if openai_error:
    - Verify API key in .env
    - Check API quotas
    - Verify network connectivity
```

2. Vector Store Issues
```python
# Check Qdrant connection
if vector_store_error:
    - Verify Qdrant is running
    - Check collection exists
    - Verify port configuration
```

3. Performance Issues
```python
# If slow responses:
    - Check cache hit rates
    - Monitor token usage
    - Verify batch processing
    - Check response times
```

### Debug Tips
1. Enable debug logging
2. Check application logs
3. Monitor system resources
4. Use health check endpoint
5. Review analytics dashboard