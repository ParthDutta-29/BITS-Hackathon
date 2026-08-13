#!/usr/bin/env bash
set -e

# Default values
DOCS_DIR="documents"
QUESTIONS_FILE="questions.json"
OUT_FILE="submission.csv"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --docs)
      DOCS_DIR="$2"
      shift 2
      ;;
    --questions)
      QUESTIONS_FILE="$2"
      shift 2
      ;;
    --out)
      OUT_FILE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "=============================================="
echo "Starting End-to-End Pipeline Execution"
echo "  Documents Directory : $DOCS_DIR"
echo "  Questions File      : $QUESTIONS_FILE"
echo "  Output CSV File     : $OUT_FILE"
echo "=============================================="

PYTHON_CMD=$(which python3 2>/dev/null || which python 2>/dev/null || echo "python")

echo "[1/4] Running Document Ingestion..."
$PYTHON_CMD ingest.py --docs "$DOCS_DIR"

echo "[2/4] Running Entity Extraction..."
$PYTHON_CMD extract_entities.py

echo "[3/4] Building SQLite Database..."
$PYTHON_CMD build_database.py --docs "$DOCS_DIR"

echo "[4/4] Generating Submission CSV..."
$PYTHON_CMD generate_submission.py --questions "$QUESTIONS_FILE" --out "$OUT_FILE"

echo "=============================================="
echo "Pipeline Execution Completed Successfully!"
echo "Output generated at: $OUT_FILE"
echo "=============================================="
