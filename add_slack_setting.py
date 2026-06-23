path = r"nozzle\settings.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace(
    'api_key: str = ""',
    'api_key: str = ""\n\n    # Slack\n    slack_webhook_url: str = ""'
)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("slack_webhook_url added")
