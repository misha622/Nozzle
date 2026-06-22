"""Unit tests for AlertNormalizer."""

import pytest
from datetime import datetime
from uuid import uuid4

from nozzle.domain.enums import SourceType, SeverityLevel, AlertStatus
from nozzle.domain.schemas import RawAlert, NormalizedAlert
from nozzle.ingestion.normalizer import AlertNormalizer


class TestAlertNormalizer:
    """Tests for alert normalization."""

    @pytest.mark.asyncio
    async def test_normalize_wazuh_alert(self):
        """Wazuh alert is correctly normalized."""
        normalizer = AlertNormalizer()
        raw = RawAlert(
            external_id="test-123",
            source_type=SourceType.WAZUH,
            source_id=uuid4(),
            raw_payload={
                "id": "test-123",
                "rule": {"id": "5716", "description": "SSHD authentication failed", "level": 5},
                "agent": {"id": "007", "name": "db-server-01", "ip": "10.0.0.1"},
                "data": {"srcip": "10.0.0.100", "dstip": "192.168.1.1"},
                "full_log": "Failed password for root from 10.0.0.100 port 22 ssh2",
            },
            received_at=datetime.utcnow(),
        )

        result = await normalizer.normalize(raw)

        assert result.external_id == "test-123"
        assert result.source_type == SourceType.WAZUH
        assert result.rule_id == "5716"
        assert result.rule_name == "SSHD authentication failed"
        assert result.severity == 5  # SeverityLevel.MEDIUM value
        assert result.agent_name == "db-server-01"
        assert result.agent_id == "007"
        assert str(result.source_ip) == "10.0.0.100"
        assert result.source_hostname == "db-server-01"
        assert str(result.destination_ip) == "192.168.1.1"
        assert result.description == "SSHD authentication failed"
        assert result.full_log == "Failed password for root from 10.0.0.100 port 22 ssh2"
        assert result.status == AlertStatus.NEW

    @pytest.mark.asyncio
    async def test_normalize_wazuh_uses_agent_ip_when_data_srcip_missing(self):
        """Falls back to agent.ip when data.srcip is missing."""
        normalizer = AlertNormalizer()
        raw = RawAlert(
            external_id="test-456",
            source_type=SourceType.WAZUH,
            source_id=uuid4(),
            raw_payload={
                "id": "test-456",
                "rule": {"id": "5501", "description": "Login session opened", "level": 3},
                "agent": {"id": "001", "name": "web-01", "ip": "192.168.1.100"},
                "data": {},
            },
            received_at=datetime.utcnow(),
        )

        result = await normalizer.normalize(raw)
        assert str(result.source_ip) == "192.168.1.100"
        assert result.severity == 3

    @pytest.mark.asyncio
    async def test_normalize_wazuh_minimal_alert(self):
        """Minimal Wazuh alert with missing fields."""
        normalizer = AlertNormalizer()
        raw = RawAlert(
            external_id="test-min",
            source_type=SourceType.WAZUH,
            source_id=uuid4(),
            raw_payload={
                "id": "test-min",
                "rule": {"id": "1002", "level": 0},
            },
            received_at=datetime.utcnow(),
        )

        result = await normalizer.normalize(raw)
        assert result.rule_id == "1002"
        assert result.severity == 0
        assert result.agent_name is None
        assert result.source_ip is None

    @pytest.mark.asyncio
    async def test_normalize_elastic_alert(self):
        """Elastic alert is correctly normalized."""
        normalizer = AlertNormalizer()
        raw = RawAlert(
            external_id="elastic-123",
            source_type=SourceType.ELASTIC,
            source_id=uuid4(),
            raw_payload={
                "signal": {
                    "id": "elastic-123",
                    "rule": {"id": "rule-1", "name": "SSH Brute Force", "description": "Multiple SSH failures"},
                    "agent": {"id": "agent-1", "name": "server-01"},
                    "severity": "high",
                    "source": {"ip": "10.0.0.55"},
                    "destination": {"ip": "192.168.1.10"},
                }
            },
            received_at=datetime.utcnow(),
        )

        result = await normalizer.normalize(raw)
        assert result.external_id == "elastic-123"
        assert result.source_type == SourceType.ELASTIC
        assert result.rule_id == "rule-1"
        assert result.rule_name == "SSH Brute Force"
        assert result.severity == 8  # SeverityLevel.HIGH
        assert str(result.source_ip) == "10.0.0.55"
        assert str(result.destination_ip) == "192.168.1.10"

    @pytest.mark.asyncio
    async def test_normalize_generic_alert(self):
        """Generic/webhook alert uses fallback logic."""
        normalizer = AlertNormalizer()
        raw = RawAlert(
            external_id="generic-1",
            source_type=SourceType.WEBHOOK,
            source_id=uuid4(),
            raw_payload={
                "_id": "generic-1",
                "rule_id": "custom-rule",
                "rule_name": "Custom Detection",
                "description": "Something happened",
                "host": {"name": "custom-host"},
                "source": {"ip": "172.16.0.1"},
            },
            received_at=datetime.utcnow(),
        )

        result = await normalizer.normalize(raw)
        assert result.source_type == SourceType.WEBHOOK
        assert result.rule_id == "custom-rule"
        assert result.rule_name == "Custom Detection"
        assert result.agent_name == "custom-host"
        assert str(result.source_ip) == "172.16.0.1"
        assert result.description == "Something happened"
