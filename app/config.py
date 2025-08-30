import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_maps_api_key: Optional[str] = None
    google_search_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouteservice_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None

    map_service: str = "google"
    llm_provider: str = "openai"
    search_provider: str = "google"


settings = Settings(
    google_maps_api_key=os.environ.get("GOOGLE_MAPS_API_KEY"),
    google_search_api_key=os.environ.get("GOOGLE_SEARCH_API_KEY"),
    google_cse_id=os.environ.get("GOOGLE_CSE_ID"),
    gemini_api_key=os.environ.get("GEMINI_API_KEY"),
    openrouteservice_api_key=os.environ.get("OPENROUTE_SERVICE_API_KEY"),
    tavily_api_key=os.environ.get("TAVILY_API_KEY"),
    map_service=os.environ.get("MAP_SERVICE", "google"),
    llm_provider=os.environ.get("LLM_PROVIDER", "openai"),
    search_provider=os.environ.get("SEARCH_PROVIDER", "google"),
)
