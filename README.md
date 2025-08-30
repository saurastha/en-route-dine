# En-Route Dine

Find the perfect restaurant right on your travel route without the hassle of detours. Whether you're on a cross-country road trip or just navigating your daily commute, En-Route Dine uses AI to understand your cravings and recommends the best spots along your journey, saving you time and helping you discover great food.

## 🎯 The Problem

Finding a good place to eat while traveling—whether it's a long road trip or your daily commute—is often a hassle. You find yourself:

- Jugging multiple apps (Maps, review sites).
- Guessing how far a restaurant is from your actual route.
- Manually searching for places that match what you're in the mood for.

This project aims to solve that problem by finding the optimal restaurant _on the route_ you are traveling, allowing you to grab a quality meal and continue your travel without getting off track, ultimately saving time and stress.

## ✨ Core Features

- **Route-Aware Search**: Finds restaurants within a specified radius of your navigation path, not just around a single point.
- **AI-Powered Recommendations**: Leverages Large Language Models (LLMs) to understand natural language queries (e.g., _"cozy Italian place with great pasta"_) and scores restaurants based on how well they match.
- **Dynamic Routing**: Provides an updated map link with the chosen restaurant as a waypoint.
- **Service Flexibility**: Easily switch between different service providers for maps, search, and AI models via configuration.
    - **Maps**: Google Maps, OpenStreetMap
    - **Search**: Google Search, Tavily
    - **LLM**: OpenAI
- **Interactive UI**: A simple and clean web interface built with Streamlit for easy interaction.

## 🏛️ System Architecture

The project is built with a modern Python stack, emphasizing separation of concerns and scalability.

1.  **FastAPI Backend**: An API server that handles all the core logic.
    - `/api/recommendations-on-route`: The main endpoint that orchestrates the entire workflow.
    - `/health`: A health check endpoint to monitor service status.

2.  **Streamlit Frontend**: A user-friendly web application for inputting travel details and viewing recommendations. It communicates with the FastAPI backend.

3.  **Service Factory Pattern**: A `ServiceFactory` dynamically creates service clients (for Maps, Search, LLM) based on environment variables. This decouples the core application logic from the specific implementations of external services, making it easy to extend or swap them out.

4.  **External APIs**: The engine relies on several external services:
    - **Maps Service**: Calculates the route polyline and finds initial restaurant candidates (Google Maps API or OpenRouteService/Overpass API).
    - **Search Service**: Gathers additional context and reviews for candidate restaurants (Google Custom Search API or Tavily API).
    - **LLM Service**: Analyzes the user's query, restaurant data, and web context to generate a "match score" and justification (OpenAI API or Google Gemini API).

### Workflow Logic

When a user requests recommendations:

1.  The **Maps Service** calculates the primary route from origin to destination.
2.  It then queries for all restaurants within a given radius of the entire route's polyline.
3.  The results are filtered by minimum rating and sorted to find the top candidates.
4.  For each top candidate, the application concurrently:
    - Calls the **Search Service** to get recent reviews or details.
    - Calls the **LLM Service** with all the data to get a match score (1-10) and a justification.
5.  The final list is ranked by the AI match score and returned to the user.
6.  An updated map link including the top-ranked restaurant is generated.

## 🚀 Getting Started

Follow these steps to set up and run the project locally.

### Prerequisites

- Python 3.12+
- [UV](https://docs.astral.sh/uv/getting-started/installation/) for dependency management
- API keys for the services you intend to use (e.g., Google Maps, OpenAI, etc.)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/en-route-dine.git
cd en-route-dine
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Configure Environment Variables

The application is configured using environment variables. Copy the example file and fill in your API keys and service choices.

```bash
touch .env
```

Now, edit the `.env` file:

```ini
# .env file

# --- Service Provider Choices ---
# MAP_SERVICE: "google" or "osm"
# SEARCH_PROVIDER: "google" or "tavily"
# LLM_PROVIDER: "openai" or "gemini"
MAP_SERVICE="osm"
SEARCH_PROVIDER="tavily"
LLM_PROVIDER="openai"

# --- API Keys ---
# Google
GOOGLE_MAPS_API_KEY="YOUR_GOOGLE_MAPS_API_KEY"
GOOGLE_SEARCH_API_KEY="YOUR_GOOGLE_SEARCH_API_KEY"
GOOGLE_CSE_ID="YOUR_CUSTOM_SEARCH_ENGINE_ID"

# OpenStreetMap (requires a free OpenRouteService key)
OPENROUTE_SERVICE_API_KEY="YOUR_OPENROUTESERVICE_API_KEY"

# LLM Providers (add your OpenAI or Gemini key)
# For aisuite library, ensure OPENAI_API_KEY is set
OPENAI_API_KEY="sk-..."
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Search Providers
TAVILY_API_KEY="YOUR_TAVILY_API_KEY"
```

### 4. Run the Application

You need to run two separate processes: the FastAPI backend and the Streamlit frontend.

**Terminal 1: Start the FastAPI Backend**

```bash
uv run uvicorn main:app --reload --port 8000
```

**Terminal 2: Start the Streamlit Frontend**

```bash
uv run streamlit run webapp.py
```

## 🛠️ API Endpoints

You can also interact with the backend API directly.

- `POST /api/recommendations-on-route`
    - Calculates a route and returns restaurant recommendations.
    - **Body**:
        ```json
        {
            "origin": "San Francisco, CA",
            "destination": "Los Angeles, CA",
            "query": "quick and healthy lunch spot",
            "min_rating": 4.2,
            "use_current_location": false,
            "radius": 1000
        }
        ```

- `GET /health`
    - Checks the status of the API and its configured services.

## 🔮 Future Improvements

Key areas for future work include:

- **Asynchronous I/O**: Migrating all blocking network calls (`requests`) to an async client (`httpx`) to fully leverage FastAPI's performance.
- **Caching**: Implementing a caching layer (e.g., Redis) to store route calculations and search results, reducing latency and API costs for common requests.
- **Real-Time Streaming**: Using WebSockets to stream recommendations to the UI as they are processed, improving perceived performance.
- **Enhanced Filtering**: Adding more user preferences, such as price range, cuisine type, and dietary restrictions.
- **Broader Test Coverage**: Increasing the number of unit and integration tests.
