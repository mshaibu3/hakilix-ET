# Brokered ingestion pipeline

## Why
A broker decouples edge ingest from persistence/inference:
- absorbs bursts
- retries and DLQs
- enables fan-out to multiple consumers (inference, FHIR bridge, analytics)

## Pub/Sub mode
Set:
- `BROKER_TYPE=pubsub`
- `PUBSUB_TOPIC=projects/<p>/topics/hakilix-telemetry`

The API will publish telemetry messages to Pub/Sub.
A worker service (`hakilix-worker`) receives a Pub/Sub push and:
1. persists telemetry to DB
2. forwards to Redis stream for inference workers
