from typing import List, Optional

from pydantic import BaseModel


class RecommendationRequest(BaseModel):
    """
    Defines the structure for an incoming recommendation request from the user.
    """

    origin: str
    destination: str
    query: str
    min_rating: Optional[float] = 4.0


class Restaurant(BaseModel):
    """
    Defines the structure for a single restaurant's data in the API response.
    """

    name: str
    address: str
    rating: float
    user_ratings_total: int
    match_score: Optional[int] = None
    justification: Optional[str] = None


class RecommendationResponse(BaseModel):
    """
    Defines the structure for the final API response.
    """

    restaurants: List[Restaurant]
