#!/bin/bash

echo "======================================================================"
echo "DEBUG SCANNER CONNECTIVITY TEST"
echo "======================================================================"
echo ""

echo "STEP 1: Fix Routing"
echo "----------------------------------------------------------------------"
echo "Current routing:"
docker exec debug-scanner cat /proc/net/route | head -4
echo ""

echo "Fixing default route to use VPN gateway (172.30.0.2)..."
docker exec debug-scanner sh -c "ip route del default 2>/dev/null || true; ip route add default via 172.30.0.2 dev eth1"
echo ""
echo "New routing:"
docker exec debug-scanner ip route show
echo ""

echo "======================================================================"
echo "STEP 2: Test DNS Resolution"
echo "======================================================================"
echo ""

echo "Resolving google.com:"
docker exec debug-scanner nslookup google.com 172.30.0.2
echo ""

echo "Resolving plugins.nessus.org:"
docker exec debug-scanner nslookup plugins.nessus.org 172.30.0.2
echo ""

echo "======================================================================"
echo "STEP 3: Get External IP Address"
echo "======================================================================"
echo ""

echo "Checking external IP via ifconfig.me:"
docker exec debug-scanner curl -s --connect-timeout 10 ifconfig.me
echo ""
echo ""

echo "Checking external IP via ipinfo.io:"
docker exec debug-scanner curl -s --connect-timeout 10 ipinfo.io/ip
echo ""
echo ""

echo "======================================================================"
echo "STEP 4: Test Internet Connectivity"
echo "======================================================================"
echo ""

echo "Ping Google DNS (8.8.8.8):"
docker exec debug-scanner ping -c 3 8.8.8.8
echo ""

echo "Curl to Google:"
docker exec debug-scanner curl -sI --connect-timeout 10 https://www.google.com | head -5
echo ""

echo "Curl to plugins.nessus.org:"
docker exec debug-scanner curl -sI --connect-timeout 10 https://plugins.nessus.org | head -5
echo ""

echo "======================================================================"
echo "STEP 5: Test HTTPS Certificate Validation"
echo "======================================================================"
echo ""

echo "Full curl test to plugins.nessus.org (verbose):"
docker exec debug-scanner curl -v --connect-timeout 10 https://plugins.nessus.org 2>&1 | head -30
echo ""

echo "======================================================================"
echo "RESULTS SUMMARY"
echo "======================================================================"
