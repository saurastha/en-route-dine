from abc import ABC, abstractmethod
from typing import Dict, Optional


class MapsService(ABC):
    @abstractmethod
    def get_route_details(
        self, origin: str, destination: str, use_current_location: bool = False
    ) -> Optional[Dict]:
        pass

    @abstractmethod
    def find_restaurants_on_route(
        self,
        route_polyline: str,
        amenity_to_search: str,
        radius: int = 1000,
    ) -> list:
        pass

    @abstractmethod
    def calculate_distance_from_route(
        self, restaurant_location: Dict, route_polyline: str
    ) -> float:
        pass

    @abstractmethod
    def get_route_with_waypoint(
        self, origin: str, waypoint: str, destination: str
    ) -> Optional[Dict]:
        pass

    @abstractmethod
    def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        pass
