from abc import ABC, abstractmethod


class SearchService(ABC):
    """
    Abstract base class for a web search service.
    Defines the contract for fetching context about a restaurant.
    """

    @abstractmethod
    def search_restaurant(
        self, restaurant_name: str, restaurant_address: str
    ) -> str:
        pass
