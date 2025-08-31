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
        user_prompt: str,
        system_prompt: str = None,
    ) -> dict:
        if not system_prompt:
            system_prompt = "You are a helful assistant."

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
            logger.error(f"LLM call failed: {e}")
            return {"score": 0, "justification": "Analysis error."}
