#!/usr/bin/env bash
set -euo pipefail

if ! python -c "import pydantic, anthropic, requests" >/dev/null 2>&1; then
  echo "Error: Python dependencies are not installed in the active environment."
  echo "Create/activate the virtual environment and run:"
  echo "  pip install -r requirements.txt"
  exit 1
fi

for file in input/*.json; do
  echo
  echo "============================================================"
  echo "Processing: $file"
  echo "============================================================"

  python -m src.podcast_agent.main --input "$file"
done

echo
echo "All transcripts processed successfully."