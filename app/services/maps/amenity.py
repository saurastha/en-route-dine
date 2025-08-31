from enum import Enum


class FoodAmenity(str, Enum):
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    FAST_FOOD = "fast_food"
    BAR = "bar"
    PUB = "pub"
    BIERGARTEN = "biergarten"
    FOOD_COURT = "food_court"
    ICE_CREAM = "ice_cream"

    @classmethod
    def get_all_values(cls) -> list[str]:
        return [item.value for item in cls]


SYSTEM_PROMPT = """
    You are an intelligent API assistant. Your task is to classify a user's food-related query into one or more predefined amenity categories from a provided list. Respond only with a JSON object containing a list of the most relevant amenity strings. If no specific category matches, default to ["restaurant"]. Do not provide any explanation or conversational text.
    """

USER_PROMPT = """
**User Query:** "{query}"

**Available Amenity Categories:**
{amenity_list}

Based on the query, identify the most relevant amenity categories from the list.

**JSON Response format:**
{{"amenities": ["amenity_1", "amenity_2"]}}
"""
