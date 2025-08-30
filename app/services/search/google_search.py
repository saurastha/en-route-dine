import requests
from loguru import logger

from .base import SearchService


class GoogleSearchService(SearchService):
    def __init__(self, api_key, cse_id):
        self.api_key = api_key
        self.cse_id = cse_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    def search_restaurant(
        self, restaurant_name: str, restaurant_address: str
    ) -> str:
        try:
            query = f'"{restaurant_name}" "{restaurant_address}"'
            params = {
                "key": self.api_key,
                "cx": self.cse_id,
                "q": query,
                "num": 3,
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            search_data = response.json()

            context_parts = []
            for item in search_data.get("items", []):
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                if title and snippet:
                    context_parts.append(f"{title}: {snippet}")

            context = " | ".join(context_parts)
            return (
                context
                if context
                else f"No web context found for {restaurant_name}"
            )

        except Exception as e:
            logger.error(f"Error searching for {restaurant_name}: {e}")
            return f"Search unavailable for {restaurant_name}"
