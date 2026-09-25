import pytest
from pydantic import ValidationError

from src.podcast_agent.models import (
    ClaimType,
    ClassifiedClaim,
    EpisodeAnalysis,
)


def make_summary(word_count: int) -> str:
    return " ".join(["word"] * word_count)


def test_episode_analysis_accepts_valid_summary() -> None:
    analysis = EpisodeAnalysis(
        episode_id="test-001",
        title="Test Episode",
        summary=make_summary(200),
        takeaways=[
            "Takeaway 1",
            "Takeaway 2",
            "Takeaway 3",
            "Takeaway 4",
            "Takeaway 5",
        ],
        quotes=[],
        topics=["testing"],
    )

    assert len(analysis.summary.split()) == 200


@pytest.mark.parametrize("word_count", [199, 301])
def test_episode_analysis_rejects_invalid_summary_length(
    word_count: int,
) -> None:
    with pytest.raises(
        ValidationError,
        match="Summary must contain 200-300 words",
    ):
        EpisodeAnalysis(
            episode_id="test-001",
            title="Test Episode",
            summary=make_summary(word_count),
            takeaways=[
                "Takeaway 1",
                "Takeaway 2",
                "Takeaway 3",
                "Takeaway 4",
                "Takeaway 5",
            ],
            quotes=[],
            topics=["testing"],
        )


def test_episode_analysis_requires_exactly_five_takeaways() -> None:
    with pytest.raises(ValidationError):
        EpisodeAnalysis(
            episode_id="test-001",
            title="Test Episode",
            summary=make_summary(200),
            takeaways=[
                "Takeaway 1",
                "Takeaway 2",
                "Takeaway 3",
                "Takeaway 4",
            ],
            quotes=[],
            topics=["testing"],
        )


def test_factual_claim_requires_verification() -> None:
    claim = ClassifiedClaim(
        claim="Some hospitals use AI to analyze X-rays.",
        timestamp="00:55",
        claim_type=ClaimType.FACTUAL,
        should_verify=True,
        reasoning="Externally verifiable statement.",
    )

    assert claim.should_verify is True


def test_prediction_cannot_be_routed_to_verification() -> None:
    with pytest.raises(
        ValidationError,
        match="should_verify must be False",
    ):
        ClassifiedClaim(
            claim="Remote-first companies will dominate hiring.",
            timestamp="05:00",
            claim_type=ClaimType.PREDICTION,
            should_verify=True,
            reasoning="Future prediction.",
        )


def test_factual_claim_cannot_skip_verification() -> None:
    with pytest.raises(
        ValidationError,
        match="should_verify must be True",
    ):
        ClassifiedClaim(
            claim="The FDA reviews certain AI medical systems.",
            timestamp="01:15",
            claim_type=ClaimType.FACTUAL,
            should_verify=False,
            reasoning="Externally verifiable statement.",
        )