# Podcast Content Agent

A containerized agentic AI application that converts raw podcast transcripts into structured editorial content and performs evidence-backed fact checking.

The system is designed for an advertising agency workflow where podcast transcripts need to be transformed into publishable summaries, takeaways, quotations, topic tags, and reviewed factual claims.

## What the Agent Does

For each transcript, the application:

1. Generates a 200–300 word episode summary.
2. Extracts exactly five key takeaways.
3. Selects notable quotes and preserves their timestamps.
4. Generates topic labels.
5. Identifies candidate factual claims.
6. Classifies claims to determine whether external verification is appropriate.
7. Plans search queries for factual claims.
8. Retrieves external evidence.
9. Evaluates the evidence against each claim.
10. Produces structured JSON containing the editorial analysis and fact-check results.

The application uses an LLM for semantic reasoning while enforcing deterministic validation around model output.

## Agent Workflow

```text
Podcast Transcript
        |
        v
+-------------------+
| Content Analysis  |
|-------------------|
| Summary           |
| Takeaways         |
| Quotes            |
| Topics            |
| Candidate Claims  |
+---------+---------+
          |
          v
+-------------------+
| Claim Classifier  |
+---------+---------+
          |
     +----+-------------------------+
     |                              |
     | factual                      | prediction / opinion /
     |                              | recommendation
     v                              v
+-------------------+          Skip Retrieval
| Search Planner    |
+---------+---------+
          |
          v
+-------------------+
| Search Provider   |
| Brave Web Search  |
+---------+---------+
          |
          v
+-------------------+
| Evidence          |
| Evaluation        |
+---------+---------+
          |
          v
+-------------------+
| Deterministic     |
| Validation        |
+---------+---------+
          |
          v
     JSON Output
```

This is intentionally implemented as a single orchestrated agent rather than a collection of independent agents. The workflow remains explicit, observable, testable, and easier to operate while still allowing the model to make decisions about claim classification, search planning, and evidence evaluation.

## Agentic Behavior

The fact-checking workflow is not a fixed sequence of hard-coded searches.

For each candidate claim, the system reasons about the type of statement and decides whether retrieval should occur.

For factual claims, the agent:

```text
classify claim
      |
      v
decide whether verification is required
      |
      v
plan one or more searches
      |
      v
invoke search tool
      |
      v
observe retrieved evidence
      |
      v
evaluate evidence against claim
      |
      v
produce verification result
```

Predictions, opinions, and recommendations are not automatically treated as externally verifiable facts.

## Safety and Validation Boundaries

LLM output is treated as untrusted application data.

Deterministic controls are applied after model generation:

- Pydantic validates the output schema.
- Summaries must contain 200–300 words.
- Exactly five takeaways are required.
- Quotes are checked against the original transcript.
- Quote timestamps and speakers must match the transcript.
- Typographic quote differences are normalized before comparison.
- Factual claims must be routed to verification.
- Predictions, opinions, and recommendations cannot be routed as factual claims.
- Search results are deduplicated by URL.
- Evidence references must correspond to retrieved search results.
- Final evidence URLs and titles come from retrieved data rather than model-generated provenance.
- Invalid model output enters a bounded correction loop.
- Persistent validation failures terminate rather than silently producing invalid output.

This creates a boundary between probabilistic model reasoning and deterministic application guarantees.

## Fact-Check Results

Factual claims are assigned one of the required verification states:

- `verified`
- `possibly_outdated_or_inaccurate`
- `unverifiable`

A confidence value represents the agent's confidence in its evidence assessment. It should not be interpreted as a statistically calibrated probability.

An unverifiable result is considered a valid outcome. The application does not treat the presence of search results as proof that a claim is true.

## Technology

- Python 3.13
- Anthropic Claude Haiku 4.5
- Brave Web Search
- Pydantic
- Requests
- Pytest
- Docker

The model and search integrations are behind provider interfaces so the application logic is not tightly coupled to a single external provider.

## Repository Structure

```text
podcast-agent/
├── .github/
│   └── workflows/
│       └── ci.yml
├── deploy/
│   └── helm/
│       └── podcast-content-agent/
├── docs/
│   ├── architecture.md
│   ├── decisions.md
│   └── production-architecture.md
├── examples/
│   ├── ep001.json
│   ├── ep002.json
│   └── ep003.json
├── infra/
│   └── terraform/
│       ├── README.md
│       ├── main.tf
│       ├── outputs.tf
│       ├── variables.tf
│       └── versions.tf
├── input/
│   ├── ep001_remote_work.json
│   ├── ep002_ai_healthcare.json
│   └── ep003_bootstrapping.json
├── scripts/
│   └── run-all.sh
├── src/
│   └── podcast_agent/
│       ├── providers/
│       ├── tools/
│       ├── verification/
│       ├── agent.py
│       ├── config.py
│       ├── main.py
│       └── models.py
├── tests/
│   ├── test_agent.py
│   ├── test_models.py
│   └── test_verifier.py
├── .env.example
├── Dockerfile
├── pytest.ini
├── requirements-dev.txt
└── requirements.txt

The core agent implementation lives under `src/podcast_agent/`. Generated
sample results are available under `examples/`. The current Kubernetes
packaging is under `deploy/helm/`, while `infra/terraform/` contains the
deliberately scoped AWS reference infrastructure. The complete proposed
production deployment is documented in `docs/production-architecture.md`.
```

## Configuration

The application requires credentials for the configured model and search providers.

Set:

```bash
export ANTHROPIC_API_KEY="..."
export BRAVE_SEARCH_API_KEY="..."
export MODEL_PROVIDER="anthropic"
export MODEL_NAME="claude-haiku-4-5"
```

Do not commit credentials to the repository.

`.env.example` documents the required configuration variables.

## Run Locally

Create the virtual environment:

```bash
python -m venv .venv
```

### Windows Git Bash

```bash
source .venv/Scripts/activate
pip install -r requirements.txt
```

### Linux / macOS

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Run one transcript:

```bash
python -m src.podcast_agent.main \
  --input input/ep001_remote_work.json
```

Process all supplied transcripts:

```bash
./scripts/run-all.sh
```

Generated files are written to `output/`.

## Run with Docker

Build the image:

```bash
docker build -t podcast-content-agent:local .
```

Run an episode:

```bash
docker run --rm \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e BRAVE_SEARCH_API_KEY="$BRAVE_SEARCH_API_KEY" \
  -e MODEL_PROVIDER="anthropic" \
  -e MODEL_NAME="claude-haiku-4-5" \
  -v "$(pwd)/input:/app/input:ro" \
  -v "$(pwd)/output:/app/output" \
  podcast-content-agent:local \
  --input /app/input/ep001_remote_work.json
```

### Windows Git Bash

Git Bash/MSYS may automatically convert Linux-style container paths into Windows paths.

If that occurs, disable path conversion for the Docker command:

```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e BRAVE_SEARCH_API_KEY="$BRAVE_SEARCH_API_KEY" \
  -e MODEL_PROVIDER="anthropic" \
  -e MODEL_NAME="claude-haiku-4-5" \
  -v "$(pwd)/input:/app/input:ro" \
  -v "$(pwd)/output:/app/output" \
  podcast-content-agent:local \
  --input /app/input/ep001_remote_work.json
```

## Example Execution Trace

The application emits readable operational traces showing the agent's execution plan and major reasoning actions without exposing private model chain-of-thought.

Example:

```text
[agent] Loading transcript: input/ep001_remote_work.json
[agent] Loaded episode=ep001 segments=19
[agent] Planning: summary, takeaways, quotes, topics, candidate claims
[agent] Invoking model: claude-haiku-4-5

[agent] Stage=content_analysis attempt=1/3
[agent] Stage=content_analysis attempt=1 validation=failed
[agent] Stage=content_analysis attempt=2/3

[agent] Stage=fact_checking candidates=...
[agent] Stage=claim_classification ...
[agent] Stage=search_planning ...
[agent] Stage=retrieval provider=brave ...
[agent] Stage=evidence_evaluation ...

[agent] Analysis complete: takeaways=5 quotes=5 candidate_claims=... fact_checks=...
[agent] Wrote output: output/ep001.json
```

The exact claims, searches, results, and retry count may vary between runs because model generation and live web retrieval are nondeterministic.

## Output

Each episode produces a structured JSON document containing:

```json
{
  "episode_id": "ep001",
  "title": "The Future of Remote Work",
  "summary": "...",
  "takeaways": [
    "...",
    "...",
    "...",
    "...",
    "..."
  ],
  "quotes": [
    {
      "speaker": "Mark",
      "timestamp": "01:20",
      "quote": "..."
    }
  ],
  "topics": [
    "remote work",
    "asynchronous communication"
  ],
  "candidate_claims": [
    {
      "claim": "...",
      "timestamp": "01:20"
    }
  ],
  "fact_checks": [
    {
      "claim": "...",
      "timestamp": "01:20",
      "status": "possibly_outdated_or_inaccurate",
      "confidence": 0.75,
      "evidence": [
        {
          "title": "...",
          "source": "...",
          "url": "...",
          "evidence_summary": "..."
        }
      ],
      "explanation": "..."
    }
  ]
}
```

Because model generation and web retrieval are nondeterministic, exact output may differ between executions.

## Example Outputs

Representative outputs from successful end-to-end runs are committed under [`examples/`](examples/):

- [`ep001.json`](examples/ep001.json) — remote-work episode demonstrating prediction filtering and partial factual support
- [`ep002.json`](examples/ep002.json) — healthcare episode demonstrating multiple externally verified claims
- [`ep003.json`](examples/ep003.json) — startup-funding episode demonstrating insufficient-evidence handling

These files are unmodified outputs generated by the application. Runtime output is written to `output/`, which is excluded from source control except for `.gitkeep`.

Because model generation and web retrieval are non-deterministic, exact wording, retrieved evidence, confidence values, and claim classifications may vary between executions.


## Testing

Run:

```bash
pytest -q
```

The deterministic test suite covers:

- summary length enforcement
- exactly five takeaways
- factual claim routing
- prediction routing
- verbatim quote grounding
- quote speaker validation
- typographic quote normalization
- bounded correction/retry behavior
- search-result deduplication
- invalid evidence-reference rejection
- retrieved evidence provenance
- no-evidence behavior

External Anthropic and Brave calls are replaced with fake providers during unit tests so the test suite is deterministic and does not require API access.

## Design Decisions

Several design choices were made to keep the implementation small enough to reason about while preserving realistic production boundaries:

**Single orchestrator instead of a multi-agent swarm.**
The problem does not require multiple independently operating agents. A single explicit controller provides sufficient autonomy while reducing coordination complexity and improving observability.

**Provider abstraction.**
Model and search access are separated from orchestration logic. Anthropic and Brave are the prototype implementations, but the workflow can support other providers.

**Retrieval is not verification.**
Search results are treated as evidence candidates. A separate evidence-evaluation step determines whether the retrieved material actually supports the claim.

**Deterministic validation around probabilistic output.**
Schema, quote grounding, routing invariants, and evidence provenance are enforced in application code rather than relying solely on prompting.

**Bounded retries.**
Invalid model responses can be corrected, but the system does not retry indefinitely.

More detailed decisions are documented in [`docs/decisions.md`](docs/decisions.md).

## Production Deployment

The local implementation demonstrates the agent workflow. A production deployment requires additional infrastructure for asynchronous processing, workload isolation, scaling, security, observability, fault tolerance, and repeatable delivery.

The proposed production architecture uses AWS and Kubernetes, with:

- Amazon EKS
- Amazon SQS and a dead-letter queue
- Amazon S3
- Amazon ECR
- AWS IAM workload identity
- AWS Secrets Manager
- multi-AZ networking
- horizontal worker scaling
- queue-aware autoscaling
- infrastructure provisioning with Terraform
- Kubernetes application deployment with Helm
- CI/CD with workload identity rather than static AWS credentials
- centralized metrics, logs, traces, and alerting

The production architecture is a design proposal and is intentionally separate from the locally implemented application.

See [`docs/production-architecture.md`](docs/production-architecture.md) for the infrastructure diagram, deployment lifecycle, scaling model, fault handling, security controls, cost considerations, and non-functional requirements.

## Current Limitations

This implementation intentionally prioritizes a clear agent workflow and defensible production design over feature breadth.

Current limitations include:

- Fact checking depends on live web-search quality and availability.
- Confidence values are model assessments, not calibrated probabilities.
- The prototype does not maintain a persistent retrieval knowledge base.
- Search-source authority is encouraged through search planning but is not enforced through a formal source-ranking system.
- Model and search-provider failures do not yet include the full retry, circuit-breaking, and fallback behavior proposed for production.
- Production AWS/EKS infrastructure is designed but not provisioned as part of this implementation.
- There is no end-user UI; the application is intentionally exposed as a CLI/container workflow.

These are explicit prototype boundaries rather than assumptions about production readiness.
