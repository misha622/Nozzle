"""Periodic model retraining task."""

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
