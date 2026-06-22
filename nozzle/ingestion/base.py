"""Base classes for alert source adapters."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncIterator

from nozzle.domain.schemas import RawAlert


class SourceAdapter(ABC):
    """Abstract base for all alert source adapters (Wazuh, Elastic, etc.)."""

    def __init__(self, source_id: str, config: dict):
        self.source_id = source_id
        self.config = config

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the source. Returns True on success."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection gracefully."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if source is reachable and responding."""
        ...

    @abstractmethod
    async def fetch_alerts(
        self, since: datetime | None = None, limit: int = 1000
    ) -> AsyncIterator[RawAlert]:
        """Fetch alerts from the source, yielding raw alerts."""
        ...

    @abstractmethod
    async def acknowledge_alert(self, external_id: str) -> bool:
        """Mark alert as acknowledged in the source system."""
        ...

    @abstractmethod
    async def add_tag(self, external_id: str, tag: str) -> bool:
        """Add a tag to an alert in the source system."""
        ...
