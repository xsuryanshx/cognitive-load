#!/bin/bash
# Simple script to run the backend server

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the server
uvicorn backend.main:app --reload --port 8000 --host 0.0.0.0

