# services/search/google_search.py
import requests
from loguru import logger

# from ...config import settings
from .base import SearchService


class GoogleSearchService(SearchService):
    """
    Google Custom Search implementation of the SearchService interface.
    Provides web search functionality to gather additional context about restaurants.
    """

    def __init__(self, api_key, cse_id):
        self.api_key = api_key
        self.cse_id = cse_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    def search_restaurant(
        self, restaurant_name: str, restaurant_address: str
    ) -> str:
        """
        Search for additional context about a restaurant using Google Custom Search.

        Args:
            restaurant_name: Name of the restaurant
            restaurant_address: Address of the restaurant

        Returns:
            Concatenated search results as context string
        """
        try:
            # Create search query
            query = f'"{restaurant_name}" "{restaurant_address}"'
            # query = "soltee hotel"
            print(query)

            params = {
                "key": self.api_key,
                "cx": self.cse_id,
                "q": query,
                "num": 3,  # Limit to 3 results to avoid too much data
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            search_data = response.json()

            # Extract and combine search results
            context_parts = []
            for item in search_data.get("items", []):
                print(item)
                title = item.get("title", "")
                snippet = item.get("snippet", "")

                if title and snippet:
                    context_parts.append(f"{title}: {snippet}")

            context = " | ".join(context_parts)

            if context:
                logger.info(f"Found search context for {restaurant_name}")
                return context
            else:
                logger.warning(
                    f"No search results found for {restaurant_name}"
                )
                return f"No additional web context found for {restaurant_name}"

        except requests.RequestException as e:
            logger.error(
                f"Request error during search for {restaurant_name}: {e}"
            )
            return f"Search unavailable for {restaurant_name}"
        except Exception as e:
            logger.error(f"Error searching for {restaurant_name}: {e}")
            return f"Error retrieving context for {restaurant_name}"
