# Observability

## Structured logs
Services emit JSON logs with consistent fields. In Cloud Run these are parsed by Cloud Logging automatically.

Set:
- `LOG_LEVEL=INFO|DEBUG|...`

## OpenTelemetry
OpenTelemetry traces are enabled by default (can be disabled with `OTEL_ENABLED=false`).
Configure OTLP exporter:
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `OTEL_EXPORTER_OTLP_HEADERS` (if required)

In GCP, common patterns:
- Export OTLP to an OpenTelemetry Collector running as a separate Cloud Run service or in GKE.
- Alternatively use a Cloud Trace exporter if you standardize on Google Ops Agent / Cloud Trace SDKs.
