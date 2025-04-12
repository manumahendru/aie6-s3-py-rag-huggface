#!/bin/bash
set -e

# Start the backend FastAPI server
echo "Starting FastAPI backend..."
cd $HOME/app/backend
# Use exec to replace the shell process with uvicorn, makes signal handling cleaner
# We don't need to run it in the background (&) anymore as it's the main process
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# The following lines are no longer needed as Uvicorn is the main process
# BACKEND_PID=$!
# echo "Backend started (PID: $BACKEND_PID)"
#
# # Wait for backend to start
# echo "Waiting for backend to start..."
# sleep 5
#
# # Start the frontend server
# echo "Starting React frontend..."
# cd $HOME/app
# serve -s frontend/build -l 3000 &
# FRONTEND_PID=$!
# echo "Frontend started (PID: $FRONTEND_PID)"
#
# # Handle script termination
# trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM
#
# # Keep the script running
# echo "Both services are running. Use http://localhost:3000 to access the application."
# while true; do
#     sleep 1
# done 