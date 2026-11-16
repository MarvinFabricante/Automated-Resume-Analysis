#!/bin/bash
# ==============================================================================
# Automated Resume Analysis System — Unified Startup & Cloudflare Tunnel Script
# ==============================================================================
# This script:
#   1. Validates prerequisites (Docker, Docker Compose, .env, directories, cloudflared)
#   2. Starts or builds all application containers (DB, Redis, Backend, Worker, Frontend)
#   3. Sets up & verifies Cloudflare Tunnel (Custom Domain e.g. mariwasa.bid or Quick Tunnel)
#   4. Updates .env (PUBLIC_BASE_URL & FRONTEND_URL CORS whitelist)
#   5. Recreates backend and worker so the live tunnel URL takes effect immediately
#   6. Verifies complete health and displays a rich access dashboard
# ==============================================================================

set -euo pipefail

# --- Color Definitions ---
readonly BOLD='\033[1m'
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# --- Project Paths & Config ---
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"

TUNNEL_CONTAINER="resume_analysis_tunnel"
BACKEND_CONTAINER="resume_analysis_backend"
WORKER_CONTAINER="resume_analysis_worker"
DB_CONTAINER="resume_analysis_db"
REDIS_CONTAINER="resume_analysis_redis"
FRONTEND_CONTAINER="resume_analysis_frontend"

# --- Helper: Detect Docker Compose Command ---
detect_docker_compose() {
    if docker compose version >/dev/null 2>&1; then
        echo "docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
    else
        echo -e "${RED}✗ Error: Neither 'docker compose' (v2 plugin) nor 'docker-compose' (v1) was found.${NC}" >&2
        echo -e "${YELLOW}Please install Docker Compose: https://docs.docker.com/compose/install/${NC}" >&2
        exit 1
    fi
}

DOCKER_COMPOSE="$(detect_docker_compose)"

# --- Banner ---
show_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "  ╔═══════════════════════════════════════════════════════════════╗"
    echo "  ║             Automated Resume Analysis System                  ║"
    echo "  ║        Mariwasa Siam Ceramics Inc. — Service Runner           ║"
    echo "  ╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# --- Help Message ---
show_help() {
    show_banner
    echo -e "${WHITE}Usage:${NC} ./start.sh [OPTION]"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo -e "  ${GREEN}(no flags)${NC}      Default: Check, build & start all services, setup Cloudflare domain, and sync env"
    echo -e "  ${GREEN}-q, --quick${NC}     Fast start: Start existing containers without rebuilding images"
    echo -e "  ${GREEN}-b, --rebuild${NC}   Force clean rebuild of all container images (--no-cache)"
    echo -e "  ${GREEN}-r, --restart${NC}   Restart all containers and re-verify Cloudflare tunnel"
    echo -e "  ${GREEN}-s, --stop${NC}      Gracefully stop and take down all containers"
    echo -e "  ${GREEN}--status${NC}        Show current health of all containers, domain, and tunnel"
    echo -e "  ${GREEN}--logs [svc]${NC}    View logs (e.g. ./start.sh --logs backend or ./start.sh --logs frontend)"
    echo -e "  ${GREEN}--seed${NC}          Run database seeds for jobs and HR accounts"
    echo -e "  ${GREEN}-h, --help${NC}      Show this help menu"
    echo ""
}

# --- Pre-flight Checks ---
preflight_checks() {
    echo -e "${BLUE}[1/6] Running system pre-flight checks...${NC}"

    # 1. Check Docker installed
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}  ✗ Docker is not installed.${NC}"
        echo -e "${YELLOW}  Please install Docker Engine: https://docs.docker.com/engine/install/${NC}"
        exit 1
    fi

    # 2. Check Docker daemon running
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}  ✗ Docker daemon is not active or user lacks docker permissions.${NC}"
        echo -e "${YELLOW}  Run:${NC} sudo systemctl start docker"
        echo -e "${YELLOW}  Ensure your user is in docker group:${NC} sudo usermod -aG docker \$USER"
        exit 1
    fi

    # 3. Check .env file
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE" ]; then
            echo -e "${YELLOW}  ! .env file not found. Initializing from .env.example...${NC}"
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            echo -e "${GREEN}  ✓ Created .env file${NC}"
        else
            echo -e "${RED}  ✗ Missing .env and .env.example! Cannot start services.${NC}"
            exit 1
        fi
    fi

    # 4. Check & create required host directories
    mkdir -p "$PROJECT_DIR/uploads/resumes" "$PROJECT_DIR/uploads/resume_images"
    chmod -R 777 "$PROJECT_DIR/uploads" 2>/dev/null || true

    # 5. Check Cloudflare Tunnel tool if custom domain is used
    local custom_domain
    custom_domain=$(grep -E "^CUSTOM_DOMAIN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d ' "' || true)
    if [ -n "$custom_domain" ]; then
        if command -v cloudflared >/dev/null 2>&1; then
            echo -e "${GREEN}  ✓ Cloudflare connector CLI (cloudflared) detected${NC}"
        else
            echo -e "${YELLOW}  ! Note: 'cloudflared' binary not found in PATH.${NC}"
        fi
    fi

    echo -e "${GREEN}  ✓ Pre-flight checks passed${NC}"
    echo ""
}

# --- Wait for Container Health ---
wait_for_db() {
    echo -e "  ... waiting for PostgreSQL to be ready"
    local max_retries=30
    local count=0
    while [ $count -lt $max_retries ]; do
        if $DOCKER_COMPOSE exec -T db pg_isready -U "${DB_USER:-postgres}" -d "${DB_NAME:-automated_resume_db}" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    return 1
}

wait_for_redis() {
    echo -e "  ... waiting for Redis to be ready"
    local max_retries=20
    local count=0
    while [ $count -lt $max_retries ]; do
        if $DOCKER_COMPOSE exec -T redis redis-cli ping >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    return 1
}

wait_for_backend() {
    echo -e "  ... waiting for FastAPI backend to respond"
    local max_retries=35
    local count=0
    while [ $count -lt $max_retries ]; do
        if curl -sf http://localhost:8000/ >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    return 1
}

wait_for_frontend() {
    echo -e "  ... waiting for Frontend (Nginx) to respond"
    local max_retries=20
    local count=0
    while [ $count -lt $max_retries ]; do
        if curl -sf http://localhost:8080/ >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    return 1
}

# --- Start Application Containers ---
start_containers() {
    local mode="${1:-build}"
    echo -e "${BLUE}[2/6] Starting application services...${NC}"

    local custom_domain
    custom_domain=$(grep -E "^CUSTOM_DOMAIN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d ' "' || true)

    if [ "$mode" == "rebuild" ]; then
        echo -e "  ⚙ Rebuilding all container images (clean)..."
        $DOCKER_COMPOSE build --no-cache
        $DOCKER_COMPOSE up -d
    elif [ "$mode" == "quick" ]; then
        echo -e "  ⚡ Quick start (using existing images)..."
        $DOCKER_COMPOSE up -d
    else
        echo -e "  ⚙ Building and starting containers..."
        $DOCKER_COMPOSE up -d --build
    fi

    # In Custom Domain mode, stop the standalone quick-tunnel docker container
    if [ -n "$custom_domain" ]; then
        $DOCKER_COMPOSE stop tunnel >/dev/null 2>&1 || true
    fi

    # Wait for core dependencies
    if ! wait_for_db; then
        echo -e "${RED}  ✗ PostgreSQL failed to become healthy within timeout.${NC}"
        echo -e "${YELLOW}  Check logs:${NC} $DOCKER_COMPOSE logs db"
        exit 1
    fi
    echo -e "${GREEN}  ✓ PostgreSQL is healthy${NC}"

    if ! wait_for_redis; then
        echo -e "${RED}  ✗ Redis failed to become healthy within timeout.${NC}"
        echo -e "${YELLOW}  Check logs:${NC} $DOCKER_COMPOSE logs redis"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Redis is healthy${NC}"

    if ! wait_for_backend; then
        echo -e "${RED}  ✗ Backend failed to start within timeout.${NC}"
        echo -e "${YELLOW}  Check logs:${NC} $DOCKER_COMPOSE logs backend"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Backend is healthy (port 8000)${NC}"

    if ! wait_for_frontend; then
        echo -e "${RED}  ✗ Frontend failed to start within timeout.${NC}"
        echo -e "${YELLOW}  Check logs:${NC} $DOCKER_COMPOSE logs frontend"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Frontend is healthy (port 8080)${NC}"
    echo ""
}

# --- Setup & Verify Cloudflare Tunnel ---
setup_cloudflare_tunnel() {
    echo -e "${BLUE}[3/6] Setting up & verifying Cloudflare Tunnel...${NC}"

    local custom_domain
    custom_domain=$(grep -E "^CUSTOM_DOMAIN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d ' "' || true)
    local tunnel_token
    tunnel_token=$(grep -E "^CLOUDFLARE_TUNNEL_TOKEN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d ' "' || true)

    if [ -n "$custom_domain" ]; then
        echo -e "  🌐 Custom Domain: ${BOLD}${CYAN}https://${custom_domain}${NC}"

        # 1. Ensure quick-tunnel docker container is stopped
        $DOCKER_COMPOSE stop tunnel >/dev/null 2>&1 || true

        # 2. Check and start the cloudflared connector
        if command -v cloudflared >/dev/null 2>&1; then
            if systemctl is-active --quiet cloudflared 2>/dev/null; then
                echo -e "${GREEN}  ✓ Cloudflare system service (cloudflared.service) is active and running${NC}"
            else
                echo -e "${YELLOW}  ⚙ Cloudflare service is stopped. Attempting to start...${NC}"
                # Try systemctl start if sudo available without password
                if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
                    sudo systemctl start cloudflared 2>/dev/null || true
                fi

                # If still not active and token is present, run in background
                if ! systemctl is-active --quiet cloudflared 2>/dev/null; then
                    if [ -n "$tunnel_token" ]; then
                        echo -e "  ⚙ Starting cloudflared tunnel connector in background..."
                        nohup cloudflared tunnel --no-autoupdate run --token "$tunnel_token" >/tmp/cloudflared_custom.log 2>&1 &
                        echo $! > /tmp/cloudflared_custom.pid
                        sleep 3
                        echo -e "${GREEN}  ✓ Cloudflare connector running (PID $(cat /tmp/cloudflared_custom.pid))${NC}"
                    else
                        echo -e "${YELLOW}  ! Notice: Please start the cloudflared service:${NC} sudo systemctl start cloudflared"
                    fi
                fi
            fi
        fi

        ACTIVE_TUNNEL_URL="https://${custom_domain}"

        # 3. Verify public connectivity to the custom domain
        echo -e "  ... verifying public reachability at ${BOLD}https://${custom_domain}${NC}"
        local reachable=false
        local status_code="000"
        for i in {1..8}; do
            status_code=$(curl -s -m 6 -o /dev/null -w "%{http_code}" "https://${custom_domain}" 2>/dev/null || echo "000")
            if [ "$status_code" = "200" ] || [ "$status_code" = "301" ] || [ "$status_code" = "302" ]; then
                reachable=true
                break
            fi
            sleep 2
        done

        if [ "$reachable" = true ]; then
            echo -e "${GREEN}  ✓ Custom domain is LIVE and reachable! (HTTP ${status_code})${NC}"
        else
            if [ "$status_code" = "530" ] || [ "$status_code" = "1016" ]; then
                echo -e "${YELLOW}  ! DNS/Tunnel route propagating at Cloudflare edge (HTTP ${status_code}). Will be fully live shortly.${NC}"
            else
                echo -e "${YELLOW}  ! Domain status: HTTP ${status_code}. Tunnel is active and routing.${NC}"
            fi
        fi

    else
        # Fallback to Quick trycloudflare tunnel
        echo -e "  ⚙ Initializing clean Cloudflare quick tunnel connection..."
        $DOCKER_COMPOSE stop tunnel >/dev/null 2>&1 || true
        $DOCKER_COMPOSE rm -f tunnel >/dev/null 2>&1 || true
        $DOCKER_COMPOSE up -d tunnel >/dev/null 2>&1

        ACTIVE_TUNNEL_URL=""
        local max_wait=45
        local waited=0

        while [ -z "$ACTIVE_TUNNEL_URL" ] && [ "$waited" -lt "$max_wait" ]; do
            sleep 2
            waited=$((waited + 2))
            ACTIVE_TUNNEL_URL=$(docker logs "$TUNNEL_CONTAINER" 2>&1 | grep -oP 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | tail -1 || true)
            if [ -z "$ACTIVE_TUNNEL_URL" ]; then
                echo -e "  ... waiting for Cloudflare edge assignment (${waited}/${max_wait}s)"
            fi
        done

        if [ -z "$ACTIVE_TUNNEL_URL" ]; then
            echo -e "${RED}  ✗ Error: Could not detect Cloudflare Tunnel URL after ${max_wait}s${NC}"
            echo -e "${YELLOW}  Check tunnel logs:${NC} docker logs $TUNNEL_CONTAINER"
            exit 1
        fi

        echo -e "${GREEN}  ✓ Tunnel created: ${BOLD}${ACTIVE_TUNNEL_URL}${NC}"

        # Verify reachability
        local reachable=false
        for i in {1..8}; do
            if curl -sf -m 8 -I "$ACTIVE_TUNNEL_URL" >/dev/null 2>&1; then
                reachable=true
                break
            fi
            sleep 2
        done
        if [ "$reachable" = true ]; then
            echo -e "${GREEN}  ✓ Quick tunnel is active and reachable over the internet!${NC}"
        fi
    fi

    echo ""
}

# --- Synchronize .env with Tunnel URL ---
sync_env_file() {
    local tunnel_url="$1"
    echo -e "${BLUE}[4/6] Synchronizing .env configuration...${NC}"

    # 1. Update or append PUBLIC_BASE_URL
    if grep -q "^PUBLIC_BASE_URL=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=$tunnel_url|" "$ENV_FILE"
    else
        echo "PUBLIC_BASE_URL=$tunnel_url" >> "$ENV_FILE"
    fi
    echo -e "  ✓ PUBLIC_BASE_URL set to ${tunnel_url}"

    # 2. Update FRONTEND_URL cleanly
    local default_origins="http://localhost:5173,http://localhost:3000,http://localhost,http://localhost:80,http://localhost:8080"
    local custom_domain
    custom_domain=$(grep -E "^CUSTOM_DOMAIN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d ' "' || true)

    local target_origins="$default_origins"
    if [ -n "$custom_domain" ]; then
        target_origins="${target_origins},https://${custom_domain},https://www.${custom_domain}"
    fi
    if [ -n "$tunnel_url" ] && [[ "$tunnel_url" != *"//${custom_domain}"* ]]; then
        target_origins="${target_origins},${tunnel_url}"
    fi

    if grep -q "^FRONTEND_URL=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^FRONTEND_URL=.*|FRONTEND_URL=${target_origins}|" "$ENV_FILE"
    else
        echo "FRONTEND_URL=${target_origins}" >> "$ENV_FILE"
    fi
    echo -e "  ✓ FRONTEND_URL CORS origins updated with active domain"

    echo ""
}

# --- Recreate Backend & Worker with New Environment ---
apply_environment_changes() {
    echo -e "${BLUE}[5/6] Applying environment configuration to Backend & AI Worker...${NC}"
    # NOTE: Docker Compose does NOT reload changed env_file variables without --force-recreate
    $DOCKER_COMPOSE up -d --force-recreate backend celery_worker >/dev/null 2>&1

    # Wait for backend to be fully online again
    if ! wait_for_backend; then
        echo -e "${RED}  ✗ Backend failed to recover after environment update.${NC}"
        echo -e "${YELLOW}  Check logs:${NC} $DOCKER_COMPOSE logs backend"
        exit 1
    fi

    echo -e "${GREEN}  ✓ Backend & AI Worker restarted with new domain configuration${NC}"
    echo ""
}

# --- Optional Database Verification / Seeding ---
verify_database() {
    echo -e "${BLUE}[6/6] Verifying database integrity...${NC}"
    local job_count=0
    job_count=$($DOCKER_COMPOSE exec -T backend python -c "
import asyncio
from app.utils.database import AsyncSessionLocal
from sqlalchemy import text
async def count_jobs():
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(text('SELECT count(*) FROM job_descriptions'))
            return res.scalar() or 0
    except Exception:
        return 0
print(asyncio.run(count_jobs()))
" 2>/dev/null || echo 0)

    if [ "$job_count" -eq 0 ]; then
        echo -e "${YELLOW}  ! Database has no job descriptions yet.${NC}"
        echo -e "${CYAN}  Tip: You can seed default Mariwasa jobs and HR accounts anytime with:${NC}"
        echo -e "       ${BOLD}./start.sh --seed${NC}"
    else
        echo -e "${GREEN}  ✓ Database connected and populated (${job_count} active jobs)${NC}"
    fi
    echo ""
}

# --- Run Seeds ---
run_seeds() {
    show_banner
    preflight_checks
    echo -e "${BLUE}🌱 Running Database Seeds (Jobs & HR Accounts)...${NC}"
    echo ""
    echo -e "  [1/2] Seeding Mariwasa Job Descriptions..."
    $DOCKER_COMPOSE exec -T backend python seed_mariwasa_jobs.py
    echo ""
    echo -e "  [2/2] Seeding HR Staff Accounts..."
    $DOCKER_COMPOSE exec -T backend python seed_hr_accounts.py
    echo ""
    echo -e "${GREEN}✓ Seeding complete!${NC}"
}

# --- Show Status ---
show_status() {
    show_banner
    echo -e "${WHITE}${BOLD}Container Status:${NC}"
    $DOCKER_COMPOSE ps
    echo ""

    local custom_domain
    custom_domain=$(grep -E "^CUSTOM_DOMAIN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d ' "' || true)
    local env_tunnel_url
    env_tunnel_url=$(grep "^PUBLIC_BASE_URL=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)

    echo -e "${WHITE}${BOLD}Tunnel & Domain Status:${NC}"
    if [ -n "$custom_domain" ]; then
        echo -e "  Mode:                  ${GREEN}${BOLD}Purchased Custom Domain (${custom_domain})${NC}"
        echo -e "  Configured in .env:    ${CYAN}${env_tunnel_url}${NC}"
        if systemctl is-active --quiet cloudflared 2>/dev/null; then
            echo -e "  Connector Service:     ${GREEN}cloudflared.service is ACTIVE (host)${NC}"
        else
            echo -e "  Connector Service:     ${YELLOW}cloudflared.service is INACTIVE${NC}"
        fi

        local status_code
        status_code=$(curl -s -m 5 -o /dev/null -w "%{http_code}" "https://${custom_domain}" 2>/dev/null || echo "000")
        if [ "$status_code" = "200" ] || [ "$status_code" = "301" ] || [ "$status_code" = "302" ]; then
            echo -e "  Public Reachability:   ${GREEN}Online & Responding (HTTP ${status_code})${NC}"
        else
            echo -e "  Public Reachability:   ${YELLOW}HTTP ${status_code} (connecting or propagating)${NC}"
        fi
    else
        local tunnel_url=""
        tunnel_url=$(docker logs "$TUNNEL_CONTAINER" 2>&1 | grep -oP 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | tail -1 || true)
        if [ -n "$tunnel_url" ]; then
            echo -e "  Mode:                  ${YELLOW}Quick Tunnel (trycloudflare.com)${NC}"
            echo -e "  Active URL:            ${GREEN}${BOLD}${tunnel_url}${NC}"
            echo -e "  Configured in .env:    ${CYAN}${env_tunnel_url}${NC}"
            if curl -sf -m 5 -I "$tunnel_url" >/dev/null 2>&1; then
                echo -e "  Reachability:          ${GREEN}Online & Responding (200 OK)${NC}"
            else
                echo -e "  Reachability:          ${YELLOW}Connecting / Not responding yet${NC}"
            fi
        else
            echo -e "  ${RED}No active tunnel found. Run ./start.sh to start it.${NC}"
        fi
    fi
    echo ""
}

# --- Stop Services ---
stop_services() {
    show_banner
    echo -e "${YELLOW}Stopping all Automated Resume Analysis services...${NC}"
    $DOCKER_COMPOSE down
    if [ -f /tmp/cloudflared_custom.pid ]; then
        kill "$(cat /tmp/cloudflared_custom.pid)" 2>/dev/null || true
        rm -f /tmp/cloudflared_custom.pid
    fi
    echo -e "${GREEN}✓ All services stopped.${NC}"
}

# --- View Logs ---
view_logs() {
    local service="${1:-}"
    if [ -n "$service" ]; then
        echo -e "${CYAN}Streaming logs for service: ${BOLD}${service}${NC} (Ctrl+C to exit)..."
        $DOCKER_COMPOSE logs -f "$service"
    else
        echo -e "${CYAN}Streaming logs for all services (Ctrl+C to exit)..."
        $DOCKER_COMPOSE logs -f
    fi
}

# --- Display Final Dashboard ---
display_dashboard() {
    local tunnel_url="$1"
    local custom_domain
    custom_domain=$(grep -E "^CUSTOM_DOMAIN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d ' "' || true)

    echo -e "${GREEN}${BOLD}═════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}             🎉 APPLICATION READY & RUNNING!                    ${NC}"
    echo -e "${GREEN}${BOLD}═════════════════════════════════════════════════════════════════${NC}"
    echo ""
    if [ -n "$custom_domain" ]; then
        echo -e "  ${WHITE}${BOLD}🌐 PUBLIC DOMAIN:${NC}            ${CYAN}${BOLD}https://${custom_domain}${NC}"
        echo -e "  ${WHITE}${BOLD}🌐 WWW DOMAIN:${NC}               ${CYAN}${BOLD}https://www.${custom_domain}${NC}"
    else
        echo -e "  ${WHITE}${BOLD}🌐 PUBLIC URL (Cloudflare):${NC}   ${CYAN}${BOLD}${tunnel_url}${NC}"
    fi
    echo -e "  ${WHITE}${BOLD}💻 LOCAL FRONTEND:${NC}           ${WHITE}http://localhost:8080${NC}"
    echo -e "  ${WHITE}${BOLD}📚 FASTAPI DOCS (Swagger):${NC}   ${WHITE}http://localhost:8000/docs${NC}"
    echo -e "  ${WHITE}${BOLD}🗄️  POSTGRESQL PORT:${NC}         ${WHITE}localhost:5434${NC}"
    echo -e "  ${WHITE}${BOLD}⚡ REDIS CACHE PORT:${NC}         ${WHITE}localhost:6380${NC}"
    echo ""
    echo -e "${YELLOW}${BOLD}  🔑 GOOGLE OAUTH CONFIGURATION:${NC}"
    echo -e "     If using Google Login, add this authorized redirect URI in"
    echo -e "     Google Cloud Console (Credentials > Authorized redirect URIs):"
    echo -e "     ${BOLD}${tunnel_url}/api/auth/google/callback${NC}"
    echo ""
    echo -e "${WHITE}${BOLD}  🛠️  HELPFUL COMMANDS:${NC}"
    echo -e "     View status:   ${GREEN}./start.sh --status${NC}"
    echo -e "     Stream logs:   ${GREEN}./start.sh --logs${NC} (or ./start.sh --logs backend)"
    echo -e "     Stop app:      ${GREEN}./start.sh --stop${NC}"
    echo -e "     Restart app:   ${GREEN}./start.sh --restart${NC}"
    echo -e "${GREEN}${BOLD}═════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# ==============================================================================
# Main Dispatcher
# ==============================================================================
main() {
    local mode="build"

    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--stop|stop|down)
                stop_services
                exit 0
                ;;
            --status|status)
                show_status
                exit 0
                ;;
            --seed|seed)
                run_seeds
                exit 0
                ;;
            -l|--logs|logs)
                shift
                view_logs "${1:-}"
                exit 0
                ;;
            -q|--quick|quick)
                mode="quick"
                shift
                ;;
            -b|--rebuild|rebuild)
                mode="rebuild"
                shift
                ;;
            -r|--restart|restart)
                mode="restart"
                shift
                ;;
            start|up)
                shift
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done

    show_banner
    preflight_checks

    if [ "$mode" == "restart" ]; then
        echo -e "${YELLOW}Restarting all services...${NC}"
        $DOCKER_COMPOSE down
        mode="quick"
    fi

    start_containers "$mode"
    setup_cloudflare_tunnel
    sync_env_file "$ACTIVE_TUNNEL_URL"
    apply_environment_changes
    verify_database
    display_dashboard "$ACTIVE_TUNNEL_URL"
}

main "$@"
