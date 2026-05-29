#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/aggregator_run_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

log() {
	printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" | tee -a "$LOG_FILE"
}

if ! command -v uv >/dev/null 2>&1; then
	log "ERROR: uv not found in PATH"
	exit 1
fi

log "Syncing dependencies with uv"
uv sync --project "$SCRIPT_DIR"

log "Running Tech News Aggregator"
uv run --project "$SCRIPT_DIR" python "$SCRIPT_DIR/tech_news_aggregator.py"

log "Waiting 30 seconds"
sleep 30

log "Running Personal Growth Aggregator"
uv run --project "$SCRIPT_DIR" python "$SCRIPT_DIR/personal_growth_aggregator.py"

log "All scripts completed successfully"
