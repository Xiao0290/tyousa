# Agent Guide

## Setup
- Use `python -m venv .venv && source .venv/bin/activate` to create an isolated env.
- Install dependencies with `pip install -e .[dev]`.

## Quality
- Format with `black .`.
- Lint with `ruff check .`.
- Run tests with `pytest`.

## Notes
- Prefer Typer CLI defined in `src/tyousa/cli.py`.
- Avoid hard-coding column indices; rely on headers when writing Excel files.
