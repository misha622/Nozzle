"""Normalizes raw alerts from various sources into a unified format."""

from datetime import datetime
from uuid import uuid4

from nozzle.domain.enums import SeverityLevel, SourceType, AlertStatus
from nozzle.domain.schemas import RawAlert, NormalizedAlert


class AlertNormalizer:
    """Converts RawAlert -> NormalizedAlert based on source type."""

    SEVERITY_MAP_WAZUH = {
        0: SeverityLevel.INFO,
        1: SeverityLevel.LOW,
        2: SeverityLevel.LOW,
        3: SeverityLevel.LOW,
        4: SeverityLevel.LOW,
        5: SeverityLevel.MEDIUM,
        6: SeverityLevel.MEDIUM,
        7: SeverityLevel.MEDIUM,
        8: SeverityLevel.HIGH,
        9: SeverityLevel.HIGH,
        10: SeverityLevel.HIGH,
        11: SeverityLevel.HIGH,
        12: SeverityLevel.CRITICAL,
        13: SeverityLevel.CRITICAL,
        14: SeverityLevel.CRITICAL,
        15: SeverityLevel.EMERGENCY,
    }

    SEVERITY_MAP_ELASTIC = {
        "info": SeverityLevel.INFO,
        "low": SeverityLevel.LOW,
        "medium": SeverityLevel.MEDIUM,
        "high": SeverityLevel.HIGH,
        "critical": SeverityLevel.CRITICAL,
    }

    async def normalize(self, raw: RawAlert) -> NormalizedAlert:
        """Normalize a single raw alert."""
        if raw.source_type == SourceType.WAZUH:
            return self._normalize_wazuh(raw)
        elif raw.source_type == SourceType.ELASTIC:
            return self._normalize_elastic(raw)
        else:
            return self._normalize_generic(raw)

    def _normalize_wazuh(self, raw: RawAlert) -> NormalizedAlert:
        payload = raw.raw_payload
        rule = payload.get("rule", {})
        agent = payload.get("agent", {})
        data = payload.get("data", {})

        severity_num = rule.get("level", 0)
        severity = self.SEVERITY_MAP_WAZUH.get(severity_num, SeverityLevel.INFO)

        src_ip = None
        if data.get("srcip"):
            src_ip = data["srcip"]
        elif agent.get("ip"):
            src_ip = agent["ip"]

        dst_ip = data.get("dstip", None)

        description = rule.get("description", "")
        full_log = payload.get("full_log", None)

        return NormalizedAlert(
            id=uuid4(),
            external_id=payload.get("id", str(uuid4())),
            source_type=SourceType.WAZUH,
            source_id=raw.source_id,
            rule_id=str(rule.get("id", "0")),
            rule_name=rule.get("description", "Unknown Rule"),
            severity=severity,
            agent_name=agent.get("name", None),
            agent_id=str(agent.get("id", "")) if agent.get("id") else None,
            source_ip=src_ip,
            source_hostname=agent.get("name", None),
            destination_ip=dst_ip,
            description=description,
            full_log=full_log,
            raw_json=payload,
            status=AlertStatus.NEW,
            received_at=raw.received_at,
            normalized_at=datetime.utcnow(),
        )

    def _normalize_elastic(self, raw: RawAlert) -> NormalizedAlert:
        payload = raw.raw_payload
        signal = payload.get("signal", payload.get("kibana.alert", {}))
        rule = signal.get("rule", {})
        agent = signal.get("agent", {})

        severity_str = signal.get("severity", "medium").lower()
        severity = self.SEVERITY_MAP_ELASTIC.get(severity_str, SeverityLevel.MEDIUM)

        return NormalizedAlert(
            id=uuid4(),
            external_id=signal.get("id", str(uuid4())),
            source_type=SourceType.ELASTIC,
            source_id=raw.source_id,
            rule_id=str(rule.get("id", "0")),
            rule_name=rule.get("name", "Unknown Rule"),
            severity=severity,
            agent_name=agent.get("name", None),
            agent_id=str(agent.get("id", "")) if agent.get("id") else None,
            source_ip=signal.get("source", {}).get("ip", None),
            destination_ip=signal.get("destination", {}).get("ip", None),
            description=rule.get("description", ""),
            full_log=None,
            raw_json=payload,
            status=AlertStatus.NEW,
            received_at=raw.received_at,
            normalized_at=datetime.utcnow(),
        )

    def _normalize_generic(self, raw: RawAlert) -> NormalizedAlert:
        payload = raw.raw_payload
        return NormalizedAlert(
            id=uuid4(),
            external_id=payload.get("id", payload.get("_id", str(uuid4()))),
            source_type=raw.source_type,
            source_id=raw.source_id,
            rule_id=payload.get("rule_id", payload.get("rule", {}).get("id", "0")),
            rule_name=payload.get("rule_name", payload.get("rule", {}).get("name", "Unknown")),
            severity=SeverityLevel.INFO,
            agent_name=payload.get("agent_name", payload.get("host", {}).get("name", None)),
            agent_id=payload.get("agent_id", None),
            source_ip=payload.get("source_ip", payload.get("source", {}).get("ip", None)),
            destination_ip=payload.get("destination_ip", payload.get("destination", {}).get("ip", None)),
            description=payload.get("description", payload.get("message", "")),
            full_log=None,
            raw_json=payload,
            status=AlertStatus.NEW,
            received_at=raw.received_at,
            normalized_at=datetime.utcnow(),
        )
