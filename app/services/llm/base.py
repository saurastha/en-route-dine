from abc import ABC, abstractmethod


class LLMService(ABC):
    @abstractmethod
    def ask_llm(self, user_prompt: str, system_prompt: str) -> dict:
        pass
