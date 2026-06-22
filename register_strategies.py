path = r"nozzle\clustering\registry.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    "from nozzle.clustering.strategies.ml_based import MLBasedStrategy",
    "from nozzle.clustering.strategies.ml_based import MLBasedStrategy\nfrom nozzle.clustering.strategies.semantic import SemanticStrategy\nfrom nozzle.clustering.strategies.temporal_burst import TemporalBurstStrategy"
)
c = c.replace(
    '"ml_based": MLBasedStrategy,',
    '"ml_based": MLBasedStrategy,\n    "semantic": SemanticStrategy,\n    "temporal_burst": TemporalBurstStrategy,'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("All 4 strategies registered")
