import logging
from backend.app.search.base import BaseSearchProvider
from backend.app.search.tavily_provider import TavilySearchProvider
from backend.app.search.brave_provider import BraveSearchProvider
from backend.app.search.mock_provider import MockSearchProvider
from backend.app.config import settings

logger = logging.getLogger(__name__)

def get_search_provider(provider_name: str = None) -> BaseSearchProvider:
    """
    Returns the configured search provider. Falls back to MockSearchProvider if keys are missing.
    """
    if not provider_name:
        provider_name = settings.SEARCH_PROVIDER

    p_type = provider_name.strip().lower()
    
    if p_type == "tavily":
        if settings.TAVILY_API_KEY:
            logger.info("Instantiating TavilySearchProvider.")
            return TavilySearchProvider(api_key=settings.TAVILY_API_KEY)
        else:
            logger.warning("Tavily API key is missing. Falling back to MockSearchProvider.")
            return MockSearchProvider()
            
    elif p_type == "brave":
        if settings.BRAVE_API_KEY:
            logger.info("Instantiating BraveSearchProvider.")
            return BraveSearchProvider(api_key=settings.BRAVE_API_KEY)
        else:
            logger.warning("Brave Subscription Token is missing. Falling back to MockSearchProvider.")
            return MockSearchProvider()
            
    else:
        logger.info("Instantiating MockSearchProvider (explicitly selected or unrecognized name).")
        return MockSearchProvider()
