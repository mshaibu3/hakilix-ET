from __future__ import annotations

import json
import logging
import os
import sys
from typing import Optional

import structlog

def init_logging(service_name: str) -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level, logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Add default fields via structlog contextvars in middleware
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = True
    logging.getLogger("uvicorn.error").propagate = True

def init_otel(service_name: str) -> None:
    if os.getenv("OTEL_ENABLED", "true").lower() not in ("1", "true", "yes"):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        resource = Resource.create({
            "service.name": service_name,
            "deployment.environment": os.getenv("HAKILIX_ENV", os.getenv("HAKILIX_ENVIRONMENT","dev")),
        })
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter()  # uses OTEL_EXPORTER_OTLP_ENDPOINT etc.
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        RequestsInstrumentor().instrument()
        # FastAPI and SQLAlchemy will be instrumented in app factory when available.
    except Exception as e:
        logging.getLogger(__name__).warning("otel_init_failed", extra={"error": str(e)})
