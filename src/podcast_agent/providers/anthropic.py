from anthropic import Anthropic

from ..config import Settings
from .base import ModelProvider


class AnthropicProvider(ModelProvider):
    def __init__(self, settings: Settings) -> None:
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model_name = settings.model_name

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        message = self.client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
        )

        return message.content[0].text