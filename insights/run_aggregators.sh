#!/bin/bash
# Shell script to run both aggregator scripts in sequence
# This script activates the virtual environment and runs the aggregators

# Exit on error
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Log file path
LOG_FILE="$SCRIPT_DIR/aggregator_run_$(date +%Y%m%d_%H%M%S).log"

# Function to log messages
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Start logging
log "Starting aggregator scripts"

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
  log "Virtual environment not found. Creating one..."
  python3 -m venv .venv
  log "Virtual environment created."
fi

# Activate virtual environment
log "Activating virtual environment"
source "$SCRIPT_DIR/.venv/bin/activate"

# Check if requirements are installed
if [ ! -f "$SCRIPT_DIR/.venv/.requirements_installed" ]; then
  log "Installing requirements..."
  pip install -r requirements.txt
  touch "$SCRIPT_DIR/.venv/.requirements_installed"
  log "Requirements installed."
fi

# Run tech news aggregator
log "Running Tech News Aggregator..."
python "$SCRIPT_DIR/tech_news_aggregator.py"
log "Tech News Aggregator completed"

# Wait for 30 seconds
log "Waiting 30 seconds before running the next script..."
sleep 30

# Run personal growth aggregator
log "Running Personal Growth Aggregator..."
python "$SCRIPT_DIR/personal_growth_aggregator.py"
log "Personal Growth Aggregator completed"

# Deactivate virtual environment
deactivate

log "All scripts completed successfully"

# Exit successfully
exit 0
