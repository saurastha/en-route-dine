# services/maps/google_maps.py
from typing import Dict, List, Optional

import googlemaps
import requests
from loguru import logger

# FIX: Use a correct relative import
from .base import MapsService


class GoogleMapsService(MapsService):
    """
    Google Maps implementation of the MapsService interface.
    Handles route calculation and restaurant finding using Google Maps API.
    """

    # FIX: The constructor now properly accepts the API key
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Google Maps API key is required.")
        self.api_key = api_key
        self.client = googlemaps.Client(key=self.api_key)

    def get_route_polyline(
        self, origin: str, destination: str
    ) -> Optional[str]:
        """
        Get the polyline string for a route between origin and destination.
        Uses the new Google Routes API.

        Args:
            origin: Starting point address
            destination: End point address

        Returns:
            Encoded polyline string or None if route calculation fails
        """
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.polyline.encodedPolyline",
        }

        payload = {
            "origin": {"address": origin},
            "destination": {"address": destination},
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()

            if "routes" in data and data["routes"]:
                polyline = data["routes"][0]["polyline"]["encodedPolyline"]
                logger.info(
                    f"Route calculated successfully via Routes API: {len(polyline)} characters"
                )
                return polyline
            else:
                logger.warning(
                    f"No route found between {origin} and {destination}. Response: {data}"
                )
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calculating route via Routes API: {e}")
            if e.response:
                logger.error(f"Error details: {e.response.text}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(
                f"Could not parse polyline from Routes API response: {e}"
            )
            return None

    def find_restaurants_on_route(
        self,
        route_polyline: str,
        keyword: str = "restaurant",
        radius: int = 1000,
    ) -> List[Dict]:
        """
        Find restaurants along a route using the polyline.
        """
        try:
            route_points = googlemaps.convert.decode_polyline(route_polyline)
            sampled_points = route_points[:: max(1, len(route_points) // 10)]
            all_restaurants = []
            seen_places = set()

            for point in sampled_points:
                try:
                    places_result = self.client.places_nearby(
                        location=(point["lat"], point["lng"]),
                        radius=radius,
                        type="restaurant",
                        keyword=keyword,
                    )

                    for place in places_result.get("results", []):
                        place_id = place.get("place_id")
                        if place_id in seen_places:
                            continue
                        seen_places.add(place_id)
                        details = self._get_place_details(place_id)
                        if details:
                            all_restaurants.append(details)

                except Exception as e:
                    logger.warning(
                        f"Error searching restaurants at point {point}: {e}"
                    )
                    continue

            logger.info(
                f"Found {len(all_restaurants)} restaurants along route"
            )
            return all_restaurants

        except Exception as e:
            logger.error(f"Error finding restaurants on route: {e}")
            return []

    def _get_place_details(self, place_id: str) -> Optional[Dict]:
        """
        Get detailed information about a place using its place_id.
        """
        try:
            place_details = self.client.place(
                place_id=place_id,
                fields=[
                    "name",
                    "formatted_address",
                    "rating",
                    "user_ratings_total",
                    "formatted_phone_number",
                    "website",
                    "opening_hours",
                    "price_level",
                ],
            )
            result = place_details.get("result", {})
            return {
                "name": result.get("name", "Unknown"),
                "address": result.get("formatted_address", ""),
                "rating": result.get("rating", 0.0),
                "user_ratings_total": result.get("user_ratings_total", 0),
                "phone": result.get("formatted_phone_number", ""),
                "website": result.get("website", ""),
                "opening_hours": result.get("opening_hours", {}).get(
                    "weekday_text", []
                ),
                "price_level": result.get("price_level", 0),
                "place_id": place_id,
            }
        except Exception as e:
            logger.warning(f"Error getting place details for {place_id}: {e}")
            return None
