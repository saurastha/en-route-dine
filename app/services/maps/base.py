from abc import ABC, abstractmethod


class MapsService(ABC):
    """
    Abstract base class for a mapping service.
    Defines the contract for getting route data and finding restaurants.
    """

    @abstractmethod
    def get_route_polyline(self, origin: str, destination: str) -> str | None:
        pass

    @abstractmethod
    def find_restaurants_on_route(
        self, route_polyline: str, keyword: str
    ) -> list:
        pass
