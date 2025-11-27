#!/bin/bash

echo "======================================================================"
echo "TESTING INTERNET CONNECTIVITY FROM VPN GATEWAY"
echo "======================================================================"
echo ""
echo "VPN Gateway should have working internet since it's the VPN endpoint"
echo ""

echo "STEP 1: Get External IP Address"
echo "----------------------------------------------------------------------"
docker exec vpn-gateway-shared wget -qO- ifconfig.me 2>&1
echo ""
echo ""

echo "STEP 2: Test DNS Resolution"
echo "----------------------------------------------------------------------"
echo "Resolving google.com:"
docker exec vpn-gateway-shared nslookup google.com 2>&1
echo ""

echo "Resolving plugins.nessus.org:"
docker exec vpn-gateway-shared nslookup plugins.nessus.org 2>&1
echo ""

echo "STEP 3: Test HTTPS Connectivity"
echo "----------------------------------------------------------------------"
echo "Testing connection to plugins.nessus.org:"
docker exec vpn-gateway-shared sh -c "wget --spider -S https://plugins.nessus.org 2>&1" | head -20
echo ""

echo "Testing connection to google.com:"
docker exec vpn-gateway-shared sh -c "wget --spider -S https://www.google.com 2>&1" | head -10
echo ""

echo "======================================================================"
echo ""
echo "Now let's create a PROPER debug scanner with pre-installed tools"
echo ""
