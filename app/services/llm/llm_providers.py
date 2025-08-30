import json
from typing import Dict, List

import aisuite as ai
from loguru import logger

from .base import LLMService


class LLMConfigs:
    model: str = "openai:gpt-4o"
    temperature: float = 0.01


class LLMCaller(LLMService):
    def __init__(self, config: LLMConfigs) -> None:
        self.config = config
        self.client = ai.Client()

    @staticmethod
    def _build_messages(system_prompt, user_prompt) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def ask_llm(
        self,
        user_query: str,
        restaurant_data: dict,
        search_context: str,
        system_prompt: str = None,
    ) -> dict:
        if not system_prompt:
            system_prompt = "You are a restaurant recommendation assistant. Evaluate how well a restaurant matches a user's request."

        user_prompt = f"""
        **User's Request:** "{user_query}"

        **Restaurant Information:**
        - Name: {restaurant_data.get("name")}
        - Rating: {restaurant_data.get("rating")} out of 5 stars from {restaurant_data.get("user_ratings_total")} users.
        - Additional Context: "{search_context}"

        **Task:**
        1. Analyze how well the restaurant fits the request (1-10 scale).
        2. Provide a brief justification.
        3. Respond with JSON: {{"score": <score>, "justification": "<justification>"}}
        """

        try:
            logger.info(f"Calling {self.config.model}")
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=self._build_messages(system_prompt, user_prompt),
                temperature=self.config.temperature,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"LLM error for {restaurant_data.get('name')}: {e}")
            return {"score": 0, "justification": "Analysis error."}
