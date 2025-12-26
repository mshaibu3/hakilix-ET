# System Architecture (Detail)

This document expands the high-level architecture shown in the main README.

## Components

### API (FastAPI)
- Auth (demo), tenant scoping, resident CRUD
- Telemetry ingest endpoint
- Risk event read APIs for dashboard

### TimescaleDB
- Time-series telemetry hypertable
- Continuous aggregates (optional)
- Risk events and audit tables

### Inference service
- Edge-like worker that consumes telemetry and emits risk signals
- In production this is where:
  - SNN / neuromorphic inference
  - sensor fusion (mmWave + thermal)
  - predictive reablement (micro-degradation detection)
  would live.

### Dashboard (Streamlit)
- Fleet overview and resident detail view
- “Live Snapshot” (single render; stable session state)
- Risk Signals card layout

### Telemetry simulator
- Generates plausible vital sign streams and risk-triggering events
- Round-robin across 10 residents (R-001..R-010)

## Security Boundaries (Demo)
- Single-network docker compose
- Environment-based configuration
- Basic auth token

## Production Security Boundary (Target)
- OIDC + mTLS
- KMS/Vault secret storage
- Network segmentation
- Principle of least privilege DB roles
