import json
from json import JSONDecodeError

from pydantic import ValidationError

from urllib.parse import urlparse

from ..models import (
    CandidateClaim,
    ClassifiedClaim,
    Evidence,
    EvidenceAssessment,
    FactCheck,
    SearchPlan,
    SearchResult,
)

from ..tools.search import SearchProvider
from ..providers.base import ModelProvider


CLASSIFIER_SYSTEM_PROMPT = """
You classify statements extracted from podcast transcripts.

Classify each statement into exactly one category:

- factual:
  A present or past assertion about the external world that could
  reasonably be checked against authoritative external evidence.

- prediction:
  A statement forecasting what will or may happen in the future.

- opinion:
  A subjective belief, judgment, interpretation, or preference.

- recommendation:
  Advice about what someone should do.

- unverifiable:
  A statement that may describe an event or experience but cannot
  reasonably be verified using external evidence.

Set should_verify=true ONLY for factual claims that are appropriate
for external retrieval.

Predictions, opinions, recommendations, and unverifiable statements
must have should_verify=false.

Return only valid JSON.
Do not use Markdown code fences.
"""

SEARCH_PLANNER_SYSTEM_PROMPT = """
You plan web searches for fact-checking podcast claims.

Given a factual claim, generate a small set of focused search queries
that will gather enough external evidence to evaluate the entire claim.

Requirements:
- Generate between 1 and 5 queries.
- Decompose compound claims when necessary.
- Prefer queries likely to surface authoritative or primary sources.
- Do not determine whether the claim is true.
- Do not provide evidence yourself.
- Do not generate unnecessary duplicate queries.
- Return only valid JSON.
- Do not use Markdown code fences.
"""

EVIDENCE_EVALUATOR_SYSTEM_PROMPT = """
You evaluate factual claims using only the supplied web search evidence.

Do not rely on your own knowledge.

Assign exactly one status:

- verified:
  The supplied evidence directly supports the material factual content
  of the claim.

- possibly_outdated_or_inaccurate:
  The evidence contradicts, materially qualifies, or indicates that
  some factual portion of the claim may be inaccurate or outdated.

- unverifiable:
  The supplied evidence is insufficient, irrelevant, or does not allow
  the claim to be reliably evaluated.

For compound claims, evaluate the entire claim. Do not mark the entire
claim verified when evidence supports only one component.

Use only evidence supplied in the numbered search results.

used_result_indices must contain only the indices of results that
materially support your assessment.

confidence represents confidence in the assessment based on the
supplied evidence. It is not a calibrated probability.

Return only valid JSON.
Do not use Markdown code fences.
"""

def parse_json_response(raw_response: str) -> dict:
    content = raw_response.strip()

    if content.startswith("```json"):
        content = content[len("```json"):].strip()
    elif content.startswith("```"):
        content = content[len("```"):].strip()

    if content.endswith("```"):
        content = content[:-3].strip()

    return json.loads(content)


class ClaimVerifier:
    def __init__(
        self,
        provider: ModelProvider,
        search_provider: SearchProvider | None = None,
    ) -> None:
        self.provider = provider
        self.search_provider = search_provider

    def classify(self, candidate: CandidateClaim) -> ClassifiedClaim:
        user_prompt = f"""
Classify this candidate statement:

Claim: {candidate.claim}
Timestamp: {candidate.timestamp}

Return exactly this JSON structure:

{{
  "claim": "{candidate.claim}",
  "timestamp": "{candidate.timestamp}",
  "claim_type": "factual | prediction | opinion | recommendation | unverifiable",
  "should_verify": true,
  "reasoning": "brief explanation"
}}
"""

        print(
            f"[agent] Stage=claim_classification "
            f"timestamp={candidate.timestamp}"
        )

        raw_response = self.provider.generate(
            system_prompt=CLASSIFIER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        try:
            parsed = parse_json_response(raw_response)
            classified = ClassifiedClaim.model_validate(parsed)
        except (JSONDecodeError, ValidationError) as exc:
            raise RuntimeError(
                f"Claim classification failed for "
                f"{candidate.timestamp}: {exc}"
            ) from exc

        print(
            f"[agent] Claim={candidate.timestamp} "
            f"type={classified.claim_type.value} "
            f"verify={classified.should_verify}"
        )

        return classified

    def plan_search(
        self,
        classified_claim: ClassifiedClaim,
    ) -> SearchPlan:
        if not classified_claim.should_verify:
            raise ValueError(
                "Search planning requires a claim with should_verify=True"
            )

        user_prompt = f"""
    Create a web search plan for this factual claim:

    Claim: {classified_claim.claim}

    Return exactly this JSON structure:

    {{
    "queries": [
        "search query"
    ]
    }}
    """

        print(
            f"[agent] Stage=search_planning "
            f"timestamp={classified_claim.timestamp}"
        )

        raw_response = self.provider.generate(
            system_prompt=SEARCH_PLANNER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        try:
            parsed = parse_json_response(raw_response)
            plan = SearchPlan.model_validate(parsed)
        except (JSONDecodeError, ValidationError) as exc:
            raise RuntimeError(
                f"Search planning failed for "
                f"{classified_claim.timestamp}: {exc}"
            ) from exc

        print(
            f"[agent] Stage=search_planning "
            f"queries={len(plan.queries)}"
        )

        return plan

    def execute_search_plan(
        self,
        plan: SearchPlan,
        max_results_per_query: int = 3,
    ) -> list[SearchResult]:
        if self.search_provider is None:
            raise RuntimeError(
                "Search provider is required to execute a search plan"
            )

        evidence: list[SearchResult] = []
        seen_urls: set[str] = set()

        for query in plan.queries:
            results = self.search_provider.search(
                query=query,
                max_results=max_results_per_query,
            )

            for result in results:
                if result.url in seen_urls:
                    continue

                seen_urls.add(result.url)
                evidence.append(result)

        print(
            f"[agent] Stage=retrieval "
            f"unique_evidence={len(evidence)}"
        )

        return evidence

    def evaluate_evidence(
        self,
        classified_claim: ClassifiedClaim,
        evidence: list[SearchResult],
    ) -> EvidenceAssessment:
        if not classified_claim.should_verify:
            raise ValueError(
                "Evidence evaluation requires a claim with should_verify=True"
            )

        if not evidence:
            return EvidenceAssessment(
                status="unverifiable",
                confidence=1.0,
                used_result_indices=[],
                explanation="No external evidence was retrieved.",
            )

        evidence_text = "\n\n".join(
            f"[{index}]\n"
            f"Title: {result.title}\n"
            f"URL: {result.url}\n"
            f"Snippet: {result.snippet}"
            for index, result in enumerate(evidence, start=1)
        )

        user_prompt = f"""
    Evaluate this factual claim:

    Claim:
    {classified_claim.claim}

    Retrieved evidence:

    {evidence_text}

    Return exactly this JSON structure:

    {{
    "status": "verified | possibly_outdated_or_inaccurate | unverifiable",
    "confidence": 0.0,
    "used_result_indices": [1],
    "explanation": "brief evidence-based explanation"
    }}
    """

        print(
            f"[agent] Stage=evidence_evaluation "
            f"timestamp={classified_claim.timestamp} "
            f"evidence={len(evidence)}"
        )

        raw_response = self.provider.generate(
            system_prompt=EVIDENCE_EVALUATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        try:
            parsed = parse_json_response(raw_response)
            assessment = EvidenceAssessment.model_validate(parsed)
        except (JSONDecodeError, ValidationError) as exc:
            raise RuntimeError(
                f"Evidence evaluation failed for "
                f"{classified_claim.timestamp}: {exc}"
            ) from exc

        invalid_indices = [
            index
            for index in assessment.used_result_indices
            if index < 1 or index > len(evidence)
        ]

        if invalid_indices:
            raise RuntimeError(
                f"Evidence evaluator returned invalid result indices: "
                f"{invalid_indices}"
            )

        print(
            f"[agent] Stage=evidence_evaluation "
            f"status={assessment.status.value} "
            f"confidence={assessment.confidence:.2f}"
        )

        return assessment

    def build_fact_check(
        self,
        classified_claim: ClassifiedClaim,
        evidence: list[SearchResult],
        assessment: EvidenceAssessment,
    ) -> FactCheck:
        selected_evidence: list[Evidence] = []

        for index in assessment.used_result_indices:
            result = evidence[index - 1]

            selected_evidence.append(
                Evidence(
                    title=result.title,
                    source=urlparse(result.url).netloc,
                    url=result.url,
                    evidence_summary=result.snippet,
                )
            )

        return FactCheck(
            claim=classified_claim.claim,
            timestamp=classified_claim.timestamp,
            status=assessment.status,
            confidence=assessment.confidence,
            evidence=selected_evidence,
            explanation=assessment.explanation,
        )