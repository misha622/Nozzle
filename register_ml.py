path = r"nozzle\clustering\registry.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    "from nozzle.clustering.strategies.rule_based import RuleBasedStrategy",
    "from nozzle.clustering.strategies.rule_based import RuleBasedStrategy\nfrom nozzle.clustering.strategies.ml_based import MLBasedStrategy"
)
c = c.replace(
    '"rule_based": RuleBasedStrategy,',
    '"rule_based": RuleBasedStrategy,\n    "ml_based": MLBasedStrategy,'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("ML strategy registered")
