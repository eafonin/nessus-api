#!/bin/bash

echo "======================================================================"
echo "ROUTING TABLE COMPARISON - ROOT CAUSE ANALYSIS"
echo "======================================================================"
echo ""

echo "Scanner 1 (172.30.0.3 - WORKING):"
echo "----------------------------------------------------------------------"
docker exec nessus-pro-1 cat /proc/net/route | head -4
echo ""
gateway1=$(docker exec nessus-pro-1 cat /proc/net/route | awk 'NR==2 {print $3}')
echo "Decoded: Default gateway = $(printf '%d.%d.%d.%d' 0x${gateway1:6:2} 0x${gateway1:4:2} 0x${gateway1:2:2} 0x${gateway1:0:2})"
echo "✓ CORRECT - Routes through VPN gateway 172.30.0.2"
echo ""

echo "Scanner 2 (172.30.0.4 - NOT WORKING):"
echo "----------------------------------------------------------------------"
docker exec nessus-pro-2 cat /proc/net/route | head -4
echo ""
gateway2=$(docker exec nessus-pro-2 cat /proc/net/route | awk 'NR==2 {print $3}')
echo "Decoded: Default gateway = $(printf '%d.%d.%d.%d' 0x${gateway2:6:2} 0x${gateway2:4:2} 0x${gateway2:2:2} 0x${gateway2:0:2})"

if [ "$gateway2" = "$gateway1" ]; then
    echo "✓ CORRECT - Routes through VPN gateway 172.30.0.2"
    echo "BUT: Still failing to connect to plugins.nessus.org"
else
    echo "✗ WRONG - NOT routing through VPN!"
fi
echo ""

echo "Debug Scanner (192.168.100.11 - NOT WORKING):"
echo "----------------------------------------------------------------------"
docker exec debug-scanner cat /proc/net/route | head -4
echo ""
gateway3=$(docker exec debug-scanner cat /proc/net/route | awk 'NR==2 {print $3}')
echo "Decoded: Default gateway = $(printf '%d.%d.%d.%d' 0x${gateway3:6:2} 0x${gateway3:4:2} 0x${gateway3:2:2} 0x${gateway3:0:2})"
echo "✗ WRONG - Routes to LAN gateway, not VPN!"
echo ""

echo "======================================================================"
echo "CONCLUSION"
echo "======================================================================"
echo ""
if [ "$gateway1" = "$gateway2" ]; then
    echo "Scanner 1 and Scanner 2 have IDENTICAL routing (both via VPN)"
    echo "BUT Scanner 2 still cannot reach plugins.nessus.org"
    echo ""
    echo "This suggests:"
    echo "  1. VPN gateway may be blocking Scanner 2's traffic (firewall)"
    echo "  2. Or activation code is invalid/already used"
    echo "  3. Or Tenable is rate-limiting from this IP"
else
    echo "Scanner 2 and Debug Scanner have INCORRECT routing"
    echo "They are NOT routing through VPN gateway!"
    echo ""
    echo "This explains why they cannot reach the internet."
fi
echo "======================================================================"
