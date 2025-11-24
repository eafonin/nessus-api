#!/bin/bash
# =============================================================================
# Nessus Scanner WebUI Access - Working Solution
# =============================================================================
# This script provides browser access to Nessus scanners by running Firefox
# inside a Docker container on the same network as the scanners.
#
# Why this works: Container-to-container communication bypasses Docker NAT,
# avoiding the TLS handshake timeout issue that affects host-to-container.
# =============================================================================

echo "=========================================="
echo "Nessus Scanner WebUI Access"
echo "=========================================="
echo ""
echo "Starting Firefox in Docker container..."
echo "Firefox will have access to the scanner internal IPs."
echo ""
echo "Scanner URLs:"
echo "  Scanner 1: https://172.30.0.3:8834"
echo "  Scanner 2: https://172.30.0.4:8834"
echo ""
echo "Credentials:"
echo "  Username: nessus"
echo "  Password: nessus"
echo ""
echo "=========================================="
echo ""

# Check if X11 forwarding is available
if [ -z "$DISPLAY" ]; then
    echo "ERROR: DISPLAY variable not set. X11 forwarding required."
    echo "If running via SSH, reconnect with: ssh -X user@host"
    exit 1
fi

# Allow Docker containers to connect to X11
xhost +local:docker 2>/dev/null || echo "Warning: xhost not available"

# Run Firefox in Docker container with access to scanner network
docker run -it --rm \
    --network nessus-shared_vpn_net \
    --name nessus-browser \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    --user $(id -u):$(id -g) \
    jlesage/firefox \
    firefox https://172.30.0.3:8834

# Clean up X11 access
xhost -local:docker 2>/dev/null || true
