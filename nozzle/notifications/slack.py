"""Slack notification sender for Nozzle."""

import httpx
import logging

from nozzle.settings import settings

logger = logging.getLogger(__name__)


async def send_slack_notification(webhook_url: str, message: str) -> bool:
    """Send a message to Slack via webhook."""
    if not webhook_url:
        logger.warning("No Slack webhook URL configured")
        return False

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                webhook_url,
                json={"text": message},
            )
            if response.status_code == 200:
                logger.info("Slack notification sent")
                return True
            else:
                logger.error(f"Slack notification failed: {response.status_code} {response.text}")
                return False
    except Exception as e:
        logger.error(f"Slack notification error: {e}")
        return False


async def notify_new_critical_cluster(cluster_name: str, alert_count: int, description: str) -> bool:
    """Send notification about a new critical cluster."""
    webhook_url = settings.slack_webhook_url
    if not webhook_url:
        return False

    message = (
        f"🚨 *Nozzle Alert*\n"
        f"*Cluster:* {cluster_name}\n"
        f"*Alerts:* {alert_count}\n"
        f"*Description:* {description}\n"
        f"*Time:* {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )
    return await send_slack_notification(webhook_url, message)
