from abc import ABC, abstractmethod


class LLMService(ABC):
    """
    Abstract base class for a Large Language Model service.
    Defines the contract for scoring a restaurant based on user query.
    """

    @abstractmethod
    def ask_llm(
        self, user_query: str, restaurant_data: dict, search_context: str
    ) -> dict:
        pass
