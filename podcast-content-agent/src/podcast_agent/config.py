import os


class Settings:
    def __init__(self) -> None:
        self.model_provider = os.getenv("MODEL_PROVIDER", "anthropic")
        self.model_name = os.getenv("MODEL_NAME", "claude-haiku-4-5")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.brave_search_api_key = os.getenv("BRAVE_SEARCH_API_KEY")

        if self.model_provider == "anthropic" and not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY must be set when MODEL_PROVIDER=anthropic"
            )

        if not self.brave_search_api_key:
            raise RuntimeError(
                "BRAVE_SEARCH_API_KEY must be set for fact checking"
            )