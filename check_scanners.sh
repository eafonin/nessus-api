#!/bin/bash

echo "======================================================================"
echo "COMPARING SCANNER CONFIGURATIONS"
echo "======================================================================"
echo ""

echo "Scanner 1 (nessus-pro-1) - WORKING:"
echo "----------------------------------------------------------------------"
echo "Registration Status:"
docker exec nessus-pro-1 /opt/nessus/sbin/nessuscli fetch --check 2>&1
echo ""

echo ""
echo "Scanner 2 (nessus-pro-2) - NOT WORKING:"
echo "----------------------------------------------------------------------"
echo "Registration Status:"
docker exec nessus-pro-2 /opt/nessus/sbin/nessuscli fetch --check 2>&1
echo ""

echo ""
echo "======================================================================"
echo "ACTIVATION CODE CHECK"
echo "======================================================================"
cd /home/nessus/docker/nessus-shared
grep -A 2 "ACTIVATION_CODE" docker-compose.yml | grep -E "(nessus-pro-1|nessus-pro-2)" -A 2
