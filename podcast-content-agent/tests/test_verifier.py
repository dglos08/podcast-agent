import json

import pytest

from src.podcast_agent.models import (
    CandidateClaim,
    ClassifiedClaim,
    ClaimType,
    SearchPlan,
    SearchResult,
)
from src.podcast_agent.providers.base import ModelProvider
from src.podcast_agent.tools.search import SearchProvider
from src.podcast_agent.verification.verifier import ClaimVerifier


class FakeModelProvider(ModelProvider):
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.responses[self.calls]
        self.calls += 1
        return response


class FakeSearchProvider(SearchProvider):
    def __init__(self, results_by_query: dict[str, list[SearchResult]]) -> None:
        self.results_by_query = results_by_query

    def search(
        self,
        query: str,
        max_results: int = 3,
    ) -> list[SearchResult]:
        return self.results_by_query.get(query, [])[:max_results]


def make_factual_claim() -> ClassifiedClaim:
    return ClassifiedClaim(
        claim="GitLab has a public company handbook.",
        timestamp="01:20",
        claim_type=ClaimType.FACTUAL,
        should_verify=True,
        reasoning="Externally verifiable.",
    )


def test_search_plan_rejects_non_verifiable_claim() -> None:
    provider = FakeModelProvider([])

    verifier = ClaimVerifier(provider=provider)

    prediction = ClassifiedClaim(
        claim="Remote work will dominate hiring.",
        timestamp="05:00",
        claim_type=ClaimType.PREDICTION,
        should_verify=False,
        reasoning="Future prediction.",
    )

    with pytest.raises(
        ValueError,
        match="should_verify=True",
    ):
        verifier.plan_search(prediction)


def test_execute_search_plan_deduplicates_urls() -> None:
    duplicate = SearchResult(
        title="GitLab Handbook",
        url="https://handbook.gitlab.com/",
        snippet="GitLab's public handbook.",
    )

    second = SearchResult(
        title="GitLab Handbook About",
        url="https://handbook.gitlab.com/handbook/",
        snippet="Information about the handbook.",
    )

    search_provider = FakeSearchProvider(
        {
            "query one": [duplicate, second],
            "query two": [duplicate],
        }
    )

    verifier = ClaimVerifier(
        provider=FakeModelProvider([]),
        search_provider=search_provider,
    )

    plan = SearchPlan(
        queries=["query one", "query two"]
    )

    evidence = verifier.execute_search_plan(plan)

    assert len(evidence) == 2
    assert evidence[0].url == "https://handbook.gitlab.com/"
    assert evidence[1].url == "https://handbook.gitlab.com/handbook/"


def test_evidence_evaluator_rejects_invalid_source_index() -> None:
    provider = FakeModelProvider(
        [
            json.dumps(
                {
                    "status": "verified",
                    "confidence": 0.9,
                    "used_result_indices": [99],
                    "explanation": "The evidence supports the claim.",
                }
            )
        ]
    )

    verifier = ClaimVerifier(provider=provider)

    evidence = [
        SearchResult(
            title="GitLab Handbook",
            url="https://handbook.gitlab.com/",
            snippet="GitLab's public handbook.",
        )
    ]

    with pytest.raises(
        RuntimeError,
        match="invalid result indices",
    ):
        verifier.evaluate_evidence(
            classified_claim=make_factual_claim(),
            evidence=evidence,
        )


def test_build_fact_check_preserves_retrieved_provenance() -> None:
    provider = FakeModelProvider(
        [
            json.dumps(
                {
                    "status": "verified",
                    "confidence": 0.95,
                    "used_result_indices": [1],
                    "explanation": "The source directly supports the claim.",
                }
            )
        ]
    )

    verifier = ClaimVerifier(provider=provider)

    evidence = [
        SearchResult(
            title="The GitLab Handbook",
            url="https://handbook.gitlab.com/",
            snippet="GitLab's public company handbook.",
        )
    ]

    claim = make_factual_claim()

    assessment = verifier.evaluate_evidence(
        classified_claim=claim,
        evidence=evidence,
    )

    fact_check = verifier.build_fact_check(
        classified_claim=claim,
        evidence=evidence,
        assessment=assessment,
    )

    assert fact_check.status.value == "verified"
    assert fact_check.confidence == 0.95
    assert len(fact_check.evidence) == 1

    source = fact_check.evidence[0]

    assert source.title == "The GitLab Handbook"
    assert source.url == "https://handbook.gitlab.com/"
    assert source.source == "handbook.gitlab.com"
    assert source.evidence_summary == "GitLab's public company handbook."


def test_empty_evidence_returns_unverifiable_without_model_call() -> None:
    provider = FakeModelProvider([])

    verifier = ClaimVerifier(provider=provider)

    assessment = verifier.evaluate_evidence(
        classified_claim=make_factual_claim(),
        evidence=[],
    )

    assert assessment.status.value == "unverifiable"
    assert assessment.used_result_indices == []
    assert provider.calls == 0