"""Periodic report generation."""

import logging
from datetime import datetime, timedelta
from nozzle.db.session import async_session_factory
from nozzle.db.queries import stats as stats_queries

logger = logging.getLogger(__name__)


async def generate_weekly_report(ctx):
    """Generate and log weekly noise report."""
    async with async_session_factory() as db:
        try:
            total = await stats_queries.get_total_alerts_24h(db)
            noise_pct = await stats_queries.get_noise_reduction_pct(db)
            top_noisy = await stats_queries.get_top_noisy_rules(db, limit=5)

            logger.info(f"Weekly Report: {total} alerts, {noise_pct}% noise reduction")
            for rule in top_noisy:
                logger.info(f"  Rule {rule['rule_id']}: noise={rule['noise_score']}, clustered={rule['times_clustered']}")
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
