"""Registry for clustering strategies."""

from typing import Type

from nozzle.clustering.base import ClusteringStrategy
from nozzle.clustering.strategies.rule_based import RuleBasedStrategy


STRATEGY_REGISTRY: dict[str, Type[ClusteringStrategy]] = {
    "rule_based": RuleBasedStrategy,
    # Future:
    # "field_similarity": FieldSimilarityStrategy,
    # "ml_based": MLBasedStrategy,
    # "temporal_burst": TemporalBurstStrategy,
    # "behavioral": BehavioralStrategy,
}


def get_strategy(name: str, **kwargs) -> ClusteringStrategy:
    """Instantiate a clustering strategy by name."""
    strategy_class = STRATEGY_REGISTRY.get(name)
    if strategy_class is None:
        raise ValueError(f"No strategy registered: {name}")
    return strategy_class(**kwargs)


def register_strategy(name: str, strategy_class: Type[ClusteringStrategy]) -> None:
    """Register a new strategy at runtime."""
    STRATEGY_REGISTRY[name] = strategy_class
