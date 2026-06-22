"""Registry for source adapters — discovers and instantiates them."""

from typing import Type

from nozzle.ingestion.base import SourceAdapter
from nozzle.ingestion.wazuh import WazuhAdapter
from nozzle.domain.enums import SourceType


ADAPTER_REGISTRY: dict[SourceType, Type[SourceAdapter]] = {
    SourceType.WAZUH: WazuhAdapter,
    # Future: SourceType.ELASTIC: ElasticAdapter,
    # Future: SourceType.GRAYLOG: GraylogAdapter,
    # Future: SourceType.SPLUNK: SplunkAdapter,
}


def get_adapter(source_type: SourceType, source_id: str, config: dict) -> SourceAdapter:
    """Instantiate the correct adapter for a given source type."""
    adapter_class = ADAPTER_REGISTRY.get(source_type)
    if adapter_class is None:
        raise ValueError(f"No adapter registered for source type: {source_type}")
    return adapter_class(source_id, config)


def register_adapter(source_type: SourceType, adapter_class: Type[SourceAdapter]) -> None:
    """Register a new adapter type at runtime."""
    ADAPTER_REGISTRY[source_type] = adapter_class
