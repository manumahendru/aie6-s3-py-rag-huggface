#!/bin/bash

# Start the backend
echo "Starting the FastAPI backend..."
cd backend

# Check if Python virtual environment exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
fi

# Start the backend in the background
python3.12 run.py &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Start the frontend
echo "Starting the React frontend..."
cd ../frontend

# Check if node_modules exists, if not run npm install
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start the frontend
npm start &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

# Handle script termination
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM

# Keep the script running
echo "Both services are running. Press Ctrl+C to stop."
wait 