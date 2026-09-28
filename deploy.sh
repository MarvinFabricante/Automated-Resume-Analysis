#!/bin/bash
# ============================================================================
# deploy.sh — Build, deploy, and auto-configure the Cloudflare tunnel URL
# ============================================================================
# This script:
#   1. Brings up all containers via docker compose
#   2. Waits for the Cloudflare quick tunnel to generate its URL
#   3. Updates PUBLIC_BASE_URL in .env with the detected tunnel URL
#   4. Restarts the backend so it picks up the new URL for OAuth/CORS
# ============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

ENV_FILE="$PROJECT_DIR/.env"
TUNNEL_CONTAINER="resume_analysis_tunnel"
BACKEND_CONTAINER="resume_analysis_backend"
WORKER_CONTAINER="resume_analysis_worker"

echo "============================================"
echo "  Automated Resume Analysis — Deployment"
echo "============================================"
echo ""

# --- Step 1: Build and start all services ---
echo "[1/4] Building and starting all services..."
docker compose up -d --build
echo "  ✓ All services started"
echo ""

# --- Step 2: Wait for Cloudflare tunnel URL ---
echo "[2/4] Waiting for Cloudflare tunnel URL..."
TUNNEL_URL=""
MAX_WAIT=60
WAITED=0

while [ -z "$TUNNEL_URL" ] && [ "$WAITED" -lt "$MAX_WAIT" ]; do
    # Extract the trycloudflare.com URL from tunnel logs
    TUNNEL_URL=$(docker logs "$TUNNEL_CONTAINER" 2>&1 | grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1 || true)
    
    if [ -z "$TUNNEL_URL" ]; then
        sleep 2
        WAITED=$((WAITED + 2))
        echo "  ... waiting ($WAITED/${MAX_WAIT}s)"
    fi
done

if [ -z "$TUNNEL_URL" ]; then
    echo "  ✗ ERROR: Could not detect tunnel URL after ${MAX_WAIT}s"
    echo "  Check tunnel logs: docker logs $TUNNEL_CONTAINER"
    exit 1
fi

echo "  ✓ Tunnel URL detected: $TUNNEL_URL"
echo ""

# --- Step 3: Update .env with the tunnel URL ---
echo "[3/4] Updating .env with tunnel URL..."

# Update or add PUBLIC_BASE_URL
if grep -q "^PUBLIC_BASE_URL=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=$TUNNEL_URL|" "$ENV_FILE"
else
    echo "PUBLIC_BASE_URL=$TUNNEL_URL" >> "$ENV_FILE"
fi

# Update FRONTEND_URL to include the tunnel URL
if grep -q "^FRONTEND_URL=" "$ENV_FILE" 2>/dev/null; then
    CURRENT_FRONTEND=$(grep "^FRONTEND_URL=" "$ENV_FILE" | cut -d= -f2-)
    # Add tunnel URL if not already present
    if ! echo "$CURRENT_FRONTEND" | grep -q "$TUNNEL_URL"; then
        sed -i "s|^FRONTEND_URL=.*|FRONTEND_URL=${CURRENT_FRONTEND},${TUNNEL_URL}|" "$ENV_FILE"
    fi
else
    echo "FRONTEND_URL=$TUNNEL_URL" >> "$ENV_FILE"
fi

echo "  ✓ .env updated"
echo ""

# --- Step 4: Restart backend to pick up new env vars ---
echo "[4/4] Recreating backend and worker to apply new URLs..."
docker compose up -d backend celery_worker
echo "  ✓ Backend and worker updated"
echo ""

# --- Summary ---
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
echo ""
echo "  Public URL:    $TUNNEL_URL"
echo "  Local URL:     http://localhost:8080"
echo "  API Docs:      http://localhost:8000/docs"
echo ""
echo "  Google OAuth:  Update your Google Cloud Console"
echo "  redirect URI to:"
echo "    ${TUNNEL_URL}/api/auth/google/callback"
echo ""
echo "  To view logs:"
echo "    docker compose logs -f"
echo ""
echo "  NOTE: Quick tunnel URLs change on restart."
echo "  Re-run this script after a restart to update."
echo "============================================"
