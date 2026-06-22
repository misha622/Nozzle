"""Rule-based clustering: groups alerts by rule_id + agent_name within a time window."""

from datetime import datetime, timedelta
from collections import defaultdict
from uuid import uuid4

from nozzle.clustering.base import ClusteringStrategy
from nozzle.domain.schemas import NormalizedAlert, ClusterCandidate


class RuleBasedStrategy(ClusteringStrategy):
    """Groups alerts that share the same rule_id and agent_name within a time window."""

    def __init__(self, window_minutes: int = 5, min_alerts: int = 3):
        self.window_minutes = window_minutes
        self.min_alerts = min_alerts

    @property
    def name(self) -> str:
        return "rule_based"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def cluster(
        self, alerts: list[NormalizedAlert]
    ) -> list[ClusterCandidate]:
        """Group alerts into clusters based on rule_id + agent_name + time proximity."""
        if not alerts:
            return []

        # Sort by received_at
        sorted_alerts = sorted(alerts, key=lambda a: a.received_at)

        # Group by (rule_id, agent_name)
        buckets: dict[tuple[str, str], list[NormalizedAlert]] = defaultdict(list)
        for alert in sorted_alerts:
            key = (alert.rule_id, alert.agent_name or "unknown")
            buckets[key].append(alert)

        clusters: list[ClusterCandidate] = []

        for (rule_id, agent_name), bucket_alerts in buckets.items():
            # Split bucket into time-based sub-groups
            sub_groups = self._split_by_time(bucket_alerts)

            for sub_group in sub_groups:
                if len(sub_group) < self.min_alerts:
                    continue

                representative = sub_group[0]
                cluster_id = uuid4()

                clusters.append(
                    ClusterCandidate(
                        id=cluster_id,
                        name=f"Rule {rule_id} on {agent_name}",
                        description=(
                            f"{len(sub_group)} alerts from rule {rule_id} "
                            f"on agent {agent_name} "
                            f"between {sub_group[0].received_at} and {sub_group[-1].received_at}"
                        ),
                        strategy=self.name,
                        confidence=0.95,
                        alert_ids=[a.id for a in sub_group],
                        alert_count=len(sub_group),
                        representative_alert_id=representative.id,
                    )
                )

        # Sort by alert_count descending (biggest clusters first)
        clusters.sort(key=lambda c: c.alert_count, reverse=True)
        return clusters

    def _split_by_time(
        self, alerts: list[NormalizedAlert]
    ) -> list[list[NormalizedAlert]]:
        """Split a list of time-sorted alerts into groups within the time window."""
        if not alerts:
            return []

        groups: list[list[NormalizedAlert]] = []
        current_group: list[NormalizedAlert] = [alerts[0]]
        window = timedelta(minutes=self.window_minutes)

        for alert in alerts[1:]:
            time_diff = alert.received_at - current_group[0].received_at
            if time_diff <= window:
                current_group.append(alert)
            else:
                groups.append(current_group)
                current_group = [alert]

        groups.append(current_group)
        return groups
