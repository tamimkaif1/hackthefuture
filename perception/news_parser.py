import json
import uuid
from datetime import datetime
from perception.models import NewsSignal

class NewsParser:
    def __init__(self):
        # In a real system, this would connect to RSS feeds or news APIs (e.g., Event Registry)
        self.mock_news_stream = [
            {
                "headline": "Major typhoon hitting Port of Shenzhen",
                "content": "A category 4 typhoon is expected to make landfall near the Port of Shenzhen, halting all maritime operations for at least 72 hours. Serious backlog expected.",
                "source": "Global Logistics Daily",
                "location": "Shenzhen, China",
                "affected_entities": ["Port of Shenzhen", "Maritime Shipping"]
            },
            {
                "headline": "Semiconductor Fab Fire in Taiwan",
                "content": "A localized fire at a major semiconductor fabrication plant in Hsinchu has halted production on the 7nm logic line. Minimal injuries reported, but supply constraints anticipated.",
                "source": "Tech Supply Chain News",
                "location": "Hsinchu, Taiwan",
                "affected_entities": ["Semiconductor Suppliers"]
            },
            {
                "headline": "Red Sea Shipping Disruption Continues",
                "content": "Continued geopolitical tensions have led major carriers to permanently reroute around the Cape of Good Hope, adding 10-14 days to Asia-Europe transit times.",
                "source": "Maritime Executive",
                "location": "Red Sea",
                "affected_entities": ["Ocean Freight", "Asia-Europe Route"]
            }
        ]
        self.current_index = 0

    def fetch_latest_news(self) -> NewsSignal:
        """Simulates fetching the latest urgent news signal."""
        if self.current_index >= len(self.mock_news_stream):
             self.current_index = 0 # Loop for demo purposes
             
        news_item = self.mock_news_stream[self.current_index]
        self.current_index += 1
        
        return NewsSignal(
            id=str(uuid.uuid4()),
            headline=news_item["headline"],
            content=news_item["content"],
            source=news_item["source"],
            timestamp=datetime.utcnow().isoformat() + "Z",
            location=news_item.get("location"),
            affected_entities=news_item.get("affected_entities", [])
        )

    def fetch_all_news(self) -> list:
        """Returns all mock news signals at once (for bubble visualization)."""
        signals = []
        for item in self.mock_news_stream:
            signals.append(NewsSignal(
                id=str(uuid.uuid4()),
                headline=item["headline"],
                content=item["content"],
                source=item["source"],
                timestamp=datetime.utcnow().isoformat() + "Z",
                location=item.get("location"),
                affected_entities=item.get("affected_entities", [])
            ))
        return signals

