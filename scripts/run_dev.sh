#!/usr/bin/env bash
# ==============================================================================
# Development runner script for NOIPMP platform
# ==============================================================================

set -euo pipefail

echo "=== Starting Network Operations Intelligence Platform (Dev Mode) ==="
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
