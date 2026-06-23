p = r"nozzle\clustering\registry.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace(
    "from nozzle.clustering.strategies.temporal_burst import TemporalBurstStrategy",
    "from nozzle.clustering.strategies.temporal_burst import TemporalBurstStrategy\nfrom nozzle.clustering.strategies.hybrid import HybridStrategy"
)
c = c.replace(
    '"temporal_burst": TemporalBurstStrategy,',
    '"temporal_burst": TemporalBurstStrategy,\n    "hybrid": HybridStrategy,'
)
with open(p, "w", encoding="utf-8") as f:
    f.write(c)
print("Hybrid registered")
