#!/bin/bash

# Configuration
PROJECT_DIR="/home/neelpatel/Code/finance/backend"
LOG_FILE="$PROJECT_DIR/sync.log"

# Navigate to project dir
cd "$PROJECT_DIR" || exit 1

# Timestamp
echo "--- Sync Started: $(date) ---" >> "$LOG_FILE"

# Run the python script using the venv
# ensure .env is loaded by the python script (which it is via dotenv)
./.venv/bin/python main.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "--- Sync Success: $(date) ---" >> "$LOG_FILE"
else
    echo "--- Sync Failed (Exit $EXIT_CODE): $(date) ---" >> "$LOG_FILE"
fi
