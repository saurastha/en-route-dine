import math
from typing import Dict, List, Optional

import googlemaps
import requests
from googlemaps.convert import decode_polyline
from loguru import logger

from .base import MapsService


class GoogleMapsService(MapsService):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Google Maps API key is required.")
        self.api_key = api_key
        self.client = googlemaps.Client(key=self.api_key)

    def get_route_details(
        self, origin: str, destination: str
    ) -> Optional[Dict]:
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.polyline.encodedPolyline,routes.legs.steps.navigationInstruction",
        }
        payload = {
            "origin": {"address": origin},
            "destination": {"address": destination},
            "travelMode": "DRIVE",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            if "routes" in data and data["routes"]:
                route = data["routes"][0]
                polyline = route["polyline"]["encodedPolyline"]
                steps = [
                    step["navigationInstruction"]["instructions"]
                    for leg in route.get("legs", [])
                    for step in leg.get("steps", [])
                    if "navigationInstruction" in step
                    and "instructions" in step["navigationInstruction"]
                ]
                return {"polyline": polyline, "steps": steps}
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calculating route: {e}")
            return None

    def get_route_with_waypoint(
        self, origin: str, waypoint: str, destination: str
    ) -> Optional[Dict]:
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.polyline.encodedPolyline,routes.legs.steps.navigationInstruction",
        }
        payload = {
            "origin": {"address": origin},
            "destination": {"address": destination},
            "intermediates": [{"address": waypoint}],
            "travelMode": "DRIVE",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            if "routes" in data and data["routes"]:
                route = data["routes"][0]
                steps = [
                    step["navigationInstruction"]["instructions"]
                    for leg in route.get("legs", [])
                    for step in leg.get("steps", [])
                    if "navigationInstruction" in step
                    and "instructions" in step["navigationInstruction"]
                ]
                return {"steps": steps}
            return None
        except Exception as e:
            logger.error(f"Error calculating route with waypoint: {e}")
            return None

    def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        try:
            result = self.client.reverse_geocode((lat, lng))
            if result and len(result) > 0:
                return result[0].get("formatted_address")
            return None
        except Exception as e:
            logger.warning(f"Reverse geocoding failed: {e}")
            return None

    def find_restaurants_on_route(
        self, route_polyline: str, keyword: str = "restaurant"
    ) -> List[Dict]:
        try:
            route_points = decode_polyline(route_polyline)
            sampled_points = route_points[:: max(1, len(route_points) // 10)]
            all_restaurants = []
            seen_places = set()

            for point in sampled_points:
                try:
                    places_result = self.client.places_nearby(
                        location=(point["lat"], point["lng"]),
                        radius=1000,
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
                    logger.warning(f"Error searching near point {point}: {e}")
                    continue

            return all_restaurants
        except Exception as e:
            logger.error(f"Error finding restaurants: {e}")
            return []

    def _get_place_details(self, place_id: str) -> Optional[Dict]:
        try:
            place_details = self.client.place(
                place_id=place_id,
                fields=[
                    "name",
                    "formatted_address",
                    "rating",
                    "user_ratings_total",
                    "geometry",
                ],
            )
            result = place_details.get("result", {})
            location = result.get("geometry", {}).get("location", {})
            lat = location.get("lat")
            lng = location.get("lng")

            if not lat or not lng:
                return None

            return {
                "name": result.get("name", "Unknown"),
                "address": result.get("formatted_address", ""),
                "rating": result.get("rating", 0.0),
                "user_ratings_total": result.get("user_ratings_total", 0),
                "latitude": lat,
                "longitude": lng,
                "place_id": place_id,
            }
        except Exception as e:
            logger.warning(f"Error getting place details: {e}")
            return None

    def calculate_distance_from_route(
        self, restaurant_location: Dict, route_polyline: str
    ) -> float:
        route_points = decode_polyline(route_polyline)
        min_dist_meters = float("inf")

        for i in range(len(route_points) - 1):
            p1 = route_points[i]
            p2 = route_points[i + 1]
            dist = self._point_to_line_segment_distance(
                p=restaurant_location, v=p1, w=p2
            )
            if dist < min_dist_meters:
                min_dist_meters = dist

        return min_dist_meters / 1000

    def _point_to_line_segment_distance(
        self, p: Dict, v: Dict, w: Dict
    ) -> float:
        p_lat, p_lon = p["lat"], p["lng"]
        v_lat, v_lon = v["lat"], v["lng"]
        w_lat, w_lon = w["lat"], w["lng"]

        segment_dist_sq = self._haversine_distance_sq(
            (v_lat, v_lon), (w_lat, w_lon)
        )
        if segment_dist_sq == 0.0:
            return self._haversine_distance((p_lat, p_lon), (v_lat, v_lon))

        dot = (p_lat - v_lat) * (w_lat - v_lat) + (p_lon - v_lon) * (
            w_lon - v_lon
        )
        t = max(0, min(1, dot / segment_dist_sq))

        proj_lat = v_lat + t * (w_lat - v_lat)
        proj_lon = v_lon + t * (w_lon - v_lon)

        return self._haversine_distance((p_lat, p_lon), (proj_lat, proj_lon))

    def _haversine_distance(self, p1: tuple, p2: tuple) -> float:
        R = 6371000
        lat1, lon1 = p1
        lat2, lon2 = p2

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2) + math.cos(
            math.radians(lat1)
        ) * math.cos(math.radians(lat2)) * (math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _haversine_distance_sq(self, p1: tuple, p2: tuple) -> float:
        lat1, lon1 = p1
        lat2, lon2 = p2
        return (lat2 - lat1) ** 2 + (lon2 - lon1) ** 2
