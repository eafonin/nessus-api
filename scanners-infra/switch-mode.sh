#!/bin/bash

# =============================================================================
# Nessus Scanner Mode Switching Script
# =============================================================================
# Purpose: Switch Nessus scanners between NORMAL and UPDATE modes
#
# Modes:
#   NORMAL: LAN scanning + WebUI access from host (ports 8834/8835)
#   UPDATE: Plugin updates via VPN (no port forwarding)
#
# Usage:
#   ./switch-mode.sh normal   # Switch to normal mode
#   ./switch-mode.sh update   # Switch to update mode
#   ./switch-mode.sh status   # Show current mode
#   ./switch-mode.sh help     # Show this help
#
# =============================================================================

set -euo pipefail

# Configuration
COMPOSE_DIR="/home/nessus/docker/nessus-shared"
BASE_COMPOSE="docker-compose.yml"
UPDATE_OVERRIDE="docker-compose.update-mode.yml"
MODE_FILE=".current_mode"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to compose directory
cd "$COMPOSE_DIR"

# Export timestamp for docker-compose
export MODE_SWITCH_TIMESTAMP=$(date +%s)

# =============================================================================
# Functions
# =============================================================================

show_help() {
    echo "Nessus Scanner Mode Switching"
    echo ""
    echo "Usage: $0 {normal|update|status|help}"
    echo ""
    echo "Modes:"
    echo "  normal   - Normal mode: LAN scanning + WebUI access (localhost:8834, :8835)"
    echo "  update   - Update mode: VPN plugin updates (no port forwarding)"
    echo "  status   - Show current mode and container status"
    echo "  help     - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 normal    # Switch to normal mode"
    echo "  $0 update    # Switch to update mode"
    echo "  $0 status    # Check current mode"
    echo ""
}

get_current_mode() {
    # Check if mode file exists
    if [[ -f "$MODE_FILE" ]]; then
        cat "$MODE_FILE"
    else
        # Detect mode from running containers
        if docker compose ps nessus-pro-1 2>/dev/null | grep -q "0.0.0.0:8834"; then
            echo "normal"
        elif docker ps --filter "name=nessus-pro-1" --filter "label=nessus.mode=update" --format "{{.Names}}" 2>/dev/null | grep -q "nessus-pro-1"; then
            echo "update"
        else
            echo "unknown"
        fi
    fi
}

show_status() {
    local current_mode=$(get_current_mode)

    echo -e "${BLUE}==============================================================================${NC}"
    echo -e "${BLUE}Nessus Scanner Mode Status${NC}"
    echo -e "${BLUE}==============================================================================${NC}"
    echo ""

    if [[ "$current_mode" == "normal" ]]; then
        echo -e "Current Mode: ${GREEN}NORMAL${NC}"
        echo ""
        echo "Configuration:"
        echo "  ✓ LAN scanning enabled"
        echo "  ✓ WebUI access: https://localhost:8834 (Scanner 1)"
        echo "  ✓ WebUI access: https://localhost:8835 (Scanner 2)"
        echo "  ✗ Plugin updates may fail (port forwarding interference)"
        echo ""
    elif [[ "$current_mode" == "update" ]]; then
        echo -e "Current Mode: ${YELLOW}UPDATE${NC}"
        echo ""
        echo "Configuration:"
        echo "  ✓ Plugin updates via VPN enabled"
        echo "  ✓ LAN scanning enabled"
        echo "  ✗ WebUI NOT accessible from host OS"
        echo "  ✓ MCP access: https://172.30.0.3:8834 (Scanner 1)"
        echo "  ✓ MCP access: https://172.30.0.4:8834 (Scanner 2)"
        echo ""
    else
        echo -e "Current Mode: ${RED}UNKNOWN${NC}"
        echo ""
        echo "Cannot determine current mode. Check container status."
        echo ""
    fi

    echo -e "${BLUE}Container Status:${NC}"
    docker compose ps nessus-pro-1 nessus-pro-2 2>/dev/null || echo "  No containers running"
    echo ""

    echo -e "${BLUE}Mode History:${NC}"
    if [[ -f "$MODE_FILE" ]]; then
        local mode_content=$(cat "$MODE_FILE")
        local mode_time=$(stat -c %y "$MODE_FILE" 2>/dev/null | cut -d'.' -f1)
        echo "  Last switch: $mode_content at $mode_time"
    else
        echo "  No mode history available"
    fi
    echo ""

    echo -e "${BLUE}==============================================================================${NC}"
}

switch_to_normal() {
    local current_mode=$(get_current_mode)

    echo -e "${BLUE}==============================================================================${NC}"
    echo -e "${BLUE}Switching to NORMAL mode${NC}"
    echo -e "${BLUE}==============================================================================${NC}"
    echo ""

    if [[ "$current_mode" == "normal" ]]; then
        echo -e "${YELLOW}Already in NORMAL mode. Nothing to do.${NC}"
        echo ""
        return 0
    fi

    echo "Configuration:"
    echo "  • LAN scanning: ENABLED"
    echo "  • WebUI access: ENABLED (localhost:8834, :8835)"
    echo "  • Plugin updates: May fail due to port forwarding"
    echo ""

    echo -e "${YELLOW}WARNING: Scanners will restart. Running scans will be interrupted.${NC}"
    echo ""
    read -p "Continue? [y/N] " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        return 1
    fi

    echo ""
    echo "Stopping scanners..."
    docker compose stop nessus-pro-1 nessus-pro-2

    echo "Starting in NORMAL mode..."
    docker compose up -d --force-recreate nessus-pro-1 nessus-pro-2

    # Save mode
    echo "normal" > "$MODE_FILE"

    echo ""
    echo -e "${GREEN}✓ Switched to NORMAL mode successfully!${NC}"
    echo ""
    echo "Scanner access:"
    echo "  • Scanner 1 WebUI: https://localhost:8834"
    echo "  • Scanner 2 WebUI: https://localhost:8835"
    echo "  • MCP API access: https://172.30.0.3:8834, https://172.30.0.4:8834"
    echo ""
    echo -e "${BLUE}==============================================================================${NC}"
}

switch_to_update() {
    local current_mode=$(get_current_mode)

    echo -e "${BLUE}==============================================================================${NC}"
    echo -e "${BLUE}Switching to UPDATE mode${NC}"
    echo -e "${BLUE}==============================================================================${NC}"
    echo ""

    if [[ "$current_mode" == "update" ]]; then
        echo -e "${YELLOW}Already in UPDATE mode. Nothing to do.${NC}"
        echo ""
        return 0
    fi

    echo "Configuration:"
    echo "  • LAN scanning: ENABLED"
    echo "  • WebUI access: DISABLED (no port forwarding)"
    echo "  • Plugin updates: ENABLED via VPN"
    echo ""

    echo -e "${YELLOW}WARNING: Scanners will restart. Running scans will be interrupted.${NC}"
    echo -e "${YELLOW}WARNING: WebUI will NOT be accessible from host OS.${NC}"
    echo ""
    read -p "Continue? [y/N] " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        return 1
    fi

    echo ""
    echo "Stopping scanners..."
    docker compose stop nessus-pro-1 nessus-pro-2

    echo "Starting in UPDATE mode..."
    docker compose -f "$BASE_COMPOSE" -f "$UPDATE_OVERRIDE" up -d --force-recreate nessus-pro-1 nessus-pro-2

    # Save mode
    echo "update" > "$MODE_FILE"

    echo ""
    echo -e "${GREEN}✓ Switched to UPDATE mode successfully!${NC}"
    echo ""
    echo "Plugin update instructions:"
    echo "  1. Access MCP worker container:"
    echo "     docker exec -it nessus-mcp-worker-dev bash"
    echo ""
    echo "  2. Use MCP API to trigger plugin updates via:"
    echo "     https://172.30.0.3:8834 (Scanner 1)"
    echo "     https://172.30.0.4:8834 (Scanner 2)"
    echo ""
    echo "  3. Or use debug-scanner to verify VPN connectivity:"
    echo "     docker exec -it debug-scanner sh"
    echo ""
    echo -e "${YELLOW}Note: WebUI is NOT accessible from host OS in this mode${NC}"
    echo ""
    echo -e "${BLUE}==============================================================================${NC}"
}

# =============================================================================
# Main
# =============================================================================

case "${1:-}" in
    normal)
        switch_to_normal
        ;;
    update)
        switch_to_update
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Error: Invalid argument${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
