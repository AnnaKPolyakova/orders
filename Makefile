.PHONY: init lint fmt types test cov hooks build run

init:
	poetry install
	poetry run pre-commit install

lint:
	poetry run ruff check .
	poetry run black --check .

fmt:
	poetry run ruff check . --fix
	poetry run ruff format .
	poetry run black .

types:
	poetry run mypy

test:
	poetry run pytest -q

cov:
	poetry run pytest --cov=acme_app --cov-report=term-missing

build:
	poetry build

run:
	poetry run acme --help
