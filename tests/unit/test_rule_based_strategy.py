"""Unit tests for RuleBasedStrategy."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from nozzle.clustering.strategies.rule_based import RuleBasedStrategy
from nozzle.domain.schemas import NormalizedAlert


def make_alert(rule_id: str, agent_name: str, minutes_ago: int = 0) -> NormalizedAlert:
    """Helper to create a test alert."""
    return NormalizedAlert(
        id=uuid4(),
        external_id=str(uuid4()),
        source_type="wazuh",
        source_id=uuid4(),
        rule_id=rule_id,
        rule_name=f"Rule {rule_id}",
        severity=5,
        agent_name=agent_name,
        description=f"Test alert from rule {rule_id}",
        raw_json={},
        received_at=datetime.utcnow() - timedelta(minutes=minutes_ago),
        normalized_at=datetime.utcnow(),
    )


class TestRuleBasedStrategy:
    """Tests for rule-based clustering strategy."""

    @pytest.mark.asyncio
    async def test_empty_alerts(self):
        """Empty list returns no clusters."""
        strategy = RuleBasedStrategy()
        result = await strategy.cluster([])
        assert result == []

    @pytest.mark.asyncio
    async def test_single_alert_below_min(self):
        """Single alert below min_alerts threshold — no cluster."""
        strategy = RuleBasedStrategy(min_alerts=3)
        alerts = [make_alert("1002", "server-01", 0)]
        result = await strategy.cluster(alerts)
        assert result == []

    @pytest.mark.asyncio
    async def test_three_alerts_same_rule_agent(self):
        """Three alerts from same rule and agent within window → one cluster."""
        strategy = RuleBasedStrategy(window_minutes=5, min_alerts=3)
        alerts = [
            make_alert("5716", "db-01", 0),
            make_alert("5716", "db-01", 1),
            make_alert("5716", "db-01", 2),
        ]
        result = await strategy.cluster(alerts)
        assert len(result) == 1
        assert result[0].alert_count == 3
        assert result[0].confidence == 0.95
        assert result[0].strategy == "rule_based"
        assert "5716" in result[0].name
        assert "db-01" in result[0].name

    @pytest.mark.asyncio
    async def test_different_rules_no_cluster(self):
        """Alerts with different rule_ids stay separate."""
        strategy = RuleBasedStrategy(min_alerts=2)
        alerts = [
            make_alert("5716", "db-01", 0),
            make_alert("5716", "db-01", 1),
            make_alert("5501", "db-01", 2),
            make_alert("5501", "db-01", 3),
        ]
        result = await strategy.cluster(alerts)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_different_agents_no_cluster(self):
        """Alerts with different agents stay separate."""
        strategy = RuleBasedStrategy(min_alerts=2)
        alerts = [
            make_alert("5716", "db-01", 0),
            make_alert("5716", "db-01", 1),
            make_alert("5716", "web-01", 2),
            make_alert("5716", "web-01", 3),
        ]
        result = await strategy.cluster(alerts)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_time_window_split(self):
        """Alerts outside time window form separate clusters."""
        strategy = RuleBasedStrategy(window_minutes=5, min_alerts=2)
        alerts = [
            make_alert("5716", "db-01", 0),
            make_alert("5716", "db-01", 1),
            make_alert("5716", "db-01", 20),  # Outside window
            make_alert("5716", "db-01", 21),
        ]
        result = await strategy.cluster(alerts)
        assert len(result) == 2  # Two separate clusters

    @pytest.mark.asyncio
    async def test_biggest_cluster_first(self):
        """Largest cluster appears first."""
        strategy = RuleBasedStrategy(min_alerts=2)
        alerts = [
            make_alert("5501", "web-01", 0),
            make_alert("5501", "web-01", 1),
            make_alert("5716", "db-01", 0),
            make_alert("5716", "db-01", 1),
            make_alert("5716", "db-01", 2),
        ]
        result = await strategy.cluster(alerts)
        assert len(result) == 2
        assert result[0].alert_count == 3  # Biggest first
        assert result[1].alert_count == 2

    @pytest.mark.asyncio
    async def test_none_agent_name(self):
        """Alerts with None agent_name use 'unknown'."""
        strategy = RuleBasedStrategy(min_alerts=2)
        alerts = [
            make_alert("1002", "unknown", 0),
            make_alert("1002", "unknown", 1),
        ]
        # Override agent_name to None
        for a in alerts:
            a.agent_name = None
        result = await strategy.cluster(alerts)
        assert len(result) == 1
        assert "unknown" in result[0].name

    @pytest.mark.asyncio
    async def test_representative_alert_id_set(self):
        """Cluster has a representative alert ID."""
        strategy = RuleBasedStrategy(min_alerts=2)
        alerts = [
            make_alert("5716", "db-01", 0),
            make_alert("5716", "db-01", 1),
        ]
        result = await strategy.cluster(alerts)
        assert result[0].representative_alert_id is not None
