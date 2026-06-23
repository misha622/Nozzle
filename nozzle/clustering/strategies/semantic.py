"""Semantic clustering using sentence transformer embeddings."""

from uuid import uuid4
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from nozzle.clustering.base import ClusteringStrategy
from nozzle.domain.schemas import NormalizedAlert, ClusterCandidate


class SemanticStrategy(ClusteringStrategy):
    """Groups alerts by semantic similarity using transformer embeddings."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.75,
        min_alerts: int = 2,
        use_rule_id: bool = True,
    ):
        self.similarity_threshold = similarity_threshold
        self.min_alerts = min_alerts
        self.use_rule_id = use_rule_id
        self._model = None

    @property
    def name(self) -> str:
        return "semantic"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _get_model(self):
        """Lazy-load the transformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    async def cluster(self, alerts: list[NormalizedAlert]) -> list[ClusterCandidate]:
        """Group alerts by semantic similarity."""
        if len(alerts) < 2:
            return []

        # Build descriptions
        descriptions = []
        for a in alerts:
            desc = (a.description or "") + " " + (a.full_log or "")
            descriptions.append(desc.strip() or a.rule_name or "unknown")

        # Generate embeddings
        model = self._get_model()
        embeddings = model.encode(descriptions, show_progress_bar=False)

        # Cosine similarity matrix
        sim_matrix = cosine_similarity(embeddings)

        # Find groups via transitive closure
        groups = self._find_groups(sim_matrix, len(alerts), alerts)

        return self._build_clusters(alerts, groups)

    def _find_groups(self, sim_matrix, n, alerts):
        """BFS for transitive similarity groups."""
        visited = set()
        groups = []

        for i in range(n):
            if i in visited:
                continue

            group = []
            stack = [i]

            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                group.append(current)

                for j in range(n):
                    if j not in visited:
                        # Rule-based pre-filter
                        if self.use_rule_id and alerts[current].rule_id != alerts[j].rule_id:
                            continue
                        if sim_matrix[current, j] >= self.similarity_threshold:
                            stack.append(j)

            if len(group) >= self.min_alerts:
                groups.append(group)

        return groups

    def _build_clusters(self, alerts, groups):
        """Build ClusterCandidate objects."""
        clusters = []
        for group_indices in groups:
            group_alerts = [alerts[i] for i in group_indices]
            rep = group_alerts[0]
            rule_ids = list(set(a.rule_id for a in group_alerts))
            agents = list(set(a.agent_name for a in group_alerts if a.agent_name))
            cluster_id = uuid4()

            clusters.append(ClusterCandidate(
                id=cluster_id,
                name=f"Semantic: Rule {','.join(rule_ids[:2])} on {agents[0] if agents else 'unknown'}",
                description=f"{len(group_alerts)} semantically similar alerts — transformer embedding clustering",
                strategy=self.name,
                confidence=min(0.95, 0.70 + len(group_alerts) / 50),
                alert_ids=[a.id for a in group_alerts],
                alert_count=len(group_alerts),
                representative_alert_id=rep.id,
            ))

        clusters.sort(key=lambda c: c.alert_count, reverse=True)
        return clusters
