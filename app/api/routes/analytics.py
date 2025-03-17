from fastapi import APIRouter, HTTPException
from app.services.monitoring_service import monitoring_service
from app.core.logger import logger
from typing import Dict, Any
from datetime import datetime

router = APIRouter()

@router.get("/analytics/summary")
async def get_analytics_summary() -> Dict[str, Any]:
    """Get summary of system analytics."""
    try:
        return await monitoring_service.get_analytics()
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")

@router.get("/analytics/response-times")
async def get_response_times() -> Dict[str, Any]:
    """Get detailed response time metrics."""
    try:
        response_times = monitoring_service.metrics['response_times']
        return {
            "average": sum(r['duration'] for r in response_times) / len(response_times) if response_times else 0,
            "max": max((r['duration'] for r in response_times), default=0),
            "min": min((r['duration'] for r in response_times), default=0),
            "total_requests": len(response_times),
            "detailed_times": response_times[-100:]  # Last 100 responses
        }
    except Exception as e:
        logger.error(f"Error getting response times: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve response times")

@router.get("/analytics/confidence")
async def get_confidence_metrics() -> Dict[str, Any]:
    """Get confidence score metrics."""
    try:
        confidence_scores = monitoring_service.metrics['confidence_scores']
        scores = [s['score'] for s in confidence_scores]
        return {
            "average_confidence": sum(scores) / len(scores) if scores else 0,
            "highest_confidence": max(scores, default=0),
            "lowest_confidence": min(scores, default=0),
            "total_responses": len(scores),
            "recent_scores": confidence_scores[-50:]  # Last 50 scores
        }
    except Exception as e:
        logger.error(f"Error getting confidence metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve confidence metrics")

@router.get("/analytics/errors")
async def get_error_metrics() -> Dict[str, Any]:
    """Get error metrics."""
    try:
        return {
            "error_counts": dict(monitoring_service.metrics['error_counts']),
            "total_errors": sum(monitoring_service.metrics['error_counts'].values())
        }
    except Exception as e:
        logger.error(f"Error getting error metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve error metrics")

@router.get("/analytics/usage")
async def get_usage_metrics() -> Dict[str, Any]:
    """Get system usage metrics."""
    try:
        return {
            "token_usage": dict(monitoring_service.metrics['token_usage']),
            "hourly_requests": dict(monitoring_service.metrics['hourly_requests']),
            "context_usage": dict(monitoring_service.metrics['context_usage'])
        }
    except Exception as e:
        logger.error(f"Error getting usage metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve usage metrics")