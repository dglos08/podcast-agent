import html
from abc import ABC, abstractmethod

import re
import requests

from ..models import SearchResult

class SearchProvider(ABC):
    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 3,
    ) -> list[SearchResult]:
        """Search for external evidence related to a query."""
        pass


class BraveSearchProvider(SearchProvider):
    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Brave Search API key is required")

        self.api_key = api_key

    def search(
        self,
        query: str,
        max_results: int = 3,
    ) -> list[SearchResult]:
        print(
            f"[agent] Stage=retrieval "
            f"provider=brave query={query!r}"
        )

        response = requests.get(
            self.BASE_URL,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
            },
            params={
                "q": query,
                "count": max_results,
                "country": "US",
                "search_lang": "en",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()
        web_results = data.get("web", {}).get("results", [])

        results = [
            SearchResult(
                title=clean_text(result.get("title", "")),
                url=result.get("url", ""),
                snippet=clean_text(result.get("description", "")),
            )
            for result in web_results[:max_results]
        ]

        print(
            f"[agent] Stage=retrieval "
            f"results={len(results)}"
        )

        return results

def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", "", value)
    return value.strip()