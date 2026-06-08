#!/bin/bash
# Start script for Foundry Workload Studio gateway + React frontend.
# Mirrors the layout from foundry-dealer-portal-chat (start/stop scripts,
# logs/ directory, port 8000 backend + 5173 frontend).

set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

echo "========================================"
echo "Foundry Workload Studio Launcher"
echo "========================================"

# Check virtual environment
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "Error: Virtual environment not found at $PROJECT_ROOT/.venv"
    echo "Create it with: uv sync --extra dev"
    exit 1
fi

# Check frontend dependencies
if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    echo "Error: Frontend dependencies not installed"
    echo "Run: cd frontend && npm install"
    exit 1
fi

# Stop any existing services first
fuser -k 8000/tcp 2>/dev/null
fuser -k 5173/tcp 2>/dev/null
sleep 1

# Load environment variables from .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
    echo "Environment loaded from .env"
else
    echo "Warning: No .env file found — using defaults (offline stub mode)"
fi

# Start backend (FastAPI gateway)
echo "Starting Backend Gateway..."
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT"
"$PROJECT_ROOT/.venv/bin/uvicorn" src.gateway.api:app \
    --host 0.0.0.0 --port 8000 --reload \
    > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

sleep 3

# Start frontend (Vite dev server)
echo "Starting Frontend App..."
cd "$PROJECT_ROOT/frontend"
npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

sleep 3

echo ""
echo "========================================"
echo "Services started!"
echo "========================================"
echo ""
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "Frontend: http://localhost:5173"
echo ""
echo "Mode:        ${ENVIRONMENT:-dev} $(if [ "${ENVIRONMENT:-dev}" = "dev" ] || [ "${ENVIRONMENT:-dev}" = "test" ]; then echo '(offline stub agents)'; else echo '(LIVE Azure)'; fi)"
echo "Foundry:     ${FOUNDRY_PROJECT_ENDPOINT:-not configured}"
echo "Search:      ${AZURE_SEARCH_ENDPOINT:-not configured}"
echo "Telemetry:   ${ENABLE_TELEMETRY:-true}"
echo ""
echo "View logs:"
echo "  tail -f $LOG_DIR/backend.log"
echo "  tail -f $LOG_DIR/frontend.log"
echo ""
echo "Stop: ./stop.sh"
