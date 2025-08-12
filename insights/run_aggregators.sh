#!/bin/bash

set -euo pipefail

# ====== CONFIG ======
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/aggregator_run_$(date +%Y%m%d_%H%M%S).log"

# ====== FUNCTIONS ======
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ====== START ======
log "Starting aggregator scripts"

cd "$SCRIPT_DIR"

# Detect OS
OS_TYPE="$(uname -s)"
log "Detected OS: $OS_TYPE"

# Ensure python3 is available
if ! command -v python3 >/dev/null 2>&1; then
    log "ERROR: python3 not found in PATH"
    exit 1
fi

# Check venv support
if ! python3 -m venv --help >/dev/null 2>&1; then
    if [[ "$OS_TYPE" == "Linux" ]]; then
        # Try to detect Debian/Ubuntu
        if command -v apt >/dev/null 2>&1; then
            log "python3-venv not installed. Attempting to install..."
            if [ "$(id -u)" -ne 0 ]; then
                log "Re-running with sudo to install python3-venv..."
                sudo apt update && sudo apt install -y python3-venv
            else
                apt update && apt install -y python3-venv
            fi
        else
            log "ERROR: python3-venv missing and cannot auto-install on this Linux."
            exit 1
        fi
    elif [[ "$OS_TYPE" == "Darwin" ]]; then
        log "NOTE: macOS detected, python3-venv usually included."
        log "If venv still fails, reinstall Python via Homebrew: brew install python3"
    fi
fi

# Create virtual environment if missing
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    log "Virtual environment not found. Creating..."
    python3 -m venv "$SCRIPT_DIR/.venv"
    log "Virtual environment created."
fi

# Activate venv
log "Activating virtual environment"
source "$SCRIPT_DIR/.venv/bin/activate"

# Install requirements if not already done
REQ_MARKER="$SCRIPT_DIR/.venv/.requirements_installed"
if [ ! -f "$REQ_MARKER" ]; then
    log "Installing requirements..."
    pip install --upgrade pip
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt"
    else
        log "WARNING: requirements.txt not found, skipping dependency install."
    fi
    touch "$REQ_MARKER"
    log "Requirements installed."
fi

# Run aggregators
log "Running Tech News Aggregator..."
python "$SCRIPT_DIR/tech_news_aggregator.py"
log "Tech News Aggregator completed."

log "Waiting 30 seconds..."
sleep 30

log "Running Personal Growth Aggregator..."
python "$SCRIPT_DIR/personal_growth_aggregator.py"
log "Personal Growth Aggregator completed."

# Deactivate venv
deactivate

log "All scripts completed successfully."
exit 0

