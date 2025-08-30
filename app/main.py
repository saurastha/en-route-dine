# app/main.py
from urllib.parse import quote_plus

from fastapi import FastAPI, HTTPException
from loguru import logger

from .factory import ServiceFactory
from .schema import RecommendationRequest, RecommendationResponse, Restaurant

app = FastAPI(
    title="AI Restaurant Recommender",
    description="Finds and ranks restaurants along a route using an LLM. Supports both Google Maps and OpenStreetMap.",
)

# Initialize services using factory pattern
maps_service = ServiceFactory.create_maps_service()
search_service = ServiceFactory.create_search_service()
llm_service = ServiceFactory.create_llm_service()

logger.info(f"Initialized with maps service: {type(maps_service).__name__}")
logger.info(
    f"Initialized with search service: {type(search_service).__name__ if search_service else 'None'}"
)
logger.info(f"Initialized with LLM service: {type(llm_service).__name__}")


def create_google_maps_link(
    origin: str, destination: str, waypoint_address: str
) -> str:
    base_url = "https://www.google.com/maps/dir/?api=1"
    return f"{base_url}&origin={quote_plus(origin)}&destination={quote_plus(destination)}&waypoints={quote_plus(waypoint_address)}"


def create_osm_link(start_coords, end_coords, waypoint_coords) -> str:
    base_url = "https://www.openstreetmap.org/directions"
    # Format: route=start_lat,start_lon;waypoint_lat,waypoint_lon;end_lat,end_lon
    route_param = (
        f"{start_coords[0]},{start_coords[1]};"
        f"{waypoint_coords[0]},{waypoint_coords[1]};"
        f"{end_coords[0]},{end_coords[1]}"
    )
    return f"{base_url}?route={route_param}"


@app.post(
    "/api/recommendations-on-route", response_model=RecommendationResponse
)
async def get_recommendations(request: RecommendationRequest):
    """
    The main API endpoint to get restaurant recommendations.
    It orchestrates the entire process from route calculation to LLM-based ranking.
    Supports both Google Maps and OpenStreetMap backends.
    """
    try:
        # Get route polyline
        route_polyline = maps_service.get_route_polyline(
            request.origin, request.destination
        )
        if not route_polyline:
            raise HTTPException(
                status_code=500, detail="Could not calculate the route."
            )

        # Find restaurants along the route
        initial_candidates = maps_service.find_restaurants_on_route(
            route_polyline, keyword="restaurant"
        )

        if not initial_candidates:
            return RecommendationResponse(restaurants=[])

        # Filter by minimum rating
        filtered_candidates = [
            r
            for r in initial_candidates
            if r.get("rating", 0) >= request.min_rating
        ]

        if not filtered_candidates:
            logger.info(
                f"No restaurants found meeting minimum rating of {request.min_rating}"
            )
            return RecommendationResponse(restaurants=[])

        # Sort by rating and take top 5 candidates
        top_candidates = sorted(
            filtered_candidates, key=lambda x: x.get("rating", 0), reverse=True
        )[:5]

        ranked_restaurants = []

        # Process each restaurant with LLM scoring
        for restaurant_data in top_candidates:
            # Get additional context from web search (if available)
            search_context = ""
            if search_service:
                try:
                    # FIX: Changed method call from get_restaurant_context to search_restaurant
                    search_context = search_service.search_restaurant(
                        restaurant_name=restaurant_data["name"],
                        restaurant_address=restaurant_data["address"],
                    )
                except Exception as e:
                    logger.warning(
                        f"Search failed for {restaurant_data['name']}: {e}"
                    )
                    search_context = f"No web context available for {restaurant_data['name']}"
            else:
                search_context = (
                    f"Web search not available for {restaurant_data['name']}"
                )

            # Get LLM match score
            try:
                llm_result = llm_service.ask_llm(
                    user_query=request.query,
                    restaurant_data=restaurant_data,
                    search_context=search_context,
                )
            except Exception as e:
                logger.error(
                    f"LLM scoring failed for {restaurant_data['name']}: {e}"
                )
                llm_result = {
                    "score": 5,  # Default neutral score
                    "justification": "Unable to analyze due to technical error",
                }

            # Create Restaurant object
            ranked_restaurants.append(
                Restaurant(
                    name=restaurant_data["name"],
                    address=restaurant_data["address"],
                    rating=restaurant_data["rating"],
                    user_ratings_total=restaurant_data["user_ratings_total"],
                    match_score=llm_result.get("score", 0),
                    justification=llm_result.get("justification", ""),
                )
            )

        # Sort by LLM match score
        ranked_restaurants.sort(key=lambda x: x.match_score, reverse=True)

        logger.info(
            f"Successfully processed {len(ranked_restaurants)} restaurants"
        )
        return RecommendationResponse(restaurants=ranked_restaurants)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the request: {str(e)}",
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
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


@app.get("/config")
async def get_config():
    """Get current service configuration (without sensitive data)."""
    from .config import settings

    return {
        "map_service": settings.map_service,
        "llm_provider": settings.llm_provider,
        "services_available": {
            "google_maps": bool(settings.google_maps_api_key),
            "openstreetmap": True,  # Always available
            "google_search": bool(
                settings.google_search_api_key and settings.google_cse_id
            ),
            "openrouteservice": bool(settings.openrouteservice_api_key),
        },
    }


# To run the app, navigate to the root directory in your terminal and use:
# uvicorn app.main:app --reload
