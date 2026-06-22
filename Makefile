.PHONY: install dev test lint run migrate clean

install:
	uv sync

dev:
	uv sync --group dev
	uv run pre-commit install

test:
	uv run pytest -v --cov=nozzle --cov-report=term-missing

test-integration:
	uv run pytest tests/integration/ -v

lint:
	uv run ruff check .
	uv run mypy nozzle/

format:
	uv run ruff format .

run:
	uv run uvicorn nozzle.main:app --reload --host 0.0.0.0 --port 8000

run-web:
	uv run streamlit run nozzle/web/app.py

migrate-create:
	uv run alembic revision --autogenerate -m "$(msg)"

migrate-up:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

docker-build:
	docker build -t nozzle:latest -f docker/Dockerfile .

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +