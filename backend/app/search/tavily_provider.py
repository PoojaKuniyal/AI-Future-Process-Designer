import httpx
import logging
from typing import List, Dict, Any
from backend.app.search.base import BaseSearchProvider

logger = logging.getLogger(__name__)

class TavilySearchProvider(BaseSearchProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.tavily.com/search"

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            logger.warning("Tavily API key is missing. Cannot run search.")
            return []

        logger.info(f"Running Tavily Search for: '{query}'")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    self.endpoint,
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": limit,
                        "search_depth": "basic"
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title", "No Title"),
                            "url": item.get("url", ""),
                            "snippet": item.get("content", item.get("snippet", ""))
                        })
                    logger.info(f"Tavily returned {len(results)} results.")
                    return results
                else:
                    logger.error(f"Tavily API error: Status {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []
