from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Executes a search query and returns a list of results.
        Each result should be a dictionary with keys: 'title', 'url', 'snippet'.
        """
        pass
