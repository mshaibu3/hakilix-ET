from __future__ import annotations

import json
import os
from typing import Any, Dict

import structlog

log = structlog.get_logger()

class Broker:
    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        raise NotImplementedError

class DirectBroker(Broker):
    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        # No-op. Used when API persists directly.
        return

class PubSubBroker(Broker):
    def __init__(self, project_id: str):
        from google.cloud import pubsub_v1
        self.project_id = project_id
        self.client = pubsub_v1.PublisherClient()

    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        data = json.dumps(message).encode("utf-8")
        future = self.client.publish(topic, data=data)
        future.result(timeout=10)

def get_broker() -> Broker:
    if os.getenv("BROKER_TYPE", "direct").lower() != "pubsub":
        return DirectBroker()
    project = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise RuntimeError("GCP_PROJECT required for pubsub broker")
    return PubSubBroker(project_id=project)
