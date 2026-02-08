.PHONY: init test build format lint typecheck clean
.PHONY: index index-core index-client stats
.PHONY: docker-build docker-run docker-clean

# Development
init:
	uv sync --all-groups

test:
	uv run pytest --cov

build: lint typecheck test

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

lint:
	uv run ruff check src/ tests/

typecheck:
	uv run mypy src/

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Indexing
index:
	uv run airflow-docs-index index

index-core:
	uv run airflow-docs-index index --source airflow-core

index-client:
	uv run airflow-docs-index index --source airflow-python-client

stats:
	uv run airflow-docs-index stats

# Docker
docker-build:
	docker build -t mcp-airflow-documentation .

docker-run:
	docker run -i --rm mcp-airflow-documentation

docker-clean:
	docker rmi mcp-airflow-documentation
