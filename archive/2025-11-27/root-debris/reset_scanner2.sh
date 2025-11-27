#!/bin/bash

echo "======================================================================"
echo "RESETTING SCANNER 2 FOR PROPER ACTIVATION"
echo "======================================================================"
echo ""

cd /home/nessus/docker/nessus-shared || exit 1

echo "Step 1: Stopping Scanner 2..."
docker compose stop nessus-pro-2
echo "✓ Stopped"
echo ""

echo "Step 2: Removing container..."
docker compose rm -f nessus-pro-2
echo "✓ Container removed"
echo ""

echo "Step 3: Removing old volume (nessus_data_2)..."
docker volume rm nessus_data_2 2>&1
echo "✓ Volume removed (or didn't exist)"
echo ""

echo "Step 4: Creating fresh Scanner 2 with activation code..."
echo "  Activation Code: YGHZ-GELQ-RNZX-QSSH-4XD5"
docker compose up -d nessus-pro-2
echo "✓ Scanner 2 started"
echo ""

echo "Step 5: Waiting for scanner to initialize (60 seconds)..."
sleep 60
echo ""

echo "Step 6: Checking initialization status..."
docker logs nessus-pro-2 --tail 30
echo ""

echo "======================================================================"
echo "Scanner 2 has been reset and is initializing with activation code"
echo "Please wait 5-10 minutes for plugin download to complete"
echo "======================================================================"
