# GCP Deployment Notes (Suggested)

This repository is designed to be deployable on Google Cloud once hardening is complete.

## Recommended target architecture
- Cloud Run (API + Dashboard) or GKE (for full control)
- Managed Redis (Memorystore) if needed
- TimescaleDB: either
  - self-managed on Compute Engine / GKE, or
  - Timescale Cloud (recommended for managed operations)

## Secrets
- GCP Secret Manager for application secrets
- Cloud KMS for key encryption and rotation

## Observability
- Cloud Logging + Cloud Monitoring
- OpenTelemetry collector (sidecar or managed) feeding traces/metrics

## CI/CD (suggested)
- GitHub Actions → Artifact Registry → Cloud Run / GKE
- Terraform for infra provisioning

## Minimum production checklist
- IaC (Terraform)
- OIDC (Entra/Keycloak)
- mTLS between devices and ingestion
- OpenTelemetry end-to-end
- Backpressure with Pub/Sub / Kafka / NATS
