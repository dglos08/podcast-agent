import json
from json import JSONDecodeError
from pydantic import ValidationError
from .models import EpisodeAnalysis, Transcript
from .providers.base import ModelProvider
from .verification.verifier import ClaimVerifier

SYSTEM_PROMPT = """
You are a podcast editorial analysis agent.

Your job is to transform a podcast transcript into structured editorial
content while remaining grounded strictly in the supplied transcript.

Requirements:
- Write a clear summary covering the core themes, key discussions,
  outcomes, and opinions.
- The summary MUST contain between 200 and 300 words. This is a hard
  validation constraint; summaries under 200 words or over 300 words
  will be rejected.
- Before returning the JSON, verify that the summary satisfies the
  200-300 word requirement.
- Produce exactly 5 concise takeaways.
- Select notable quotes suitable for show notes or social media.
- Quotes must be verbatim from the transcript.
- Preserve the timestamp and speaker associated with each quote.
- Produce concise topic tags.
- Identify factual claims that could reasonably be verified using an
  external source.
- Do not treat opinions, predictions, recommendations, or subjective
  statements as factual claims.
- Do not fact-check the claims yourself. A separate verification stage
  will do that.
- Do not invent information not present in the transcript.
- Return only valid JSON. Do not use Markdown code fences.
"""
def parse_json_response(raw_response: str) -> dict:
    """Parse a model response that is expected to contain only JSON."""
    content = raw_response.strip()

    if content.startswith("```json"):
        content = content[len("```json"):].strip()
    elif content.startswith("```"):
        content = content[len("```"):].strip()

    if content.endswith("```"):
        content = content[:-3].strip()

    return json.loads(content)

def normalize_quote_text(text: str) -> str:
    """Normalize typographic punctuation for deterministic quote comparison."""
    return (
        text
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .strip()
    )

def validate_quotes(
    analysis: EpisodeAnalysis,
    transcript: Transcript,
) -> None:
    segments_by_timestamp = {
        segment.timestamp: segment
        for segment in transcript.transcript
    }

    for quote in analysis.quotes:
        segment = segments_by_timestamp.get(quote.timestamp)

        if segment is None:
            raise ValueError(
                f"Quote references unknown timestamp: {quote.timestamp}"
            )

        if quote.speaker != segment.speaker:
            raise ValueError(
                f"Quote speaker mismatch at {quote.timestamp}: "
                f"expected {segment.speaker}, received {quote.speaker}"
            )

        normalized_quote = normalize_quote_text(quote.quote)
        normalized_segment = normalize_quote_text(segment.text)

        if normalized_quote not in normalized_segment:
            raise ValueError(
                f"Quote is not verbatim at {quote.timestamp}: "
                f"{quote.quote!r}"
            )
        
class PodcastAgent:
    def __init__(
        self,
        provider: ModelProvider,
        verifier: ClaimVerifier | None = None,
    ) -> None:
        self.provider = provider
        self.verifier = verifier

    def analyze(self, transcript: Transcript) -> EpisodeAnalysis:
        transcript_json = transcript.model_dump_json(indent=2)

        user_prompt = f"""
Analyze the following podcast transcript.

The JSON response must have exactly this structure:

{{
  "episode_id": "string",
  "title": "string",
  "summary": "string",
  "takeaways": [
    "string",
    "string",
    "string",
    "string",
    "string"
  ],
  "quotes": [
    {{
      "speaker": "string",
      "timestamp": "string",
      "quote": "string"
    }}
  ],
  "topics": ["string"],
  "candidate_claims": [
    {{
      "claim": "string",
      "timestamp": "string"
    }}
  ],
  "fact_checks": []
}}

Use the episode_id and title exactly as provided.
fact_checks must be an empty array because verification occurs later.

TRANSCRIPT:
{transcript_json}
"""

        max_attempts = 3
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            print(
                f"[agent] Stage=content_analysis "
                f"attempt={attempt}/{max_attempts}"
            )

            raw_response = self.provider.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )

            try:
                parsed = parse_json_response(raw_response)
                analysis = EpisodeAnalysis.model_validate(parsed)
                validate_quotes(analysis, transcript)

                print(
                    f"[agent] Stage=content_analysis "
                    f"attempt={attempt} validation=success"
                )

                return self.verify_claims(analysis)

            except (JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc

                print(
                    f"[agent] Stage=content_analysis "
                    f"attempt={attempt} validation=failed "
                    f"error={exc}"
                )

                if attempt < max_attempts:
                    user_prompt += f"""

        Your previous response failed validation.

        Validation error:
        {exc}

        Correct the response and return the complete JSON object again.
        Do not use Markdown code fences.
        Do not explain the correction.
        """

        raise RuntimeError(
            f"Content analysis failed after {max_attempts} attempts: "
            f"{last_error}"
        )

    def verify_claims(
        self,
        analysis: EpisodeAnalysis,
    ) -> EpisodeAnalysis:
        if self.verifier is None:
            print("[agent] Stage=fact_checking skipped=no_verifier")
            return analysis

        fact_checks = []

        print(
            f"[agent] Stage=fact_checking "
            f"candidates={len(analysis.candidate_claims)}"
        )

        for candidate in analysis.candidate_claims:
            classified = self.verifier.classify(candidate)

            if not classified.should_verify:
                print(
                    f"[agent] Claim={candidate.timestamp} "
                    f"retrieval=skipped "
                    f"reason={classified.claim_type.value}"
                )
                continue

            plan = self.verifier.plan_search(classified)

            evidence = self.verifier.execute_search_plan(plan)

            assessment = self.verifier.evaluate_evidence(
                classified_claim=classified,
                evidence=evidence,
            )

            fact_check = self.verifier.build_fact_check(
                classified_claim=classified,
                evidence=evidence,
                assessment=assessment,
            )

            fact_checks.append(fact_check)

        analysis.fact_checks = fact_checks

        print(
            f"[agent] Stage=fact_checking "
            f"completed={len(fact_checks)}"
        )

        return analysis