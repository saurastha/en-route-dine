import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus

from fastapi import FastAPI, HTTPException, Request
from loguru import logger

from .factory import ServiceFactory
from .schema import RecommendationRequest, RecommendationResponse, Restaurant
from .services.maps.amenity import FoodAmenity
from .services.maps.google_maps import GoogleMapsService
from .services.maps.open_street_map import OpenStreetMapService
from .services.maps.utils import get_user_location

app = FastAPI(
    title="AI Restaurant Recommender",
    description="Finds and ranks restaurants along a route using AI",
)

maps_service = ServiceFactory.create_maps_service()
search_service = ServiceFactory.create_search_service()
llm_service = ServiceFactory.create_llm_service()


def create_google_maps_link(
    origin: str, destination: str, waypoint_address: str
) -> str:
    base_url = "https://www.google.com/maps/dir/?api=1"
    encoded_origin = quote_plus(origin)
    encoded_destination = quote_plus(destination)
    encoded_waypoint = quote_plus(waypoint_address)
    return f"{base_url}&origin={encoded_origin}&destination={encoded_destination}&waypoints={encoded_waypoint}"


def create_osm_link(start_coords, end_coords, waypoint_coords) -> str:
    base_url = "https://www.openstreetmap.org/directions"
    route_param = (
        f"{start_coords[0]},{start_coords[1]};"
        f"{waypoint_coords[0]},{waypoint_coords[1]};"
        f"{end_coords[0]},{end_coords[1]}"
    )
    return f"{base_url}?engine=osrm_car&route={route_param}"


async def determine_amenity_with_llm(query: str) -> str:
    amenity_list = FoodAmenity.get_all_values()

    system_prompt = """
    You are an intelligent API assistant.
    Your task is to classify a user's food-related query into only one predefined amenity categories from a provided list.
    Respond only with a JSON object containing the most relevant amenity.
    If no specific category matches, default to "restaurant". Do not provide any explanation or conversational text.
    """

    user_prompt = f"""
    **User Query:** "{query}"

    **Available Amenity Categories:**
    {amenity_list}

    Based on the query, identify the most relevant amenity categories from the list.

    **JSON Response format:**
    {{"amenities": "<most_suitable_amenity>"}}
    """
    default_amenity = "restaurant"

    try:
        logger.info(f"Classifying amenity for query: '{query}'")
        result = llm_service.ask_llm(
            system_prompt=system_prompt, user_prompt=user_prompt
        )
        amenity = result.get("amenities", default_amenity)

        validated_amenity = amenity in amenity_list
        if not validated_amenity:
            return default_amenity

        logger.info(f"LLM determined amenities: {amenity}")
        return amenity
    except Exception as e:
        logger.error(
            f"LLM amenity classification failed: {e}. Defaulting to 'restaurant'."
        )
        return default_amenity


def process_restaurant_candidate(
    restaurant_data: dict,
    query: str,
    route_polyline: str,
    origin: str,
    destination: str,
    route_details: dict,
) -> Restaurant:
    """
    Processes a single restaurant candidate: performs search, LLM scoring,
    distance calculation, and map link creation.
    """
    search_context = ""
    if search_service:
        try:
            search_context = search_service.search_restaurant(
                restaurant_name=restaurant_data["name"],
                restaurant_address=restaurant_data["address"],
            )
        except Exception as e:
            logger.warning(f"Search failed for {restaurant_data['name']}: {e}")
            search_context = "No web context available"

    system_prompt = "You are a restaurant recommendation assistant. Evaluate how well a restaurant matches a user's request."

    user_prompt = f"""
    **User's Request:** "{query}"

    **Restaurant Information:**
    - Name: {restaurant_data.get("name")}
    - Rating: {restaurant_data.get("rating")} out of 5 stars from {restaurant_data.get("user_ratings_total")} users.
    - Additional Context: "{search_context}"

    **Task:**
    1. Analyze how well the restaurant fits the request (1-10 scale). Even when the cuisine or menu do not specifically mention the user's choice, try to co-related things and determine the scale.
    2. Provide a brief justification. Keep the justification short.
    3. Respond with JSON: {{"score": <score>, "justification": "<justification>"}}
    """

    try:
        llm_result = llm_service.ask_llm(
            system_prompt=system_prompt, user_prompt=user_prompt
        )
    except Exception as e:
        logger.error(f"LLM scoring failed for {restaurant_data['name']}: {e}")
        llm_result = {"score": 0, "justification": "Analysis error"}

    distance_km = maps_service.calculate_distance_from_route(
        restaurant_location={
            "lat": restaurant_data["latitude"],
            "lng": restaurant_data["longitude"],
        },
        route_polyline=route_polyline,
    )

    map_link = ""
    if isinstance(maps_service, GoogleMapsService):
        map_link = create_google_maps_link(
            origin,
            destination,
            restaurant_data["address"],
        )
    elif isinstance(maps_service, OpenStreetMapService):
        if route_details.get("start_coords") and route_details.get(
            "end_coords"
        ):
            map_link = create_osm_link(
                start_coords=route_details["start_coords"],
                end_coords=route_details["end_coords"],
                waypoint_coords=(
                    restaurant_data["latitude"],
                    restaurant_data["longitude"],
                ),
            )

    return Restaurant(
        name=restaurant_data["name"],
        address=restaurant_data["address"],
        rating=restaurant_data["rating"],
        user_ratings_total=restaurant_data["user_ratings_total"],
        match_score=llm_result.get("score", 0),
        justification=llm_result.get("justification", ""),
        distance_from_route_km=round(distance_km, 2),
        map_link=map_link,
    )


@app.post(
    "/api/recommendations-on-route", response_model=RecommendationResponse
)
async def get_recommendations(
    request_data: RecommendationRequest, request: Request
):
    try:
        origin = request_data.origin

        route_details = maps_service.get_route_details(
            origin, request_data.destination, request_data.use_current_location
        )
        if not route_details or not route_details.get("polyline"):
            raise HTTPException(
                status_code=500, detail="Could not calculate route"
            )

        route_polyline = route_details["polyline"]

        amenity_to_search = await determine_amenity_with_llm(
            request_data.query
        )

        initial_candidates = maps_service.find_restaurants_on_route(
            route_polyline, amenity_to_search, request_data.radius
        )

        logger.debug(initial_candidates)

        if not initial_candidates:
            return RecommendationResponse(
                origin=origin,
                destination=request_data.destination,
                route_summary=[],
                restaurants=[],
            )

        filtered_candidates = [
            r
            for r in initial_candidates
            if r.get("rating", 0) >= request_data.min_rating
        ]

        if not filtered_candidates:
            return RecommendationResponse(
                origin=origin,
                destination=request_data.destination,
                route_summary=route_details.get("steps", []),
                restaurants=[],
            )

        ranked_restaurants = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    process_restaurant_candidate,
                    restaurant_data,
                    request_data.query,
                    route_polyline,
                    origin,
                    request_data.destination,
                    route_details,
                )
                for restaurant_data in random.sample(filtered_candidates, 5)
            }

            for future in as_completed(futures):
                try:
                    ranked_restaurants.append(future.result())
                except Exception as exc:
                    logger.error(
                        f"A restaurant processing task generated an exception: {exc}"
                    )

        ranked_restaurants.sort(key=lambda x: x.match_score, reverse=True)

        logger.debug(f"After ranking: {ranked_restaurants}")

        route_summary = route_details.get("steps", [])
        if ranked_restaurants:
            best_restaurant = ranked_restaurants[0]
            waypoint_route = maps_service.get_route_with_waypoint(
                origin, best_restaurant.address, request_data.destination
            )
            if waypoint_route and waypoint_route.get("steps"):
                route_summary = waypoint_route["steps"]

        return RecommendationResponse(
            origin=origin,
            destination=request_data.destination,
            route_summary=route_summary,
            restaurants=ranked_restaurants,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "maps": type(maps_service).__name__,
            "search": type(search_service).__name__
            if search_service
            else None,
            "llm": type(llm_service).__name__,
        },
    }


@app.post("/api/detect-location")
async def detect_current_location(request: Request):
    """Endpoint to detect user's current location using IP geolocation."""
    current_location = get_user_location()
    return {"coordinates": current_location}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return {"error": "Endpoint not found", "path": str(request.url)}


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal server error on {request.url}: {exc}")
    return {
        "error": "Internal server error",
        "message": "Please try again later",
    }


@app.on_event("startup")
async def startup_event():
    logger.info("Starting En-Route-Dine API")
    logger.info(f"Maps Service: {type(maps_service).__name__}")
    logger.info(
        f"Search Service: {type(search_service).__name__ if search_service else 'None'}"
    )
    logger.info(f"LLM Service: {type(llm_service).__name__}")
    logger.info("Service initialization complete")
