import math
from typing import Dict, List, Optional, Tuple

import polyline
import requests
from loguru import logger

from .base import MapsService


class OpenStreetMapService(MapsService):
    """
    OpenStreetMap implementation of the MapsService interface.
    Uses OpenRouteService for routing and Overpass API for POI search.
    """

    def __init__(self, ors_api_key: Optional[str] = None):
        """
        Initialize OpenStreetMap service.

        Args:
            ors_api_key: Optional OpenRouteService API key for better rate limits
        """
        self.ors_api_key = ors_api_key
        self.ors_base_url = "https://api.openrouteservice.org"
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.nominatim_url = "https://nominatim.openstreetmap.org"

        self.headers = {"User-Agent": "AI-Restaurant-Recommender/1.0"}
        if self.ors_api_key:
            self.headers["Authorization"] = self.ors_api_key

    def get_route_polyline(
        self, origin: str, destination: str
    ) -> Optional[str]:
        """
        Get the polyline string for a route between origin and destination.
        Uses OpenRouteService for routing.

        Args:
            origin: Starting point address or coordinates
            destination: End point address or coordinates

        Returns:
            Encoded polyline string or None if route calculation fails
        """
        try:
            origin_coords = self._geocode_address(origin)
            dest_coords = self._geocode_address(destination)

            if not origin_coords or not dest_coords:
                logger.error(
                    f"Failed to geocode origin: {origin} or destination: {destination}"
                )
                return None

            route_data = self._get_route_from_ors(origin_coords, dest_coords)

            if route_data and "routes" in route_data and route_data["routes"]:
                geometry = route_data["routes"][0]["geometry"]
                logger.info(
                    "Route calculated successfully via OpenRouteService"
                )
                return geometry
            else:
                logger.warning(
                    f"No route found between {origin} and {destination}"
                )
                return None

        except Exception as e:
            logger.error(f"Error calculating route via OpenStreetMap: {e}")
            return None

    def find_restaurants_on_route(
        self,
        route_polyline: str,
        keyword: str = "restaurant",
        radius: int = 1000,
    ) -> List[Dict]:
        """
        Find restaurants along a route using the polyline.
        Uses Overpass API to search for amenity=restaurant.

        Args:
            route_polyline: Encoded polyline string representing the route
            keyword: Search keyword (used for filtering, default: "restaurant")
            radius: Search radius in meters from route points

        Returns:
            List of restaurant dictionaries with standardized fields
        """
        try:
            route_points = polyline.decode(route_polyline)

            sampled_points = self._sample_route_points(
                route_points, max_points=10
            )

            all_restaurants = []
            seen_places = set()

            for point in sampled_points:
                try:
                    restaurants = self._search_restaurants_overpass(
                        lat=point[0], lon=point[1], radius=radius
                    )

                    for restaurant in restaurants:
                        restaurant_id = restaurant.get("id")

                        if restaurant_id in seen_places:
                            continue

                        seen_places.add(restaurant_id)

                        standardized = self._standardize_restaurant_data(
                            restaurant
                        )
                        if standardized:
                            all_restaurants.append(standardized)

                except Exception as e:
                    logger.warning(
                        f"Error searching restaurants at point {point}: {e}"
                    )
                    continue

            logger.info(
                f"Found {len(all_restaurants)} restaurants along route via OpenStreetMap"
            )
            return all_restaurants

        except Exception as e:
            logger.error(
                f"Error finding restaurants on route via OpenStreetMap: {e}"
            )
            return []

    def _geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert an address to coordinates using Nominatim.

        Args:
            address: Address string to geocode

        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        try:
            params = {"q": address, "format": "json", "limit": 1}

            response = requests.get(
                f"{self.nominatim_url}/search",
                params=params,
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return (lat, lon)

            return None

        except Exception as e:
            logger.error(f"Error geocoding address {address}: {e}")
            return None

    def _get_route_from_ors(
        self,
        origin_coords: Tuple[float, float],
        dest_coords: Tuple[float, float],
    ) -> Optional[Dict]:
        """
        Get route from OpenRouteService.
        """
        try:
            coordinates = [
                [origin_coords[1], origin_coords[0]],
                [dest_coords[1], dest_coords[0]],
            ]

            url = f"{self.ors_base_url}/v2/directions/driving-car"

            payload = {"coordinates": coordinates, "format": "geojson"}

            response = requests.post(
                url, json=payload, headers=self.headers, timeout=15
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as http_err:
            # Also print the body of the error response
            print(f"HTTP error occurred: {http_err}")
            print(f"Error response body: {http_err.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error getting route from OpenRouteService: {e}")
            return None

    def _search_restaurants_overpass(
        self, lat: float, lon: float, radius: int
    ) -> List[Dict]:
        """
        Search for restaurants using Overpass API.

        Args:
            lat: Latitude of search center
            lon: Longitude of search center
            radius: Search radius in meters

        Returns:
            List of restaurant data from Overpass API
        """
        try:
            overpass_query = f"""
            [out:json][timeout:25];
            (
              node["amenity"="restaurant"](around:{radius},{lat},{lon});
              way["amenity"="restaurant"](around:{radius},{lat},{lon});
              relation["amenity"="restaurant"](around:{radius},{lat},{lon});
            );
            out center meta;
            """

            response = requests.post(
                self.overpass_url,
                data=overpass_query,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            return data.get("elements", [])

        except Exception as e:
            logger.warning(f"Error querying Overpass API: {e}")
            return []

    def _standardize_restaurant_data(self, restaurant: Dict) -> Optional[Dict]:
        """
        Convert Overpass API restaurant data to standardized format.

        Args:
            restaurant: Raw restaurant data from Overpass API

        Returns:
            Standardized restaurant dictionary or None if data is insufficient
        """
        try:
            tags = restaurant.get("tags", {})

            # Skip if no name
            name = tags.get("name")
            if not name:
                return None

            # Get coordinates
            if "lat" in restaurant and "lon" in restaurant:
                lat, lon = restaurant["lat"], restaurant["lon"]
            elif "center" in restaurant:
                lat, lon = (
                    restaurant["center"]["lat"],
                    restaurant["center"]["lon"],
                )
            else:
                return None

            # Build address from available components
            address_parts = []
            if tags.get("addr:housenumber"):
                address_parts.append(tags["addr:housenumber"])
            if tags.get("addr:street"):
                address_parts.append(tags["addr:street"])
            if tags.get("addr:city"):
                address_parts.append(tags["addr:city"])
            if tags.get("addr:postcode"):
                address_parts.append(tags["addr:postcode"])

            address = (
                ", ".join(address_parts)
                if address_parts
                else f"{lat:.4f}, {lon:.4f}"
            )

            # Extract other useful information
            cuisine = tags.get("cuisine", "")
            phone = tags.get("phone", "")
            website = tags.get("website", "")
            opening_hours = tags.get("opening_hours", "")

            # OpenStreetMap doesn't have built-in ratings, so we'll use a default
            # In a real implementation, you might want to integrate with a ratings service
            rating = 3.5  # Default rating
            user_ratings_total = 0  # Not available in OSM

            return {
                "name": name,
                "address": address,
                "rating": rating,
                "user_ratings_total": user_ratings_total,
                "phone": phone,
                "website": website,
                "opening_hours": [opening_hours] if opening_hours else [],
                "cuisine": cuisine,
                "latitude": lat,
                "longitude": lon,
                "place_id": f"osm_{restaurant.get('type', 'node')}_{restaurant.get('id', '')}",
                "source": "OpenStreetMap",
            }

        except Exception as e:
            logger.warning(f"Error standardizing restaurant data: {e}")
            return None

    def _sample_route_points(
        self, route_points: List[Tuple[float, float]], max_points: int = 10
    ) -> List[Tuple[float, float]]:
        """
        Sample points along the route to limit API calls.

        Args:
            route_points: List of (latitude, longitude) tuples
            max_points: Maximum number of points to sample

        Returns:
            List of sampled route points
        """
        if len(route_points) <= max_points:
            return route_points

        step = len(route_points) // max_points
        sampled = []

        for i in range(0, len(route_points), step):
            sampled.append(route_points[i])
            if len(sampled) >= max_points:
                break

        if route_points and sampled[-1] != route_points[-1]:
            sampled.append(route_points[-1])

        return sampled

    @staticmethod
    def _calculate_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate the distance between two points using Haversine formula.

        Args:
            lat1, lon1: Coordinates of first point
            lat2, lon2: Coordinates of second point

        Returns:
            Distance in meters
        """
        R = 6371000
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad)
            * math.cos(lat2_rad)
            * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
