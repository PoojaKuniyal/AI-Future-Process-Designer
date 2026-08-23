import httpx
import logging
import urllib.parse
from typing import List, Dict, Any
from backend.app.search.base import BaseSearchProvider

logger = logging.getLogger(__name__)

class BraveSearchProvider(BaseSearchProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.search.brave.com/res/v1/web/search"

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            logger.warning("Brave Subscription Token is missing. Cannot run search.")
            return []

        logger.info(f"Running Brave Search for: '{query}'")
        try:
            # Brave Search API uses GET with query params
            encoded_query = urllib.parse.quote(query)
            url = f"{self.endpoint}?q={encoded_query}&count={limit}"
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    # Brave response structure holds results under web.results
                    web_results = data.get("web", {}).get("results", [])
                    for item in web_results:
                        results.append({
                            "title": item.get("title", "No Title"),
                            "url": item.get("url", ""),
                            "snippet": item.get("description", "")
                        })
                    logger.info(f"Brave returned {len(results)} results.")
                    return results
                else:
                    logger.error(f"Brave API error: Status {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Brave search failed: {e}")
            return []
