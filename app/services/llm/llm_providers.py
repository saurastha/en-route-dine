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
            system_prompt = "You are a helpful restaurant recommendation assistant. Your task is to evaluate how well a restaurant matches a user's request."

        user_prompt = f"""
        **User's Request:** "{user_query}"

        **Restaurant Information:**
        - Name: {restaurant_data.get("name")}
        - Rating: {restaurant_data.get("rating")} out of 5 stars from {restaurant_data.get("user_ratings_total")} users.
        - Additional Context from the Web: "{search_context}"

        **Your Task:**
        1. Carefully analyze the user's request and all the restaurant information.
        2. Determine how well the restaurant fits the request on a scale of 1 (poor match) to 10 (perfect match).
        3. Provide a brief, one-sentence justification for your score.
        4. Respond ONLY with a valid JSON object in the following format: {{"score": <your_score>, "justification": "<your_one_sentence_justification>"}}

        Do not add any other text, explanations, or markdown formatting outside of the JSON object.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=self._build_messages(system_prompt, user_prompt),
                temperature=self.config.temperature,
            )
            json_response = json.loads(response.choices[0].message.content)
            return json_response
        except Exception as e:
            logger.info(
                f"Error getting LLM score for {restaurant_data.get('name')}: {e}"
            )
            return {"score": 0, "justification": "Error during analysis."}
