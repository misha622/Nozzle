# Fix 1: settings.py - add api_key
path = r"nozzle\settings.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace(
    "api_port: int = 8000",
    'api_port: int = 8000\n\n    # Auth\n    api_key: str = ""'
)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("1. api_key added to settings")

# Fix 2: main.py - add auth dependency
path = r"nozzle\main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace(
    "from fastapi import FastAPI",
    "from fastapi import FastAPI, Security"
)
c = c.replace(
    "from nozzle.api.router import api_router",
    "from nozzle.api.router import api_router\nfrom nozzle.web.utils.auth import verify_api_key"
)
c = c.replace(
    'app.include_router(api_router, prefix="/api/v1")',
    'app.include_router(api_router, prefix="/api/v1", dependencies=[Security(verify_api_key)])'
)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("2. API key auth added to main")

# Fix 3: ml/training.py - model persistence
path = r"nozzle\ml\training.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace(
    'logger.info(f"Trained classifier on {len(X)} samples, accuracy: {self.model.score(X, y):.2f}")',
    'import joblib, os\n        os.makedirs("models", exist_ok=True)\n        joblib.dump(self.model, "models/noise_classifier.pkl")\n        logger.info(f"Trained classifier on {len(X)} samples, saved to models/noise_classifier.pkl")'
)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("3. Model persistence added")

# Fix 4: semantic.py - async encode
path = r"nozzle\clustering\strategies\semantic.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace(
    "model = self._get_model()\n        embeddings = model.encode(descriptions, show_progress_bar=False)",
    "model = self._get_model()\n        import asyncio\n        embeddings = await asyncio.to_thread(model.encode, descriptions, show_progress_bar=False, batch_size=32)"
)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("4. asyncio.to_thread added")

print("\nAll Day 2 fixes applied.")
