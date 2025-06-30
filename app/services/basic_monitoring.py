import time
from datetime import datetime
from typing import Dict

#create class
class BasicMonitor:
    """ A simple monitoring system"""
    def __init__(self):
        #create a list to store conversations
        self.conversations = []
        print("📊 Basic Monitoring has began")

    def record_conversation(self, user_message: str, bot_response: str, response_time: float):
        "record a single conversation"
        conversation = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "bot_response": bot_response,
            "response_time": response_time
        }
        self.conversations.append(conversation)
        #show many conversations have been recorded
        print(f"This amount of conversation has been stored: {len(self.conversations)}")

    def get_stats(self) -> Dict:
        #return a message if there is no conversation
        if not self.conversations:
            return {"Message": "No conversation recorded yet"}
        
        total_conversation = len(self.conversations)
        total_time =sum(conv["response_time"] for conv in self.conversations)
        average_time = total_time / total_conversation

        return {
            "total_conversation": total_conversation,
            "average_response_time": round(average_time,2),
            "latest_conversation": self.conversations[-1]["timestamp"]
        }

basic_monitor = BasicMonitor()




#testing 
if __name__ == "__main__":
    #simulate convo
    #initialize the class
    monitor = BasicMonitor()

    #record some fake convo
    monitor.record_conversation("Hi", "Hello", 1.2)
    monitor.record_conversation("What is AI", "Artificial Inteligence is the ...", 2.0)
    monitor.record_conversation("Thank you", "Youre Welcome", 0.2)


    #get stats
    stats = monitor.get_stats()
    print(f"current stats: {stats}")
