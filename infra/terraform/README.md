# Terraform Reference Infrastructure

This directory contains a deliberately scoped Terraform reference for the
AWS resources directly owned by the Podcast Content Agent.

It complements the production architecture documented in
[`../../docs/production-architecture.md`](../../docs/production-architecture.md).
It is not intended to provision the complete production platform.

## Implemented Resources

The reference configuration provisions:

- Amazon ECR repository for immutable application images
- Amazon S3 bucket for transcript and result persistence
- S3 public-access protections and versioning
- Amazon SQS job queue
- Amazon SQS dead-letter queue
- SQS redrive policy
- Least-privilege IAM policy for worker access to S3 and SQS

## Scope Boundary

The production architecture assumes that the application may be deployed
into an existing customer AWS and Kubernetes platform.

This reference therefore does not provision:

- VPCs or subnets
- NAT gateways or other egress infrastructure
- Amazon EKS
- Application Load Balancers
- KEDA
- Karpenter
- Kubernetes resources
- observability infrastructure
- workload-identity bindings
- secret values

Those concerns are described in the production architecture but are
intentionally excluded from this Terraform implementation rather than
assuming a customer's networking, Kubernetes, identity, security, and
observability standards.

Kubernetes application resources are represented separately by the Helm
chart under `deploy/helm/podcast-content-agent`.

## Workload Identity

Terraform creates the IAM permissions policy required by the worker but
does not bind that policy to a specific EKS identity mechanism.

In a production deployment, the platform would bind this policy to the
worker's Kubernetes identity using the customer's supported mechanism,
such as EKS Pod Identity or IAM Roles for Service Accounts (IRSA).

This keeps application permissions separate from platform-specific
identity configuration.

## State

This reference does not define a Terraform backend.

A production deployment should use the customer's approved remote-state
backend, encryption, access controls, locking strategy, and environment
separation rather than embedding assumptions about state management in
the reference configuration.

## Validation

Initialize Terraform without configuring a backend:

```bash
terraform init -backend=false