from loguru import logger
from tavily import TavilyClient

from .base import SearchService


class TavilySearchService(SearchService):
    def __init__(self, api_key: str):
        self.client = TavilyClient(api_key=api_key)

    def search_restaurant(
        self, restaurant_name: str, restaurant_address: str
    ) -> str:
        try:
            query = f"{restaurant_name} restaurant {restaurant_address} details/reviews"

            logger.info(f"Search Query: {query}")

            response = self.client.search(
                query=query, include_answer="advanced", search_depth="advanced"
            )

            return (
                response["answer"]
                if response
                else f"No web context found for {restaurant_name}"
            )

        except Exception as e:
            logger.error(f"Tavily search error for {restaurant_name}: {e}")
            return f"Search unavailable for {restaurant_name}"
