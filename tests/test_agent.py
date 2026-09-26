import json

import pytest

from src.podcast_agent.agent import PodcastAgent, validate_quotes
from src.podcast_agent.models import (
    EpisodeAnalysis,
    Quote,
    Transcript,
    TranscriptSegment,
)
from src.podcast_agent.providers.base import ModelProvider


def make_summary(word_count: int = 200) -> str:
    return " ".join(["word"] * word_count)


def make_transcript() -> Transcript:
    return Transcript(
        episode_id="test-001",
        title="Test Episode",
        host="Sarah",
        guests=["Mark"],
        transcript=[
            TranscriptSegment(
                timestamp="00:45",
                speaker="Mark",
                section="Deep Dive",
                text=(
                    "It's more about async-first culture, documentation, "
                    "and autonomy. Being remote doesn't just mean a location."
                ),
            )
        ],
    )


def make_analysis(
    summary_words: int = 200,
    quote: str = "It's more about async-first culture, documentation, and autonomy.",
) -> EpisodeAnalysis:
    return EpisodeAnalysis(
        episode_id="test-001",
        title="Test Episode",
        summary=make_summary(summary_words),
        takeaways=[
            "Takeaway 1",
            "Takeaway 2",
            "Takeaway 3",
            "Takeaway 4",
            "Takeaway 5",
        ],
        quotes=[
            Quote(
                speaker="Mark",
                timestamp="00:45",
                quote=quote,
            )
        ],
        topics=["remote work"],
        candidate_claims=[],
    )


class FakeProvider(ModelProvider):
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.responses[self.calls]
        self.calls += 1
        return response


def test_validate_quotes_accepts_exact_grounded_quote() -> None:
    transcript = make_transcript()
    analysis = make_analysis()

    validate_quotes(analysis, transcript)


def test_validate_quotes_normalizes_curly_apostrophes() -> None:
    transcript = Transcript(
        episode_id="test-001",
        title="Test Episode",
        host="Sarah",
        guests=["Mark"],
        transcript=[
            TranscriptSegment(
                timestamp="00:45",
                speaker="Mark",
                section="Deep Dive",
                text="It’s more about async-first culture and autonomy.",
            )
        ],
    )

    analysis = make_analysis(
        quote="It's more about async-first culture and autonomy."
    )

    validate_quotes(analysis, transcript)


def test_validate_quotes_rejects_hallucinated_quote() -> None:
    transcript = make_transcript()

    analysis = make_analysis(
        quote="Remote work always increases productivity."
    )

    with pytest.raises(ValueError):
        validate_quotes(analysis, transcript)


def test_validate_quotes_rejects_wrong_speaker() -> None:
    transcript = make_transcript()
    analysis = make_analysis()

    analysis.quotes[0].speaker = "Sarah"

    with pytest.raises(ValueError):
        validate_quotes(analysis, transcript)


def test_agent_retries_after_invalid_summary() -> None:
    invalid_response = {
        "episode_id": "test-001",
        "title": "Test Episode",
        "summary": make_summary(150),
        "takeaways": [
            "Takeaway 1",
            "Takeaway 2",
            "Takeaway 3",
            "Takeaway 4",
            "Takeaway 5",
        ],
        "quotes": [
            {
                "speaker": "Mark",
                "timestamp": "00:45",
                "quote": (
                    "It's more about async-first culture, "
                    "documentation, and autonomy."
                ),
            }
        ],
        "topics": ["remote work"],
        "candidate_claims": [],
        "fact_checks": [],
    }

    valid_response = {
        **invalid_response,
        "summary": make_summary(200),
    }

    provider = FakeProvider(
        responses=[
            json.dumps(invalid_response),
            json.dumps(valid_response),
        ]
    )

    agent = PodcastAgent(provider=provider)

    result = agent.analyze(make_transcript())

    assert provider.calls == 2
    assert len(result.summary.split()) == 200