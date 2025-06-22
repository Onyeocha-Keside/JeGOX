# JéGO AI Chatbot

A sophisticated AI-powered chatbot API built with FastAPI, OpenAI GPT, and Qdrant vector database for intelligent document-based conversations about JéGO products and services.

## 🚀 Features

### Core Functionality
- **Intelligent Chat System**: Context-aware conversations using OpenAI GPT models
- **Document Processing**: RAG (Retrieval-Augmented Generation) with vector embeddings
- **Session Management**: JWT-based ticket system for stateless session handling
- **Security**: Rate limiting, input validation, and conversation encryption
- **Monitoring**: Comprehensive analytics and performance tracking
- **Caching**: In-memory response caching for improved performance

### Advanced Capabilities
- **Multi-Document Search**: Intelligent context retrieval from multiple documents
- **Confidence Scoring**: AI response confidence assessment
- **Token Management**: Smart context truncation to stay within OpenAI limits
- **Batch Processing**: Efficient document embedding generation
- **Real-time Analytics**: Performance metrics and usage tracking

## 🏗️ Architecture

### Core Components

**FastAPI Application (`main.py`)**
- CORS middleware with security headers
- Request timing and error handling
- Global exception handlers
- Development server configuration

**Chat Router (`api/routes/chat.py`)**
- JWT-based session management with ticket system
- Document processing endpoints
- Vector search testing utilities
- Health check endpoints

**Services Layer**
- **Chat Service**: Message processing and conversation management
- **OpenAI Service**: GPT completions and embeddings generation
- **Vector Store**: Qdrant cloud integration for similarity search
- **Monitoring**: Analytics and performance tracking

## 🔧 Setup & Installation

### Prerequisites
- Python 3.8+
- OpenAI API key
- Qdrant Cloud instance

### Environment Variables
Create a `.env` file with:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-turbo

# Qdrant Configuration
QDRANT_HOST=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION_NAME=jego_documents

# Security
ENCRYPTION_KEY=your-32-character-secret-key
TICKET_EXPIRY_MINUTES=60
TICKET_ALGORITHM=HS256

# Application
APP_NAME=JéGO AI Chatbot
ENVIRONMENT=development
TEMPERATURE=0.7
```

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd jego-chatbot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Initialize the database**
```bash
# The vector store will auto-create collections on first run
python -m app.services.vector_store
```

4. **Process documents (optional)**
```bash
# Place documents in data/raw/ directory
python process_documents.py
```

5. **Run the application**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📋 API Documentation

### Chat Endpoints

#### Send Message
```http
POST /api/chat
Content-Type: application/json

{
  "message": "Tell me about JéGO vehicles",
  "ticket": "optional-session-ticket",
  "metadata": {}
}
```

**Response:**
```json
{
  "response": "AI generated response",
  "confidence": 0.9,
  "needs_human": false,
  "context_used": true,
  "encrypted_history": "...",
  "ticket": "new-session-ticket",
  "is_new_session": false
}
```

#### Clear Chat History
```http
POST /api/chat/clear/{session_id}
```

### Document Management

#### Process Document
```http
POST /api/documents/process
Content-Type: application/json

{
  "file_path": "/path/to/document.pdf",
  "metadata": {
    "filename": "document.pdf",
    "type": "pdf",
    "source": "manual_upload"
  }
}
```

#### Get Document Status
```http
GET /api/documents/status
```

### Debugging Endpoints

#### Test Vector Search
```http
GET /api/vector-search/test?query=your search query
```

#### Health Check
```http
GET /api/
```

## 🎫 Session Management System

### JWT-Based Ticketing

The chatbot uses a sophisticated JWT-based ticketing system for stateless session management:

**Key Features:**
- **Stateless Design**: No server-side session storage required
- **Auto-Expiring Tickets**: Configurable expiration (default: 60 minutes)
- **Message Counting**: Tracks conversation length
- **Context Preservation**: Maintains user context across requests

**Ticket Lifecycle:**
1. **New Session**: Client sends message without ticket
2. **Ticket Generation**: Server creates JWT with session data
3. **Ticket Refresh**: Each message validates and refreshes the ticket
4. **Auto-Expiry**: Expired tickets automatically create new sessions

**Implementation Details:**
```python
class TicketService:
    def generate_ticket(self, user_id=None, context=None, expires_in_minutes=60):
        """Generate JWT ticket with session data"""
        
    def validate_and_refresh_ticket(self, ticket):
        """Validate existing ticket and return refreshed version"""
```

### Migration from Analytics

**Important Note**: The ticketing system has been completely refactored in the chat service but **has not yet been implemented in the analytics system**. The analytics endpoints may still use older session management patterns while the monitoring system is being developed.

## 📊 Vector Store Implementation

### Qdrant Cloud Integration

**Configuration:**
- **Embedding Model**: `text-embedding-3-large` (3072 dimensions)
- **Distance Metric**: Cosine similarity
- **Storage**: Cloud-based with local disk optimization

**Key Features:**
```python
class VectorStore:
    def store_embeddings(self, embeddings, metadata):
        """Store document chunks with batch processing"""
        
    def search_similar(self, query_embedding, limit=5):
        """Find semantically similar documents"""
        
    def get_collection_info(self):
        """Get collection statistics and health"""
```

**Optimizations:**
- Batch processing for large document uploads
- Retry logic for cloud reliability
- Token-aware context building
- Duplicate detection via content hashing

## 🧠 Chat Service Architecture

### Intelligent Context Retrieval

The chat service implements sophisticated context management:

**Multi-Strategy Search:**
1. **Direct Embedding Search**: Primary similarity search
2. **Expanded Query Generation**: Automatic query expansion for comprehensive results
3. **Product Diversity**: Ensures results cover multiple JéGO products
4. **Token Management**: Intelligent truncation to fit OpenAI limits

**Context Prioritization:**
```python
def _prioritize_documents(self, docs, message):
    """Priority scoring based on:
    - Direct product name matches (1.5x boost)
    - Technical specification queries (1.3x boost)
    - Comprehensive overview queries (1.2x boost)
    """
```

### Conversation Management

**Features:**
- Limited conversation history (last 5 exchanges)
- Context-aware responses
- Confidence scoring based on available context
- Automatic cache management

## 🔒 Security Features

### Input Validation & Rate Limiting
- Message length validation (1-1000 characters)
- Rate limiting per IP address
- Input sanitization and validation
- CORS protection with security headers

### Data Protection
- Conversation history encryption
- Secure JWT token handling
- No persistent session storage
- API key protection

## 📈 Monitoring & Analytics

### Performance Tracking
- Response time monitoring
- Confidence score tracking
- Context usage analytics
- Cache hit rate analysis

### Health Monitoring
- OpenAI API status checking
- Vector store connectivity
- Collection status verification
- Endpoint health checks

## 🛠️ Development Tools

### Debug Endpoints

The API includes comprehensive debugging tools:

```http
# Test Qdrant connection
GET /api/debug/qdrant-connection

# Check collection status
GET /api/debug/collection

# Test specific vector operations
GET /api/debug/test-specific-methods

# Recreate collection with correct dimensions
POST /api/debug/recreate-collection

# Emergency reset (use with caution)
POST /api/debug/emergency-reset
```

### Document Processing Script

Use `process_documents.py` for batch document upload:

```python
# Place documents in data/raw/
# Supports: .pdf, .docx, .doc, .txt
python process_documents.py
```

## 🚀 Deployment

### Production Configuration

1. **Environment Setup**
```bash
ENVIRONMENT=production
OPENAI_MODEL=gpt-4-turbo
TICKET_EXPIRY_MINUTES=120
```

2. **Security Headers**
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Cache-Control: no-store, no-cache

3. **Performance Optimization**
- GZip compression for responses
- In-memory caching layer
- Batch processing for embeddings

### Monitoring Setup

The application includes built-in monitoring that tracks:
- API response times
- Token usage and costs
- Error rates and types
- User interaction patterns

## 🔄 Future Roadmap

### Planned Features
- [ ] Complete analytics system integration with new ticketing
- [ ] Advanced conversation analytics
- [ ] Multi-language support
- [ ] Document version management
- [ ] Advanced caching strategies

### Current Development
- **Monitoring System**: Comprehensive analytics and performance tracking system currently in development
- **Analytics Migration**: Updating analytics endpoints to use the new JWT ticketing system

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Install development dependencies
4. Run tests before submitting PR

### Code Standards
- FastAPI best practices
- Async/await patterns
- Comprehensive error handling
- Security-first development


---

**Built with ❤️ for JéGO intelligent solutions**
