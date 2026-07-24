# Adapter Development Guide

## Implementing a Custom HTTP Adapter

```python
from iios.integration.services.rest_client import BaseRestClient
from typing import Any, Dict, Optional

class MyRestClient(BaseRestClient):
    def call(self, method, url, payload=None, headers=None, params=None, timeout_ms=30000):
        # inject requests/httpx here
        import requests
        r = requests.request(method, url, json=payload, headers=headers, timeout=timeout_ms/1000)
        return {"status_code": r.status_code, "body": r.json()}

    def health_check(self):
        return True
```

## Implementing a Custom Kafka Adapter

```python
from iios.integration.services.kafka_adapter import BaseKafkaAdapter, KafkaMessage
from typing import Dict, List, Optional, Any
from iios.integration.services.constants import MessageDeliveryMode

class MyKafkaAdapter(BaseKafkaAdapter):
    def __init__(self, bootstrap_servers: str):
        # inject kafka-python here
        from kafka import KafkaProducer
        self._producer = KafkaProducer(bootstrap_servers=bootstrap_servers)

    def produce(self, topic, value, key=None, delivery_mode=MessageDeliveryMode.AT_LEAST_ONCE):
        import json
        self._producer.send(topic, value=json.dumps(value).encode())
        return KafkaMessage(topic=topic, key=key, value=value, partition=0, offset=0)

    def consume(self, topic, group_id, max_messages=1, timeout_ms=5000):
        return []

    def health_check(self):
        return True
```

## Registering a Custom Adapter

```python
from iios.integration.services import AdapterDescriptor, AdapterRegistry, AdapterProtocol, ServiceType

registry = AdapterRegistry()
desc = AdapterDescriptor(
    adapter_id    = "my-kafka",
    protocol      = AdapterProtocol.KAFKA,
    service_types = [ServiceType.KAFKA],
    name          = "My Kafka Adapter",
    version       = "1.0.0",
    metadata      = {},
)
registry.register(desc)
```
