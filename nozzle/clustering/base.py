"""Base class for clustering strategies."""

from abc import ABC, abstractmethod

from nozzle.domain.schemas import NormalizedAlert, ClusterCandidate


class ClusteringStrategy(ABC):
    """Abstract base for all clustering strategies."""

    @abstractmethod
    async def cluster(
        self, alerts: list[NormalizedAlert]
    ) -> list[ClusterCandidate]:
        """Group alerts into clusters."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of this strategy."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Strategy version."""
        ...
