from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class TranscriptSegment(BaseModel):
    timestamp: str
    speaker: str
    section: str | None = None
    text: str


class Transcript(BaseModel):
    episode_id: str
    title: str
    host: str
    guests: list[str]
    transcript: list[TranscriptSegment]


class Quote(BaseModel):
    speaker: str
    timestamp: str
    quote: str


class ClaimStatus(str, Enum):
    VERIFIED = "verified"
    POSSIBLY_OUTDATED_OR_INACCURATE = "possibly_outdated_or_inaccurate"
    UNVERIFIABLE = "unverifiable"

class ClaimType(str, Enum):
    FACTUAL = "factual"
    PREDICTION = "prediction"
    OPINION = "opinion"
    RECOMMENDATION = "recommendation"
    UNVERIFIABLE = "unverifiable"

class Evidence(BaseModel):
    title: str
    source: str
    url: str | None = None
    evidence_summary: str

class EvidenceAssessment(BaseModel):
    status: ClaimStatus
    confidence: float = Field(ge=0.0, le=1.0)
    used_result_indices: list[int] = Field(default_factory=list)
    explanation: str
    
class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class SearchPlan(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=5)
    
class FactCheck(BaseModel):
    claim: str
    timestamp: str
    status: ClaimStatus
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    explanation: str


class CandidateClaim(BaseModel):
    claim: str
    timestamp: str

class ClassifiedClaim(BaseModel):
    claim: str
    timestamp: str
    claim_type: ClaimType
    should_verify: bool
    reasoning: str
    @model_validator(mode="after")
    def validate_verification_routing(self):
        expected = self.claim_type == ClaimType.FACTUAL

        if self.should_verify != expected:
            raise ValueError(
                f"should_verify must be {expected} "
                f"when claim_type={self.claim_type.value}"
            )

        return self

class EpisodeAnalysis(BaseModel):
    episode_id: str
    title: str
    summary: str
    takeaways: list[str] = Field(min_length=5, max_length=5)
    quotes: list[Quote]
    topics: list[str]
    candidate_claims: list[CandidateClaim] = Field(default_factory=list)
    fact_checks: list[FactCheck] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def validate_summary_length(cls, value: str) -> str:
        word_count = len(value.split())

        if not 200 <= word_count <= 300:
            raise ValueError(
                f"Summary must contain 200-300 words; received {word_count}"
            )

        return value