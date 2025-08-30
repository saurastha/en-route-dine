from typing import Optional

from loguru import logger

from .config import settings
from .services.llm.base import LLMService
from .services.llm.llm_providers import LLMCaller, LLMConfigs
from .services.maps.base import MapsService
from .services.maps.google_maps import GoogleMapsService
from .services.maps.open_street_map import OpenStreetMapService
from .services.search.base import SearchService
from .services.search.google_search import GoogleSearchService
from .services.search.tavily_search import TavilySearchService


class ServiceFactory:
    @staticmethod
    def create_maps_service() -> MapsService:
        map_service = settings.map_service.lower()

        if map_service == "google":
            if not settings.google_maps_api_key:
                logger.warning(
                    "Google Maps API key not found, falling back to OpenStreetMap"
                )
                return OpenStreetMapService(
                    ors_api_key=settings.openrouteservice_api_key
                )
            return GoogleMapsService(api_key=settings.google_maps_api_key)

        elif map_service in ["osm", "openstreetmap"]:
            return OpenStreetMapService(
                ors_api_key=settings.openrouteservice_api_key
            )

        else:
            logger.warning(
                f"Unknown map service: {map_service}, defaulting to Google Maps"
            )
            if settings.google_maps_api_key:
                return GoogleMapsService(api_key=settings.google_maps_api_key)
            else:
                return OpenStreetMapService(
                    ors_api_key=settings.openrouteservice_api_key
                )

    @staticmethod
    def create_search_service() -> Optional[SearchService]:
        search_provider = settings.search_provider.lower()

        if search_provider == "tavily" and settings.tavily_api_key:
            return TavilySearchService(api_key=settings.tavily_api_key)
        elif (
            search_provider == "google"
            and settings.google_search_api_key
            and settings.google_cse_id
        ):
            return GoogleSearchService(
                api_key=settings.google_search_api_key,
                cse_id=settings.google_cse_id,
            )
        elif settings.google_search_api_key and settings.google_cse_id:
            return GoogleSearchService(
                api_key=settings.google_search_api_key,
                cse_id=settings.google_cse_id,
            )
        elif settings.tavily_api_key:
            return TavilySearchService(api_key=settings.tavily_api_key)
        else:
            logger.warning("No search service credentials found")
            return None

    @staticmethod
    def create_llm_service() -> LLMService:
        llm_config = LLMConfigs()

        if settings.llm_provider.lower() == "gemini":
            llm_config.model = "gemini-1.5-pro"
        elif settings.llm_provider.lower() == "openai":
            llm_config.model = "openai:gpt-4o"

        return LLMCaller(llm_config)
