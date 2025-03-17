from datetime import datetime, timedelta
from typing import Dict, List, Any
from app.core.logger import logger
import json
import asyncio
from collections import defaultdict

class MonitoringService:
    def __init__(self):
        """Initialize monitoring service."""
        self.metrics = {
            'response_times': [],
            'token_usage': defaultdict(int),
            'confidence_scores': [],
            'user_interactions': defaultdict(int),
            'error_counts': defaultdict(int),
            'hourly_requests': defaultdict(int),
            'context_usage': defaultdict(int)
        }
        self.current_hour = datetime.now().hour
        
    async def record_response_time(self, start_time: float, end_time: float):
        """Record API response time."""
        response_time = end_time - start_time
        self.metrics['response_times'].append({
            'timestamp': datetime.now().isoformat(),
            'duration': response_time
        })
        
        # Keep only last 1000 response times
        if len(self.metrics['response_times']) > 1000:
            self.metrics['response_times'] = self.metrics['response_times'][-1000:]
            
        await self._check_response_time_alert(response_time)

    async def record_token_usage(self, tokens_used: int, model: str):
        """Record token usage by model."""
        self.metrics['token_usage'][model] += tokens_used
        
        # Alert if token usage is high
        if self.metrics['token_usage'][model] > 1000000:  # 1M tokens
            logger.warning(f"High token usage detected for {model}")

    async def record_confidence_score(self, score: float):
        """Record confidence scores."""
        self.metrics['confidence_scores'].append({
            'timestamp': datetime.now().isoformat(),
            'score': score
        })
        
        # Keep only last 1000 scores
        if len(self.metrics['confidence_scores']) > 1000:
            self.metrics['confidence_scores'] = self.metrics['confidence_scores'][-1000:]
        
        # Alert on low confidence trend
        await self._check_confidence_trend()

    async def record_user_interaction(self, interaction_type: str):
        """Record user interaction types."""
        self.metrics['user_interactions'][interaction_type] += 1
        current_hour = datetime.now().hour
        
        # Reset hourly counters if hour changed
        if self.current_hour != current_hour:
            self.metrics['hourly_requests'] = defaultdict(int)
            self.current_hour = current_hour
        
        self.metrics['hourly_requests'][current_hour] += 1

    async def record_error(self, error_type: str):
        """Record error occurrences."""
        self.metrics['error_counts'][error_type] += 1
        
        # Alert on high error rate
        if self.metrics['error_counts'][error_type] > 100:  # Threshold
            logger.error(f"High error rate detected for {error_type}")

    async def record_context_usage(self, context_used: bool):
        """Record whether context was used in responses."""
        status = 'with_context' if context_used else 'without_context'
        self.metrics['context_usage'][status] += 1

    async def get_analytics(self) -> Dict[str, Any]:
        """Get analytics summary."""
        try:
            total_requests = sum(self.metrics['hourly_requests'].values())
            avg_response_time = sum(r['duration'] for r in self.metrics['response_times'][-100:]) / 100 if self.metrics['response_times'] else 0
            avg_confidence = sum(s['score'] for s in self.metrics['confidence_scores'][-100:]) / 100 if self.metrics['confidence_scores'] else 0
            
            return {
                'total_requests': total_requests,
                'average_response_time': round(avg_response_time, 3),
                'average_confidence': round(avg_confidence, 2),
                'token_usage_summary': dict(self.metrics['token_usage']),
                'error_summary': dict(self.metrics['error_counts']),
                'context_usage_summary': dict(self.metrics['context_usage']),
                'hourly_request_distribution': dict(self.metrics['hourly_requests'])
            }
        except Exception as e:
            logger.error(f"Error generating analytics: {e}")
            return {}

    async def _check_response_time_alert(self, response_time: float):
        """Check and alert for slow response times."""
        if response_time > 5.0:  # 5 seconds threshold
            logger.warning(f"Slow response time detected: {response_time:.2f}s")

    async def _check_confidence_trend(self):
        """Check and alert for low confidence trend."""
        recent_scores = [s['score'] for s in self.metrics['confidence_scores'][-10:]]
        if recent_scores and sum(recent_scores) / len(recent_scores) < 0.7:
            logger.warning("Low confidence trend detected in recent responses")

    async def export_metrics(self, file_path: str):
        """Export metrics to JSON file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.metrics, f, indent=2)
            logger.info(f"Metrics exported to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")

    async def start_periodic_export(self, interval_minutes: int = 60):
        """Start periodic export of metrics."""
        while True:
            await asyncio.sleep(interval_minutes * 60)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await self.export_metrics(f"metrics_{timestamp}.json")

monitoring_service = MonitoringService()