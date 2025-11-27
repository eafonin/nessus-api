#!/bin/bash

echo "======================================================================"
echo "ISSUE 2: Testing Target Host 172.32.0.215 Connectivity"
echo "======================================================================"
echo ""
echo "Testing ICMP (ping):"
ping -c 3 172.32.0.215 2>&1
echo ""
echo "Testing SSH port 22:"
timeout 5 nc -zv 172.32.0.215 22 2>&1 || echo "  SSH port 22 not reachable"
echo ""
echo "Testing common ports:"
for port in 22 80 443 3389 8080; do
    result=$(timeout 2 nc -zv 172.32.0.215 $port 2>&1)
    if echo "$result" | grep -q "succeeded"; then
        echo "  Port $port: OPEN"
    else
        echo "  Port $port: closed/filtered"
    fi
done
