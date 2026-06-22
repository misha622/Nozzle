"""Burst detection using Isolation Forest on alert frequency patterns."""

from datetime import datetime, timedelta
from uuid import uuid4
from collections import defaultdict
import numpy as np
from sklearn.ensemble import IsolationForest

from nozzle.clustering.base import ClusteringStrategy
from nozzle.domain.schemas import NormalizedAlert, ClusterCandidate


class TemporalBurstStrategy(ClusteringStrategy):
    """Detects anomalous bursts in alert frequency by rule and agent."""

    def __init__(
        self,
        window_minutes: int = 5,
        contamination: float = 0.1,
        min_alerts: int = 3,
    ):
        self.window_minutes = window_minutes
        self.contamination = contamination
        self.min_alerts = min_alerts

    @property
    def name(self) -> str:
        return "temporal_burst"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def cluster(self, alerts: list[NormalizedAlert]) -> list[ClusterCandidate]:
        """Detect burst patterns in alert stream."""
        if len(alerts) < self.min_alerts:
            return []

        # Build time-series features per (rule_id, agent_name)
        buckets = defaultdict(list)
        for a in alerts:
            key = (a.rule_id, a.agent_name or "unknown")
            buckets[key].append(a)

        clusters = []
        for (rule_id, agent_name), bucket in buckets.items():
            if len(bucket) < self.min_alerts:
                continue

            # Sort by time
            bucket.sort(key=lambda a: a.received_at)

            # Calculate inter-arrival times
            times = [a.received_at for a in bucket]
            deltas = []
            for i in range(1, len(times)):
                delta = (times[i] - times[i-1]).total_seconds()
                deltas.append(delta)

            if len(deltas) < 2:
                continue

            # Build feature matrix: [index, delta, rolling_avg, rolling_std]
            features = []
            window = max(3, len(deltas) // 4)
            for i in range(len(deltas)):
                start = max(0, i - window)
                window_deltas = deltas[start:i+1]
                mean_val = np.mean(window_deltas) if window_deltas else 0
                std_val = np.std(window_deltas) if len(window_deltas) > 1 else 0.01
                features.append([i, deltas[i], mean_val, std_val])

            features = np.array(features)

            # Normalize
            if features.shape[0] < 3:
                continue
            features = (features - features.mean(axis=0)) / (features.std(axis=0) + 1e-8)

            # Isolation Forest for anomaly detection
            iso = IsolationForest(
                contamination=self.contamination,
                random_state=42,
            )
            predictions = iso.fit_predict(features)

            # Find contiguous anomalous regions
            burst_regions = self._find_burst_regions(predictions, bucket)

            for region_alerts in burst_regions:
                if len(region_alerts) >= self.min_alerts:
                    rep = region_alerts[0]
                    cluster_id = uuid4()
                    clusters.append(ClusterCandidate(
                        id=cluster_id,
                        name=f"Burst: Rule {rule_id} on {agent_name}",
                        description=f"{len(region_alerts)} alerts in anomalous burst — {len(region_alerts)}x normal rate",
                        strategy=self.name,
                        confidence=0.85,
                        alert_ids=[a.id for a in region_alerts],
                        alert_count=len(region_alerts),
                        representative_alert_id=rep.id,
                    ))

        clusters.sort(key=lambda c: c.alert_count, reverse=True)
        return clusters

    def _find_burst_regions(self, predictions, bucket):
        """Find contiguous -1 (anomaly) regions in predictions."""
        # predictions[i] corresponds to the interval between bucket[i] and bucket[i+1]
        # We map anomalies back to the alerts that created them
        regions = []
        current_region = [bucket[0]]

        for i, pred in enumerate(predictions):
            if pred == -1:  # Anomaly
                current_region.append(bucket[i + 1])
            else:
                if len(current_region) >= self.min_alerts:
                    regions.append(current_region)
                current_region = [bucket[i + 1]]

        if len(current_region) >= self.min_alerts:
            regions.append(current_region)

        return regions
