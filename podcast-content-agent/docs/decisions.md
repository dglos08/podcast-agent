# Architecture Decisions

This document records the major design decisions made for the Podcast Content Agent and the tradeoffs behind them.

These decisions apply to the take-home implementation unless explicitly identified as production considerations.

## ADR-001: Use Python for the Application

**Decision:** Implement the agent in Python.

**Rationale:** Python provides mature SDK support for model providers, HTTP integrations, structured validation, and testing while keeping the implementation small enough to inspect and reason about.

**Tradeoff:** The architecture is not dependent on Python. Another runtime could implement the same orchestration and provider boundaries.

---

## ADR-002: Use Explicit Application Orchestration

**Decision:** Implement the workflow directly in application code rather than introducing an agent framework.

**Rationale:** The workflow has a relatively small and understandable dependency graph. Explicit orchestration keeps model invocation, tool execution, validation, retries, and failure behavior visible in the application code.

This also makes the agent easier to test without requiring framework-specific abstractions.

**Tradeoff:** An agent framework could become useful for more complex execution graphs, durable state, long-running workflows, or significantly more sophisticated tool coordination. Those capabilities are not required for the current workload.

---

## ADR-003: Use a Single Orchestrated Agent

**Decision:** Use one orchestrated agent workflow rather than multiple independently operating agents.

**Rationale:** Content analysis, claim classification, retrieval planning, and evidence evaluation form a predictable dependency chain. Introducing multiple autonomous agents would add coordination, state management, latency, and additional failure modes without a clear benefit for this workload.

**Tradeoff:** Independent agents may become useful if future requirements introduce parallel research, specialized models, long-running tasks, human approval workflows, or more complex tool use.

---

## ADR-004: Abstract Model Access Behind a Provider Interface

**Decision:** Keep model access behind the `ModelProvider` interface.

**Prototype implementation:** Anthropic Claude Haiku 4.5.

**Rationale:** Core orchestration should not depend directly on a specific model vendor. The provider boundary allows the model backend to change without redesigning the agent workflow.

**Tradeoff:** The abstraction intentionally exposes only the capabilities currently required by the application rather than attempting to normalize every feature offered by every model provider.

**Production consideration:** A customer deployment could use Amazon Bedrock or another approved model provider based on security, networking, governance, availability, performance, and cost requirements.

---

## ADR-005: Use Web Search as the Prototype Retrieval Tool

**Decision:** Use Brave Web Search behind the `SearchProvider` interface.

**Rationale:** Live web search demonstrates actual tool use and allows factual claims to be evaluated against information outside the supplied transcript.

Search planning remains separate from search execution so the model determines what information it needs while application code controls the external tool invocation.

**Tradeoff:** Search quality and source authority vary. Retrieved results are therefore treated as evidence candidates rather than proof that a claim is correct.

**Production consideration:** Customer requirements may favor an approved external search provider, internal knowledge base, enterprise retrieval system, or a combination of retrieval sources.

---

## ADR-006: Treat Model Output as Untrusted Data

**Decision:** Enforce deterministic validation around probabilistic model output.

**Rationale:** A fluent model response does not guarantee schema correctness, grounded quotations, correct routing, or legitimate evidence provenance.

The application therefore enforces:

- Pydantic schema validation
- 200–300 word summary length
- exactly five takeaways
- transcript-grounded quotations
- valid quote speakers and timestamps
- claim-routing invariants
- valid evidence references
- evidence provenance derived from retrieved results
- bounded correction retries

**Tradeoff:** Strict validation can reject model output that might otherwise appear usable. For editorial content and factual verification, explicit rejection is preferable to silently accepting malformed or ungrounded output.

---

## ADR-007: Separate Retrieval from Verification

**Decision:** Do not treat successful information retrieval as successful fact verification.

**Rationale:** A search result may mention a claim without actually supporting it. Retrieval and evidence evaluation are therefore separate stages.

The retrieval layer discovers candidate evidence. The evidence evaluator determines whether the supplied evidence supports the claim.

If no evidence is retrieved, the application returns an `unverifiable` result rather than asking the model to infer evidence.

**Tradeoff:** Separating these stages requires additional model interaction, increasing latency and token usage. The additional cost provides a clearer reasoning boundary and reduces the risk of presenting irrelevant search results as verification.

---

## ADR-008: Preserve Evidence Provenance in Application Code

**Decision:** Do not allow the language model to generate final evidence URLs or source metadata.

**Rationale:** Retrieved search results are numbered before evidence evaluation. The model selects relevant evidence by index, and application code maps those indices back to the original search results.

This preserves the retrieved:

- title
- URL
- source domain
- evidence snippet

Invalid evidence indices are rejected.

**Tradeoff:** This requires additional mapping and validation logic but reduces the risk of fabricated or modified citations entering the final result.

---

## ADR-009: Use Bounded Correction Retries

**Decision:** Allow invalid content-analysis responses to be corrected through a bounded retry loop.

**Rationale:** Model output can occasionally violate deterministic requirements even when the task is otherwise successful. A correction attempt can recover from issues such as schema violations, incorrect summary length, or ungrounded quotations.

The implementation limits content-analysis generation to three attempts.

**Tradeoff:** Retries increase latency and token consumption. A bounded limit prevents persistent failures from becoming uncontrolled retry loops.

---

## ADR-010: Containerize the Prototype and Separate Production Infrastructure

**Decision:** Deliver the implemented application as a locally runnable Docker container while treating cloud and Kubernetes deployment as a separate production architecture concern.

**Rationale:** Docker provides a reproducible execution environment and satisfies the requirement for a locally runnable application without requiring reviewers to provision cloud infrastructure.

Separating application implementation from production infrastructure also allows scalability, networking, security, reliability, and operational concerns to be evaluated independently.

**Tradeoff:** The repository demonstrates the application container but does not provision the proposed production infrastructure.

**Production consideration:** The proposed deployment uses AWS and Amazon EKS, with cloud infrastructure provisioned through Terraform and Kubernetes application resources deployed through Helm.

See [`production-architecture.md`](production-architecture.md) for the production architecture and deployment strategy.