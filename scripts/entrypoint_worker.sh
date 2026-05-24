#!/bin/bash
set -e

# Run self-diagnostics
echo "Running diagnostics..."
python scripts/diagnostic.py

# Start the worker
echo "Starting worker..."
exec python -m worker
