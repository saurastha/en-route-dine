from abc import ABC, abstractmethod


class LLMService(ABC):
    @abstractmethod
    def ask_llm(
        self, user_query: str, restaurant_data: dict, search_context: str
    ) -> dict:
        pass
