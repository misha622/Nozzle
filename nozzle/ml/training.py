"""LightGBM classifier training on analyst feedback."""

import logging
import numpy as np
from lightgbm import LGBMClassifier
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from nozzle.domain.models import Feedback, Alert, RuleStats
from nozzle.domain.enums import Decision

logger = logging.getLogger(__name__)


class NoiseClassifier:
    """Predicts whether an alert is noise based on historical feedback."""

    def __init__(self):
        import os
        self._trained = False
        model_path = "models/noise_classifier.pkl"
        if os.path.exists(model_path):
            try:
                import joblib
                self.model = joblib.load(model_path)
                self._trained = True
                logging.getLogger(__name__).info("Loaded pre-trained model from disk")
                return
            except Exception:
                pass

        self.model = LGBMClassifier(
            n_estimators=100, max_depth=5, num_leaves=15,
            min_child_samples=10, random_state=42,
        )
        self._trained = False

    async def train(self, db: AsyncSession) -> bool:
        """Train the model on feedback-labeled alerts."""
        result = await db.execute(
            select(Feedback).where(
                Feedback.decision.in_([Decision.CONFIRMED_NOISE, Decision.CONFIRMED_INCIDENT])
            ).limit(500)
        )
        feedbacks = result.scalars().all()

        if len(feedbacks) < 5:
            logger.info(f"Not enough feedback: {len(feedbacks)} samples")
            return False

        X, y = [], []
        for fb in feedbacks:
            if not fb.cluster_id:
                continue
            alerts_result = await db.execute(
                select(Alert).where(Alert.cluster_id == fb.cluster_id)
            )
            for alert in alerts_result.scalars().all():
                stats_result = await db.execute(
                    select(RuleStats).where(
                        RuleStats.source_id == alert.source_id,
                        RuleStats.external_rule_id == alert.rule_id,
                    )
                )
                stats = stats_result.scalar_one_or_none()
                X.append(self._extract_features(alert, stats))
                y.append(1 if fb.decision == Decision.CONFIRMED_NOISE else 0)

        if len(set(y)) < 2:
            logger.info("Need both noise and incident labels")
            return False

        X, y = np.array(X), np.array(y)
        self.model.fit(X, y)
        self._trained = True
        import joblib, os
        os.makedirs("models", exist_ok=True)
        joblib.dump(self.model, "models/noise_classifier.pkl")
        logger.info(f"Trained classifier on {len(X)} samples, saved to models/noise_classifier.pkl")
        return True

    def predict_noise_probability(self, alert, rule_stats=None) -> float:
        """Predict probability that an alert is noise."""
        if not self._trained:
            return 0.5
        features = self._extract_features(alert, rule_stats)
        proba = self.model.predict_proba([features])[0]
        return float(proba[1]) if len(proba) > 1 else 0.5

    def _extract_features(self, alert, rule_stats=None) -> list:
        return [
            alert.severity or 0,
            alert.severity / 15.0,
            1 if alert.agent_name else 0,
            1 if alert.source_ip else 0,
            len(alert.description) if alert.description else 0,
            len(alert.full_log) if alert.full_log else 0,
            rule_stats.noise_score if rule_stats else 0.5,
            rule_stats.times_clustered if rule_stats else 0,
            rule_stats.times_escalated if rule_stats else 0,
        ]


classifier = NoiseClassifier()
