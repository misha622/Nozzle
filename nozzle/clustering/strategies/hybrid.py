"""Hybrid clustering: semantic embeddings first, rule-based fallback for leftovers."""

from uuid import uuid4

from nozzle.clustering.base import ClusteringStrategy
from nozzle.domain.schemas import NormalizedAlert, ClusterCandidate
from nozzle.clustering.strategies.semantic import SemanticStrategy
from nozzle.clustering.strategies.rule_based import RuleBasedStrategy


class HybridStrategy(ClusteringStrategy):
    """Semantic clustering with rule-based fallback for unclustered alerts."""

    def __init__(
        self,
        similarity_threshold: float = 0.75,
        min_alerts: int = 2,
        window_minutes: int = 30,
    ):
        self.semantic = SemanticStrategy(
            similarity_threshold=similarity_threshold,
            min_alerts=min_alerts,
        )
        self.rule_based = RuleBasedStrategy(
            window_minutes=window_minutes,
            min_alerts=min_alerts,
        )

    @property
    def name(self) -> str:
        return "hybrid"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def cluster(self, alerts: list[NormalizedAlert]) -> list[ClusterCandidate]:
        """Semantic first, then rule-based on what remains."""
        if len(alerts) < 2:
            return []

        # Step 1: Semantic clustering
        semantic_clusters = await self.semantic.cluster(alerts)

        # Collect IDs of already clustered alerts
        clustered_ids = set()
        for c in semantic_clusters:
            for aid in c.alert_ids:
                clustered_ids.add(aid)

        # Find unclustered alerts
        leftovers = [a for a in alerts if a.id not in clustered_ids]

        # Step 2: Rule-based fallback with wider window
        if len(leftovers) >= self.rule_based.min_alerts:
            rule_clusters = await self.rule_based.cluster(leftovers)
        else:
            rule_clusters = []

        # Merge all clusters
        all_clusters = semantic_clusters + rule_clusters
        all_clusters.sort(key=lambda c: c.alert_count, reverse=True)

        return all_clusters
