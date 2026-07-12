#!/bin/bash
set -e

PROJECT_DIR="/path/to/naukri_automation_resume"
VENV_DIR="$PROJECT_DIR/venv"
LOGFILE="$PROJECT_DIR/naukri_log.txt"
DEBUGFILE="$PROJECT_DIR/debug.txt"

# Minimal PATH for cron
export PATH="/usr/bin:/bin:/snap/bin"

echo "CRON TRIGGERED at $(date)" >> "$DEBUGFILE"
echo "----------------------------------------" >> "$LOGFILE"
echo "$(date): Job started" >> "$LOGFILE"

cd "$PROJECT_DIR"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Run script
pip install -r requirements.txt
python naukri.py >> "$LOGFILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date): Job finished successfully" >> "$LOGFILE"
else
    echo "$(date): Job failed with exit code $EXIT_CODE" >> "$LOGFILE"
fi

echo "" >> "$LOGFILE"
