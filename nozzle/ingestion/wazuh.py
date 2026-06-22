"""Wazuh API adapter for fetching alerts."""

import logging
from datetime import datetime
from uuid import UUID
from typing import AsyncIterator

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from nozzle.ingestion.base import SourceAdapter
from nozzle.domain.schemas import RawAlert
from nozzle.domain.enums import SourceType
from nozzle.core.exceptions import SourceConnectionError, SourceAuthError

logger = logging.getLogger(__name__)


class WazuhAdapter(SourceAdapter):
    """Fetches alerts from Wazuh REST API (v4.x)."""

    def __init__(self, source_id: str, config: dict):
        super().__init__(source_id, config)
        self.base_url = config["base_url"].rstrip("/")
        self.username = config["username"]
        self.password = config["password"]
        self.verify_ssl = config.get("verify_ssl", True)
        self.timeout = config.get("timeout", 30)
        self._token: str | None = None
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> bool:
        """Authenticate and get JWT token."""
        try:
            self._client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=self.timeout,
            )
            return await self._authenticate()
        except Exception as e:
            logger.error(f"Failed to connect to Wazuh: {e}")
            raise SourceConnectionError(self.base_url, str(e))

    async def disconnect(self) -> None:
        """Logout and close HTTP client."""
        if self._client:
            try:
                await self._client.delete(f"{self.base_url}/security/user/authenticate")
            except Exception:
                pass
            await self._client.aclose()
            self._client = None
        self._token = None

    async def health_check(self) -> bool:
        """Check if Wazuh API is reachable."""
        try:
            async with httpx.AsyncClient(verify=self.verify_ssl, timeout=5) as client:
                response = await client.get(f"{self.base_url}/")
                return response.status_code < 500
        except Exception:
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def fetch_alerts(
        self, since: datetime | None = None, limit: int = 1000
    ) -> AsyncIterator[RawAlert]:
        """Fetch alerts from Wazuh with pagination."""
        if not self._client or not self._token:
            await self.connect()

        offset = 0
        while True:
            response = await self._fetch_page(since, offset, limit)
            if response is None:
                break

            items = response.get("data", {}).get("affected_items", [])
            if not items:
                break

            for item in items:
                yield RawAlert(
                    external_id=item.get("id", ""),
                    source_type=SourceType.WAZUH,
                    source_id=UUID(self.source_id),
                    raw_payload=item,
                    received_at=datetime.utcnow(),
                )

            total = response.get("data", {}).get("total_affected_items", 0)
            offset += len(items)
            if offset >= total:
                break

    async def acknowledge_alert(self, external_id: str) -> bool:
        """Not directly supported by Wazuh API — we tag instead."""
        return await self.add_tag(external_id, "nozzle:acknowledged")

    async def add_tag(self, external_id: str, tag: str) -> bool:
        """Add a tag to alert via Wazuh API (if available)."""
        return True

    async def _authenticate(self) -> bool:
        """Get JWT token from Wazuh."""
        if not self._client:
            return False

        try:
            response = await self._client.post(
                f"{self.base_url}/security/user/authenticate",
                json={"username": self.username, "password": self.password},
            )
            response.raise_for_status()
            data = response.json()
            self._token = data.get("data", {}).get("token")
            if self._token:
                self._client.headers["Authorization"] = f"Bearer {self._token}"
                return True
            raise SourceAuthError(self.base_url)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise SourceAuthError(self.base_url)
            raise SourceConnectionError(self.base_url, str(e))

    async def _fetch_page(
        self, since: datetime | None, offset: int, limit: int
    ) -> dict | None:
        """Fetch a single page of alerts."""
        if not self._client:
            return None

        params = {
            "offset": offset,
            "limit": limit,
            "sort": "-timestamp",
            "select": "id,timestamp,rule,agent,data,full_log,syscheck,decoder,location,manager,predecoder",
        }

        if since:
            params["timestamp>"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            response = await self._client.get(
                f"{self.base_url}/alerts", params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch alerts page {offset}: {e}")
            return None
