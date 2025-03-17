from fastapi import APIRouter, HTTPException
from app.services.interaction_analysis import interaction_analysis
from app.core.logger import logger
from typing import Dict, Any

router = APIRouter()

@router.get("/analysis/session/{session_id}")
async def get_session_analysis(session_id: str) -> Dict[str, Any]:
    """Get analysis for a specific session."""
    try:
        analysis = await interaction_analysis.get_session_analysis(session_id)
        if "error" in analysis:
            # Change to more user-friendly message
            raise HTTPException(
                status_code=404,
                detail=f"No chat interactions found for session ID: {session_id}. Please make some chat requests first."
            )
        return analysis
    except Exception as e:
        logger.error(f"Error getting session analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/global")
async def get_global_analysis() -> Dict[str, Any]:
    """Get global analysis of all interactions."""
    try:
        analysis = await interaction_analysis.get_global_analysis()
        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])
        return analysis
    except Exception as e:
        logger.error(f"Error getting global analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))