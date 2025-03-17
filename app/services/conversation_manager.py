from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import asyncio
from app.core.security import security_manager
from app.core.logger import logger
from app.core.error import ChatbotException

class Conversation:
    def __init__(self, session_id: str, metadata: Optional[Dict[str, Any]] = None):
        self.session_id = session_id
        self.messages: List[Dict[str, str]] = []
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.is_active = True
        self.summary: Optional[str] = None
        self.tags: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "is_active": self.is_active,
            "summary": self.summary,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Create conversation instance from dictionary."""
        conv = cls(data["session_id"], data.get("metadata"))
        conv.messages = data["messages"]
        conv.created_at = datetime.fromisoformat(data["created_at"])
        conv.last_updated = datetime.fromisoformat(data["last_updated"])
        conv.is_active = data["is_active"]
        conv.summary = data.get("summary")
        conv.tags = data.get("tags", [])
        return conv

class ConversationManager:
    def __init__(self):
        """Initialize conversation manager."""
        self.conversations: Dict[str, Conversation] = {}
        self.expiry_time = timedelta(hours=24)  # Conversations expire after 24 hours
        self.backup_interval = timedelta(hours=1)  # Backup every hour
        self.max_messages = 100  # Maximum messages per conversation
        
        # Start background tasks
        asyncio.create_task(self._periodic_cleanup())
        asyncio.create_task(self._periodic_backup())

    async def create_conversation(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Create a new conversation."""
        if session_id in self.conversations:
            raise ChatbotException("Conversation already exists")
            
        conversation = Conversation(session_id, metadata)
        self.conversations[session_id] = conversation
        logger.info(f"Created new conversation: {session_id}")
        return conversation

    async def get_conversation(
        self,
        session_id: str,
        create_if_missing: bool = True
    ) -> Optional[Conversation]:
        """Get an existing conversation or create new if specified."""
        conversation = self.conversations.get(session_id)
        
        if not conversation and create_if_missing:
            conversation = await self.create_conversation(session_id)
        
        if conversation:
            # Check if conversation has expired
            if datetime.now() - conversation.last_updated > self.expiry_time:
                await self.archive_conversation(session_id)
                if create_if_missing:
                    conversation = await self.create_conversation(session_id)
                else:
                    return None
                    
        return conversation

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> Conversation:
        """Add a message to a conversation."""
        conversation = await self.get_conversation(session_id)
        
        if len(conversation.messages) >= self.max_messages:
            await self.archive_conversation(session_id)
            conversation = await self.create_conversation(session_id)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        conversation.messages.append(message)
        conversation.last_updated = datetime.now()
        
        # Update summary periodically
        if len(conversation.messages) % 5 == 0:
            await self._update_conversation_summary(conversation)
        
        return conversation

    async def archive_conversation(self, session_id: str) -> bool:
        """Archive a conversation."""
        try:
            conversation = self.conversations.get(session_id)
            if not conversation:
                return False
                
            # Encrypt conversation data
            encrypted_data = security_manager.encrypt_conversation(
                json.dumps(conversation.to_dict())
            )
            
            # Save to archive (implement your storage solution)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversations/archive/{session_id}_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump({"encrypted_data": encrypted_data}, f)
            
            # Remove from active conversations
            del self.conversations[session_id]
            logger.info(f"Archived conversation: {session_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error archiving conversation {session_id}: {e}")
            return False

    async def export_conversation(
        self,
        session_id: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export a conversation in specified format."""
        conversation = await self.get_conversation(session_id, create_if_missing=False)
        if not conversation:
            raise ChatbotException("Conversation not found")
            
        if format == "json":
            return conversation.to_dict()
        elif format == "text":
            return self._format_conversation_as_text(conversation)
        else:
            raise ChatbotException(f"Unsupported export format: {format}")

    async def add_tag(self, session_id: str, tag: str) -> None:
        """Add a tag to a conversation."""
        conversation = await self.get_conversation(session_id)
        if tag not in conversation.tags:
            conversation.tags.append(tag)

    async def _periodic_cleanup(self):
        """Periodically clean up expired conversations."""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                current_time = datetime.now()
                
                for session_id, conversation in list(self.conversations.items()):
                    if current_time - conversation.last_updated > self.expiry_time:
                        await self.archive_conversation(session_id)
                        
            except Exception as e:
                logger.error(f"Error in conversation cleanup: {e}")

    async def _periodic_backup(self):
        """Periodically backup active conversations."""
        while True:
            try:
                await asyncio.sleep(3600)  # Backup every hour
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                backup_data = {
                    session_id: conv.to_dict()
                    for session_id, conv in self.conversations.items()
                }
                
                # Encrypt backup data
                encrypted_backup = security_manager.encrypt_conversation(
                    json.dumps(backup_data)
                )
                
                # Save backup
                filename = f"conversations/backup/backup_{timestamp}.json"
                with open(filename, 'w') as f:
                    json.dump({"encrypted_data": encrypted_backup}, f)
                    
                logger.info("Conversation backup completed")
                
            except Exception as e:
                logger.error(f"Error in conversation backup: {e}")

    async def _update_conversation_summary(self, conversation: Conversation):
        """Update the summary of a conversation."""
        try:
            # Implement summary generation logic here
            # You could use OpenAI to generate a summary of the conversation
            pass
        except Exception as e:
            logger.error(f"Error updating conversation summary: {e}")

    def _format_conversation_as_text(self, conversation: Conversation) -> Dict[str, Any]:
        """Format conversation as readable text."""
        formatted_messages = []
        for msg in conversation.messages:
            timestamp = datetime.fromisoformat(msg["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            formatted_messages.append(
                f"[{timestamp}] {msg['role'].capitalize()}: {msg['content']}"
            )
            
        return {
            "session_id": conversation.session_id,
            "created_at": conversation.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "content": "\n".join(formatted_messages),
            "summary": conversation.summary,
            "tags": conversation.tags
        }

conversation_manager = ConversationManager()