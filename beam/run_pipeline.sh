#!/bin/bash

# ============================================================================
# APACHE BEAM PIPELINE RUNNER
# ============================================================================
#
# Runs the local DirectRunner pipeline to process Pub/Sub messages.
# DirectRunner runs entirely on your machine - no GCP resources used - $0 cost
#
# Usage: bash beam/run_pipeline.sh [--limit 100]

LIMIT=${1:-100}

echo "[INFO] Starting Apache Beam pipeline (DirectRunner)"
echo "[INFO] Limit: $LIMIT messages"
echo ""

python beam/pipeline.py --limit $LIMIT

echo ""
echo "[✓] Pipeline execution complete"
