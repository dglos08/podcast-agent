import argparse
import json
from pathlib import Path

from .agent import PodcastAgent
from .config import Settings
from .models import Transcript
from .providers.anthropic import AnthropicProvider
from .tools.search import BraveSearchProvider
from .verification.verifier import ClaimVerifier

def load_transcript(path: Path) -> Transcript:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Transcript.model_validate(data)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a podcast transcript."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the transcript JSON file.",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Directory for generated output.",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[agent] Loading transcript: {input_path}")

    transcript = load_transcript(input_path)

    print(
        f"[agent] Loaded episode={transcript.episode_id} "
        f"segments={len(transcript.transcript)}"
    )

    settings = Settings()
    provider = AnthropicProvider(settings)
    search_provider = BraveSearchProvider(
        api_key=settings.brave_search_api_key
    )

    verifier = ClaimVerifier(
        provider=provider,
        search_provider=search_provider,
    )

    agent = PodcastAgent(
        provider=provider,
        verifier=verifier,
    )

    print("[agent] Planning: summary, takeaways, quotes, topics, candidate claims")
    print(f"[agent] Invoking model: {settings.model_name}")

    analysis = agent.analyze(transcript)

    print(
        f"[agent] Analysis complete: "
        f"takeaways={len(analysis.takeaways)} "
        f"quotes={len(analysis.quotes)} "
        f"candidate_claims={len(analysis.candidate_claims)} "
        f"fact_checks={len(analysis.fact_checks)}"
    )

    output_path = output_dir / f"{transcript.episode_id}.json"
    output_path.write_text(
        analysis.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print(f"[agent] Wrote output: {output_path}")


if __name__ == "__main__":
    main()