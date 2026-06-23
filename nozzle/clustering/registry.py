"""Registry for clustering strategies."""

from typing import Type

from nozzle.clustering.base import ClusteringStrategy
from nozzle.clustering.strategies.rule_based import RuleBasedStrategy
from nozzle.clustering.strategies.ml_based import MLBasedStrategy
from nozzle.clustering.strategies.semantic import SemanticStrategy
from nozzle.clustering.strategies.temporal_burst import TemporalBurstStrategy
from nozzle.clustering.strategies.hybrid import HybridStrategy


STRATEGY_REGISTRY: dict[str, Type[ClusteringStrategy]] = {
    "rule_based": RuleBasedStrategy,
    "ml_based": MLBasedStrategy,
    "semantic": SemanticStrategy,
    "temporal_burst": TemporalBurstStrategy,
    "hybrid": HybridStrategy,
    # Future:
    # "field_similarity": FieldSimilarityStrategy,
    # "ml_based": MLBasedStrategy,
    "semantic": SemanticStrategy,
    "temporal_burst": TemporalBurstStrategy,
    "hybrid": HybridStrategy,
    # "temporal_burst": TemporalBurstStrategy,
    "hybrid": HybridStrategy,
    # "behavioral": BehavioralStrategy,
}


def get_strategy(name: str, **kwargs) -> ClusteringStrategy:
    """Instantiate a clustering strategy by name."""
    strategy_class = STRATEGY_REGISTRY.get(name)
    if strategy_class is None:
        raise ValueError(f"No strategy registered: {name}")

    # Filter kwargs to only what the strategy accepts
    import inspect
    sig = inspect.signature(strategy_class.__init__)
    valid_params = set(sig.parameters.keys()) - {"self"}
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
    return strategy_class(**filtered_kwargs)


def register_strategy(name: str, strategy_class: Type[ClusteringStrategy]) -> None:
    """Register a new strategy at runtime."""
    STRATEGY_REGISTRY[name] = strategy_class
