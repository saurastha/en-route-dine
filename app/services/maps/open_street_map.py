import math
from typing import Dict, List, Optional, Tuple

import polyline
import requests
from loguru import logger

from .base import MapsService
from .utils import get_user_location


class OpenStreetMapService(MapsService):
    def __init__(self, ors_api_key: Optional[str] = None):
        self.ors_api_key = ors_api_key
        self.ors_base_url = "https://api.openrouteservice.org"
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.nominatim_url = "https://nominatim.openstreetmap.org"
        self.headers = {"User-Agent": "AI-Restaurant-Recommender/1.0"}
        if self.ors_api_key:
            self.headers["Authorization"] = self.ors_api_key

    def get_route_details(
        self, origin: str, destination: str, use_current_location: bool = False
    ) -> Optional[Dict]:
        try:
            if use_current_location:
                origin_coords = get_user_location()
            else:
                origin_coords = self._geocode_address(origin)

            dest_coords = self._geocode_address(destination)

            logger.info(
                f"Origin co-ordinates: {origin_coords} | Destination co-ordinates: {dest_coords}"
            )

            if not origin_coords or not dest_coords:
                logger.error("Failed to geocode origin or destination")
                return {}

            route_data = self._get_route_from_ors(origin_coords, dest_coords)

            if (
                route_data
                and "features" in route_data
                and route_data["features"]
            ):
                feature = route_data["features"][0]
                geometry = feature["geometry"]["coordinates"]
                encoded_polyline = polyline.encode(
                    [(lat, lon) for lon, lat in geometry]
                )

                steps = [
                    step["instruction"]
                    for segment in feature["properties"].get("segments", [])
                    for step in segment.get("steps", [])
                ]

                return {
                    "polyline": encoded_polyline,
                    "steps": steps,
                    "start_coords": origin_coords,
                    "end_coords": dest_coords,
                }
            return {}
        except Exception as e:
            logger.error(f"Error calculating route: {e}")
            return {}

    def get_route_with_waypoint(
        self, origin: str, waypoint: str, destination: str
    ) -> Optional[Dict]:
        try:
            origin_coords = self._geocode_address(origin)
            waypoint_coords = self._geocode_address(waypoint)
            dest_coords = self._geocode_address(destination)

            if not all([origin_coords, waypoint_coords, dest_coords]):
                return None

            coordinates = [
                [origin_coords[1], origin_coords[0]],
                [waypoint_coords[1], waypoint_coords[0]],
                [dest_coords[1], dest_coords[0]],
            ]

            url = f"{self.ors_base_url}/v2/directions/driving-car/geojson"
            payload = {"coordinates": coordinates, "instructions": "true"}
            response = requests.post(
                url, json=payload, headers=self.headers, timeout=15
            )
            response.raise_for_status()

            route_data = response.json()
            if (
                route_data
                and "features" in route_data
                and route_data["features"]
            ):
                feature = route_data["features"][0]
                steps = [
                    step["instruction"]
                    for segment in feature["properties"].get("segments", [])
                    for step in segment.get("steps", [])
                ]
                return {"steps": steps}
            return None
        except Exception as e:
            logger.error(f"Error calculating route with waypoint: {e}")
            return None

    def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        try:
            params = {
                "lat": lat,
                "lon": lng,
                "format": "json",
                "addressdetails": 1,
            }
            response = requests.get(
                f"{self.nominatim_url}/reverse",
                params=params,
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("display_name")
        except Exception as e:
            logger.warning(f"Reverse geocoding failed: {e}")
            return None

    def find_restaurants_on_route(
        self,
        route_polyline: str,
        amenity_to_search: str,
        radius: int = 1000,
    ) -> List[Dict]:
        try:
            logger.info(
                f"Finding restaurants along the route for: {amenity_to_search}"
            )
            restaurants = self._search_restaurants_along_polyline_overpass(
                route_polyline, amenity_to_search, radius
            )

            all_restaurants = []
            seen_places = set()

            for restaurant in restaurants:
                restaurant_id = restaurant.get("id")
                if restaurant_id in seen_places:
                    continue
                seen_places.add(restaurant_id)
                standardized = self._standardize_restaurant_data(restaurant)
                if standardized:
                    all_restaurants.append(standardized)

            logger.info(f"Found: {len(all_restaurants)} restaurants")
            return all_restaurants
        except Exception as e:
            logger.error(f"Error finding restaurants along route: {e}")
            return []

    def calculate_distance_from_route(
        self, restaurant_location: Dict, route_polyline: str
    ) -> float:
        route_points = polyline.decode(route_polyline)
        min_dist_meters = float("inf")
        route_points_dicts = [
            {"lat": lat, "lng": lon} for lat, lon in route_points
        ]

        for i in range(len(route_points_dicts) - 1):
            p1 = route_points_dicts[i]
            p2 = route_points_dicts[i + 1]
            dist = self._point_to_line_segment_distance(
                p=restaurant_location, v=p1, w=p2
            )
            if dist < min_dist_meters:
                min_dist_meters = dist

        return min_dist_meters / 1000

    def _geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
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
                return (float(data[0]["lat"]), float(data[0]["lon"]))
            return None
        except Exception as e:
            logger.error(f"Error geocoding address {address}: {e}")
            return None

    def _get_route_from_ors(
        self,
        origin_coords: Tuple[float, float],
        dest_coords: Tuple[float, float],
    ) -> Optional[Dict]:
        try:
            coordinates = [
                [origin_coords[1], origin_coords[0]],
                [dest_coords[1], dest_coords[0]],
            ]
            url = f"{self.ors_base_url}/v2/directions/driving-car/geojson"
            payload = {"coordinates": coordinates, "instructions": "true"}
            response = requests.post(
                url, json=payload, headers=self.headers, timeout=15
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting route from ORS: {e}")
            return None

    def _search_restaurants_along_polyline_overpass(
        self, route_polyline: str, amenity_to_search: str, radius: int
    ) -> List[Dict]:
        try:
            MAX_POLYLINE_POINTS = 150
            decoded_points = polyline.decode(route_polyline)

            if len(decoded_points) > MAX_POLYLINE_POINTS:
                step = len(decoded_points) // MAX_POLYLINE_POINTS
                simplified_points = decoded_points[::step]
            else:
                simplified_points = decoded_points

            flattened_coords = [
                coord for point in simplified_points for coord in point
            ]
            polyline_coords_str = ",".join(map(str, flattened_coords))

            overpass_query = f"""
            [out:json][timeout:30];
            (
              nwr["amenity"="{amenity_to_search}"](around:{radius},{polyline_coords_str});
            );
            out center meta;
            """
            logger.debug(overpass_query)
            response = requests.post(
                self.overpass_url,
                data={"data": overpass_query},
                headers=self.headers,
                timeout=40,
            )
            response.raise_for_status()
            return response.json().get("elements", [])
        except requests.exceptions.HTTPError as http_err:
            logger.error(
                f"HTTP error querying Overpass API: {http_err} - Response: {http_err.response.text}"
            )
            return []
        except Exception as e:
            logger.warning(f"Error querying Overpass API along polyline: {e}")
            return []

    def _standardize_restaurant_data(self, restaurant: Dict) -> Optional[Dict]:
        try:
            tags = restaurant.get("tags", {})
            if not tags.get("name"):
                return None

            if "lat" in restaurant and "lon" in restaurant:
                lat, lon = restaurant["lat"], restaurant["lon"]
            elif "center" in restaurant:
                lat, lon = (
                    restaurant["center"]["lat"],
                    restaurant["center"]["lon"],
                )
            else:
                return None

            address_parts = [
                tags.get("addr:housenumber"),
                tags.get("addr:street"),
                tags.get("addr:city"),
                tags.get("addr:postcode"),
            ]
            address = ", ".join(part for part in address_parts if part)

            if not address:
                reverse_geocoded = self.reverse_geocode(lat, lon)
                address = reverse_geocoded or f"{lat:.4f}, {lon:.4f}"

            return {
                "name": tags["name"],
                "address": address,
                "rating": 3.5,
                "user_ratings_total": 0,
                "latitude": lat,
                "longitude": lon,
                "place_id": f"osm_{restaurant.get('type', 'node')}_{restaurant.get('id', '')}",
            }
        except Exception as e:
            logger.warning(f"Error standardizing restaurant data: {e}")
            return None

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
        lat1, lon1, lat2, lon2 = map(
            math.radians, [p1[0], p1[1], p2[0], p2[1]]
        )
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        return R * (2 * math.asin(math.sqrt(a)))

    def _haversine_distance_sq(self, p1: tuple, p2: tuple) -> float:
        return (p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2
