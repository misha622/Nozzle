"""ML-based clustering using TF-IDF + cosine similarity."""

from collections import defaultdict
from uuid import uuid4

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from nozzle.clustering.base import ClusteringStrategy
from nozzle.domain.schemas import NormalizedAlert, ClusterCandidate
from nozzle.ml.feature_engineering import AlertFeatureExtractor


class MLBasedStrategy(ClusteringStrategy):
    """Groups alerts by text similarity using TF-IDF + cosine similarity."""

    def __init__(
        self,
        similarity_threshold: float = 0.6,
        min_alerts: int = 2,
        max_features: int = 500,
        use_rule_id: bool = True,
    ):
        self.similarity_threshold = similarity_threshold
        self.min_alerts = min_alerts
        self.max_features = max_features
        self.use_rule_id = use_rule_id
        self.extractor = AlertFeatureExtractor(max_features=max_features)

    @property
    def name(self) -> str:
        return "ml_based"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def cluster(
        self, alerts: list[NormalizedAlert]
    ) -> list[ClusterCandidate]:
        """Group alerts by text similarity."""
        if len(alerts) < 2:
            return []

        # Clean and prepare descriptions
        descriptions = [
            self.extractor.clean_description(
                (a.description or "") + " " + (a.full_log or "")
            )
            for a in alerts
        ]

        # Try TF-IDF, fall back to rule-based pre-grouping if too few alerts
        if len(alerts) >= 10 and len(set(descriptions)) >= 3:
            return await self._tfidf_cluster(alerts, descriptions)
        else:
            return await self._simple_similarity_cluster(alerts, descriptions)

    async def _tfidf_cluster(
        self, alerts: list[NormalizedAlert], descriptions: list[str]
    ) -> list[ClusterCandidate]:
        """Cluster using TF-IDF + cosine similarity."""
        try:
            tfidf_matrix = self.extractor.fit_transform(descriptions)
        except ValueError:
            return []

        similarity_matrix = cosine_similarity(tfidf_matrix)

        # Group by transitive similarity
        groups = self._find_similarity_groups(similarity_matrix, len(alerts))

        return self._build_clusters(alerts, groups)

    async def _simple_similarity_cluster(
        self, alerts: list[NormalizedAlert], descriptions: list[str]
    ) -> list[ClusterCandidate]:
        """Fallback: simple Jaccard-like similarity on words."""
        groups = []
        assigned = set()

        for i in range(len(alerts)):
            if i in assigned:
                continue

            group = [i]
            words_i = set(descriptions[i].split())

            for j in range(i + 1, len(alerts)):
                if j in assigned:
                    continue

                # Rule-based pre-filter
                if self.use_rule_id and alerts[i].rule_id != alerts[j].rule_id:
                    continue

                words_j = set(descriptions[j].split())
                if not words_i or not words_j:
                    continue

                intersection = words_i & words_j
                union = words_i | words_j
                similarity = len(intersection) / len(union) if union else 0

                if similarity >= self.similarity_threshold:
                    group.append(j)
                    assigned.add(j)

            if len(group) >= self.min_alerts:
                groups.append(group)
                assigned.add(i)

        return self._build_clusters(alerts, groups)

    def _find_similarity_groups(
        self, similarity_matrix: np.ndarray, n: int
    ) -> list[list[int]]:
        """Find transitive groups above similarity threshold."""
        visited = set()
        groups = []

        for i in range(n):
            if i in visited:
                continue

            # BFS for transitive closure
            group = []
            stack = [i]

            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                group.append(current)

                for j in range(n):
                    if j not in visited and similarity_matrix[current, j] >= self.similarity_threshold:
                        stack.append(j)

            if len(group) >= self.min_alerts:
                groups.append(group)

        return groups

    def _build_clusters(
        self,
        alerts: list[NormalizedAlert],
        groups: list[list[int]],
    ) -> list[ClusterCandidate]:
        """Build ClusterCandidate objects from groups."""
        clusters = []

        for group_indices in groups:
            group_alerts = [alerts[i] for i in group_indices]
            representative = group_alerts[0]

            # Calculate confidence based on average intra-group similarity
            confidence = min(0.95, 0.70 + (len(group_alerts) / 50))

            # Build a descriptive name
            rule_ids = list(set(a.rule_id for a in group_alerts))
            rule_name = f"Rule {','.join(rule_ids[:2])}" if rule_ids else "Unknown"
            agents = list(set(a.agent_name for a in group_alerts if a.agent_name))
            agent_name = agents[0] if agents else "unknown"

            cluster_id = uuid4()
            clusters.append(
                ClusterCandidate(
                    id=cluster_id,
                    name=f"{rule_name} on {agent_name}",
                    description=(
                        f"{len(group_alerts)} similar alerts from {len(rule_ids)} rule(s) "
                        f"on {agent_name} — ML-detected pattern"
                    ),
                    strategy=self.name,
                    confidence=confidence,
                    alert_ids=[a.id for a in group_alerts],
                    alert_count=len(group_alerts),
                    representative_alert_id=representative.id,
                )
            )

        clusters.sort(key=lambda c: c.alert_count, reverse=True)
        return clusters
