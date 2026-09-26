from abc import ABC, abstractmethod


class ModelProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a text response from the configured model."""
        pass