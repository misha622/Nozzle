# Fix 1: Remove empty strategy files
import os
for f in [
    r"nozzle\clustering\strategies\behavioral.py",
    r"nozzle\clustering\strategies\field_similarity.py",
    r"nozzle\clustering\resolvers\conflict_resolver.py",
    r"nozzle\clustering\resolvers\__init__.py",
    r"nozzle\clustering\strategies\temporal_burst.py.bak",
]:
    if os.path.exists(f) and os.path.getsize(f) == 0:
        os.remove(f)
        print(f"Removed empty: {f}")

# Fix 2: CORS fix
path = r"nozzle\main.py"
with open(path, "r", encoding="utf-8") as fp:
    c = fp.read()
c = c.replace(
    'allow_origins=["*"],\n        allow_credentials=True,',
    'allow_origins=["*"],\n        allow_credentials=False,'
)
with open(path, "w", encoding="utf-8") as fp:
    fp.write(c)
print("CORS fixed")

# Fix 3: N+1 queries in _update_rule_stats
path = r"nozzle\clustering\manager.py"
with open(path, "r", encoding="utf-8") as fp:
    c = fp.read()

old_method = '''    async def _update_rule_stats(self, candidates):
        """Update RuleStats after clustering."""
        rule_counts = {}
        for candidate in candidates:
            for alert_id in candidate.alert_ids:
                result = await self.db.execute(
                    select(Alert).where(Alert.id == str(alert_id))
                )
                alert = result.scalar_one_or_none()
                if alert:
                    key = (alert.source_id, alert.rule_id)
                    rule_counts[key] = rule_counts.get(key, 0) + 1'''

new_method = '''    async def _update_rule_stats(self, candidates):
        """Update RuleStats after clustering."""
        all_ids = [str(aid) for cand in candidates for aid in cand.alert_ids]
        if not all_ids:
            return

        # Single query: fetch all alerts in one go
        result = await self.db.execute(
            select(Alert).where(Alert.id.in_(all_ids))
        )
        alert_map = {a.id: a for a in result.scalars().all()}

        rule_counts = {}
        for candidate in candidates:
            for alert_id in candidate.alert_ids:
                alert = alert_map.get(str(alert_id))
                if alert:
                    key = (alert.source_id, alert.rule_id)
                    rule_counts[key] = rule_counts.get(key, 0) + 1'''

c = c.replace(old_method, new_method)
with open(path, "w", encoding="utf-8") as fp:
    fp.write(c)
print("N+1 queries fixed")

# Fix 4: Scheduler tasks placeholders
for f, content in [
    (r"nozzle\scheduler\tasks\training.py", '''"""Periodic model retraining task."""

import logging
from nozzle.db.session import async_session_factory
from nozzle.ml.training import classifier

logger = logging.getLogger(__name__)


async def retrain_model(ctx):
    """Retrain noise classifier on accumulated feedback."""
    async with async_session_factory() as db:
        try:
            success = await classifier.train(db)
            if success:
                logger.info("Model retrained successfully")
            else:
                logger.info("Not enough feedback data for retraining")
        except Exception as e:
            logger.error(f"Model retraining failed: {e}")
'''),
    (r"nozzle\scheduler\tasks\reports.py", '''"""Periodic report generation."""

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
'''),
]:
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w", encoding="utf-8") as fp:
        fp.write(content)
    print(f"Created: {f}")

print("\nAll fixes applied.")
