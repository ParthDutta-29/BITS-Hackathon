#!/usr/bin/env bash
set -e

echo "=== Setup Environment ==="
PYTHON_CMD=$(which python3 2>/dev/null || which python 2>/dev/null || echo "python")
echo "Using Python executable: $PYTHON_CMD"

echo "Installing dependencies from requirements.txt..."
$PYTHON_CMD -m pip install -r requirements.txt

echo "Setup completed successfully!"
