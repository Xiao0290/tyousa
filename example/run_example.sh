#!/usr/bin/env bash
set -euo pipefail

# Example pipeline using RichReport fixtures (no external API keys required)
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
CANDIDATES="$ROOT_DIR/example/candidates_example.csv"
TEMPLATE="$ROOT_DIR/example/template.xlsx"

# Generate sample template and RichReport workbook locally (avoids storing binaries)
python -m tyousa.cli prepare-samples --output-dir "$ROOT_DIR/example"

# Fetch stats from RichReport sample and write filled workbook
python -m tyousa.cli fetch-stats "$CANDIDATES" --richreport-root "$ROOT_DIR/example"
python -m tyousa.cli fill-excel outputs/metrics.csv --template-path "$TEMPLATE"

echo "Filled workbook saved to outputs/filled.xlsx"
