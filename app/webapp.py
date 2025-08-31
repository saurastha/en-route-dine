import pandas as pd
import requests
import streamlit as st

FASTAPI_URL = "http://127.0.0.1:8000"


def get_recommendations(
    origin, destination, query, min_rating, use_current_location, radius
):
    """
    Sends a request to the FastAPI backend to get restaurant recommendations.
    """
    endpoint = f"{FASTAPI_URL}/api/recommendations-on-route"
    payload = {
        "origin": origin,
        "destination": destination,
        "query": query,
        "min_rating": min_rating,
        "use_current_location": use_current_location,
        "radius": radius,
    }
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to the recommendation service: {e}")
        return None


def main():
    """
    The main function for the Streamlit UI.
    """
    st.set_page_config(page_title="En-Route Dine", layout="wide")

    st.title("En-Route Dine: AI Restaurant Recommender")
    st.markdown(
        "Find the best restaurants along your route that match your cravings!"
    )

    with st.sidebar:
        st.header("Your Journey")
        use_current_location = st.checkbox(
            "Use my current location for the origin"
        )
        origin = ""
        if not use_current_location:
            origin = st.text_input("Origin", "New York, NY")
        destination = st.text_input("Destination", "Boston, MA")

        st.header("Your Preferences")
        query = st.text_input(
            "What are you in the mood for?",
            placeholder="e.g., 'cozy Italian restaurant with great pasta'",
        )
        max_deviation_from_route = st.slider(
            "Radius of search from route (m)", 500, 2000, 700, 100
        )
        min_rating = st.slider("Minimum restaurant rating", 1.0, 5.0, 1.0, 0.1)

        if st.button("Find Restaurants"):
            if not destination or not query:
                st.warning(
                    "Please provide a destination and what you're looking for."
                )
            else:
                with st.spinner("Finding the best spots for you..."):
                    recommendations = get_recommendations(
                        origin,
                        destination,
                        query,
                        min_rating,
                        use_current_location,
                        max_deviation_from_route,
                    )
                    st.session_state.recommendations = recommendations

    if (
        "recommendations" in st.session_state
        and st.session_state.recommendations
    ):
        recommendations = st.session_state.recommendations
        if recommendations["restaurants"]:
            st.header("Top Recommendations")

            df = pd.DataFrame(recommendations["restaurants"])

            for index, row in df.iterrows():
                with st.container():
                    st.subheader(f"{index + 1}. {row['name']}")
                    st.write(f"**Address:** {row['address']}")
                    st.write(
                        f"**Rating:** {row['rating']} ({row['user_ratings_total']} reviews)"
                    )
                    st.write(f"**Match Score:** {row['match_score']}/10")
                    st.info(f"**Justification:** {row['justification']}")
                    st.write(
                        f"**Distance from route:** {row['distance_from_route_km']:.2f} km"
                    )
                    st.markdown(
                        f"[View on Map]({row['map_link']})",
                        unsafe_allow_html=True,
                    )
                    st.markdown("---")
        else:
            st.info(
                "No restaurants found matching your criteria. Try adjusting the rating or your query."
            )

        with st.expander("View Route Summary"):
            for step in recommendations.get("route_summary", []):
                st.write(step)


if __name__ == "__main__":
    main()
