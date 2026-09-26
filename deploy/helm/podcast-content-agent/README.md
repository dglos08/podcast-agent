# Podcast Content Agent Helm Chart

This chart provides a reference Kubernetes deployment for the current
containerized Podcast Content Agent.

## Scope

The current application is implemented as a batch-oriented CLI process.
Accordingly, this chart deploys the application as a Kubernetes `Job`
rather than introducing an HTTP service or long-running worker that does
not exist in the current implementation.

The production architecture described in
[`../../../docs/production-architecture.md`](../../../docs/production-architecture.md)
extends this model into an asynchronous API and worker architecture using
S3 and SQS. That architecture is intentionally documented as production
design rather than represented here as implemented functionality.

## Prerequisites

- Kubernetes cluster
- Helm 3
- Container image accessible to the cluster
- Existing Kubernetes Secret containing:
  - `ANTHROPIC_API_KEY`
  - `BRAVE_SEARCH_API_KEY`
- A mechanism for making the requested transcript available at the
  configured input path

## Validation

Validate the chart without deploying it:

```bash
helm lint deploy/helm/podcast-content-agent
helm template test deploy/helm/podcast-content-agent
