from abc import ABC, abstractmethod


class SearchService(ABC):
    @abstractmethod
    def search_restaurant(
        self, restaurant_name: str, restaurant_address: str
    ) -> str:
        pass
