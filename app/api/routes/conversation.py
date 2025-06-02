# from fastapi import APIRouter, HTTPException, Query
# from typing import List, Optional, Dict, Any
# from app.services.conversation_manager import conversation_manager
# from app.core.logger import logger
# from datetime import datetime
# from pydantic import BaseModel

# router = APIRouter()

# class ConversationExport(BaseModel):
#     """Model for conversation export response."""
#     session_id: str
#     created_at: str
#     content: str
#     summary: Optional[str] = None
#     tags: List[str] = []

# class ConversationMetadata(BaseModel):
#     """Model for conversation metadata."""
#     user_id: Optional[str] = None
#     user_type: Optional[str] = None
#     custom_data: Optional[Dict[str, Any]] = None

# @router.post("/conversations/create")
# async def create_conversation(metadata: Optional[ConversationMetadata] = None):
#     """Create a new conversation."""
#     try:
#         session_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(metadata)}"
#         conversation = await conversation_manager.create_conversation(
#             session_id,
#             metadata.dict() if metadata else None
#         )
#         return {"session_id": conversation.session_id}
#     except Exception as e:
#         logger.error(f"Error creating conversation: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/conversations/{session_id}")
# async def get_conversation(session_id: str):
#     """Get conversation details."""
#     try:
#         conversation = await conversation_manager.get_conversation(
#             session_id,
#             create_if_missing=False
#         )
#         if not conversation:
#             raise HTTPException(status_code=404, detail="Conversation not found")
#         return conversation.to_dict()
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error retrieving conversation: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/conversations/{session_id}/archive")
# async def archive_conversation(session_id: str):
#     """Archive a conversation."""
#     try:
#         success = await conversation_manager.archive_conversation(session_id)
#         if not success:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Conversation not found or already archived"
#             )
#         return {"status": "archived"}
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error archiving conversation: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/conversations/{session_id}/export")
# async def export_conversation(
#     session_id: str,
#     format: str = Query("json", regex="^(json|text)$")
# ) -> ConversationExport:
#     """Export a conversation in specified format."""
#     try:
#         exported = await conversation_manager.export_conversation(session_id, format)
#         return ConversationExport(**exported)
#     except Exception as e:
#         logger.error(f"Error exporting conversation: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/conversations/{session_id}/tags/{tag}")
# async def add_conversation_tag(session_id: str, tag: str):
#     """Add a tag to a conversation."""
#     try:
#         await conversation_manager.add_tag(session_id, tag)
#         return {"status": "tag_added"}
#     except Exception as e:
#         logger.error(f"Error adding tag: {e}")
#         raise HTTPException(status_code=500, detail=str(e))