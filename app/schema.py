from typing import List, Optional

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    origin: Optional[str] = None
    destination: str
    query: str
    min_rating: Optional[float] = 4.0
    use_current_location: bool = False
    radius: int = 700  # meter


class Restaurant(BaseModel):
    name: str
    address: str
    rating: float
    user_ratings_total: int
    match_score: Optional[int] = None
    justification: Optional[str] = None
    distance_from_route_km: Optional[float] = Field(
        None, description="Distance from the main route to the restaurant"
    )
    map_link: Optional[str] = Field(
        None,
        description="Direct link to the route with this restaurant as waypoint",
    )


class RecommendationResponse(BaseModel):
    origin: str
    destination: str
    route_summary: List[str] = Field(
        description="Summary of route steps including the restaurant stop"
    )
    restaurants: List[Restaurant]
