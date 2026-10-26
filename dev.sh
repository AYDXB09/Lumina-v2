#!/bin/bash
# Start Lumina V2 — backend + frontend in one terminal
# Usage: ./dev.sh
# Stop:  Ctrl+C

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Kill anything already on these ports
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

echo "Starting Lumina V2..."
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo "  Press Ctrl+C to stop both"
echo ""

# Start backend
cd "$ROOT/backend" && python3 main.py &
BACKEND_PID=$!

# Start frontend
cd "$ROOT/frontend" && npm run dev &
FRONTEND_PID=$!

# Ctrl+C kills both
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait
