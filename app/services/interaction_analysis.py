from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime
import json
from app.core.logger import logger
from app.services.openai_service import openai_service

class InteractionAnalysis:
    def __init__(self):
        """Initialize interaction analysis service."""
        self.interactions = defaultdict(list)
        self.topic_categories = {
            'product_inquiry': ['product', 'price', 'features', 'specifications'],
            'technical_support': ['help', 'issue', 'problem', 'error', 'not working'],
            'pricing': ['cost', 'price', 'payment', 'discount'],
            'general_info': ['company', 'about', 'location', 'contact']
        }
        
    async def analyze_interaction(
        self,
        message: str,
        session_id: str,
        response: str,
        context_used: bool,
        confidence: float
    ) -> Dict[str, Any]:
        """Analyze a single interaction."""
        try:
            # Prepare analysis prompt
            analysis_prompt = [
                {
                    "role": "system",
                    "content": "Analyze this customer interaction and categorize it. Identify: "
                              "1. Main topic/category "
                              "2. Customer intent "
                              "3. Specific product/service mentioned "
                              "4. Sentiment "
                              "5. Key terms used "
                              "Return as JSON format."
                }
            ]
            
            interaction_context = f"Customer message: {message}\nBot response: {response}"
            analysis_prompt.append({"role": "user", "content": interaction_context})
            
            # Get analysis from OpenAI
            analysis_response = await openai_service.get_chat_completion(
                messages=analysis_prompt
            )
            
            try:
                analysis_data = json.loads(analysis_response)
            except json.JSONDecodeError:
                # Fallback to basic analysis if JSON parsing fails
                analysis_data = self._basic_analysis(message)
            
            # Store analysis
            analysis_record = {
                'timestamp': datetime.now().isoformat(),
                'message': message,
                'response': response,
                'context_used': context_used,
                'confidence': confidence,
                'analysis': analysis_data
            }
            
            self.interactions[session_id].append(analysis_record)
            return analysis_data
            
        except Exception as e:
            logger.error(f"Error analyzing interaction: {e}")
            return self._basic_analysis(message)
    
    def _basic_analysis(self, message: str) -> Dict[str, Any]:
        """Perform basic analysis when advanced analysis fails."""
        analysis = {
            'category': 'unknown',
            'intent': 'general_inquiry',
            'product_mentioned': None,
            'sentiment': 'neutral',
            'key_terms': []
        }
        
        # Basic category detection
        message_lower = message.lower()
        for category, keywords in self.topic_categories.items():
            if any(keyword in message_lower for keyword in keywords):
                analysis['category'] = category
                break
        
        return analysis
    
    async def get_session_analysis(self, session_id: str) -> Dict[str, Any]:
        """Get analysis for entire session."""
        try:
            session_interactions = self.interactions[session_id]
            if not session_interactions:
                return {"error": "No interactions found for session"}
            
            categories = [inter['analysis'].get('category') for inter in session_interactions]
            intents = [inter['analysis'].get('intent') for inter in session_interactions]
            
            return {
                'session_id': session_id,
                'interaction_count': len(session_interactions),
                'common_categories': self._get_most_common(categories),
                'common_intents': self._get_most_common(intents),
                'context_usage_rate': sum(1 for i in session_interactions if i['context_used']) / len(session_interactions),
                'average_confidence': sum(i['confidence'] for i in session_interactions) / len(session_interactions),
                'interactions': session_interactions
            }
        except Exception as e:
            logger.error(f"Error getting session analysis: {e}")
            return {"error": str(e)}
    
    async def get_global_analysis(self) -> Dict[str, Any]:
        """Get global analysis of all interactions."""
        try:
            all_interactions = [
                interaction
                for session in self.interactions.values()
                for interaction in session
            ]
            
            if not all_interactions:
                return {"error": "No interactions recorded"}
            
            categories = [inter['analysis'].get('category') for inter in all_interactions]
            intents = [inter['analysis'].get('intent') for inter in all_interactions]
            products = [inter['analysis'].get('product_mentioned') for inter in all_interactions if inter['analysis'].get('product_mentioned')]
            
            return {
                'total_interactions': len(all_interactions),
                'unique_sessions': len(self.interactions),
                'top_categories': self._get_most_common(categories, 5),
                'top_intents': self._get_most_common(intents, 5),
                'top_products': self._get_most_common(products, 5),
                'context_usage_rate': sum(1 for i in all_interactions if i['context_used']) / len(all_interactions),
                'average_confidence': sum(i['confidence'] for i in all_interactions) / len(all_interactions)
            }
        except Exception as e:
            logger.error(f"Error getting global analysis: {e}")
            return {"error": str(e)}
    
    def _get_most_common(self, items: List[str], limit: int = 3) -> List[Dict[str, Any]]:
        """Get most common items with their counts."""
        if not items:
            return []
            
        count_dict = defaultdict(int)
        for item in items:
            if item:
                count_dict[item] += 1
                
        sorted_items = sorted(count_dict.items(), key=lambda x: x[1], reverse=True)
        return [{'item': item, 'count': count} for item, count in sorted_items[:limit]]

interaction_analysis = InteractionAnalysis()