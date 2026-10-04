#!/bin/bash
# ==============================================================================
# deploy.sh — Wrapper forwarding to start.sh
# ==============================================================================
# This script forwards all arguments to the unified startup script start.sh
# to build, start, create the Cloudflare tunnel, and synchronize environments.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start.sh" "$@"
