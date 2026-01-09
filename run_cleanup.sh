#!/usr/bin/env bash
# -------------------------
# Audio cleanup script
# Removes virtual mix sink and loopback
# -------------------------

# Load environment variables from .env
ENV_FILE="$(dirname "$0")/.env"

if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo ".env not found in $(dirname "$0")!"
    exit 1
fi

# Load module IDs
if [ -f /tmp/mix_module_id.txt ]; then
    MIX_MODULE_ID=$(cat /tmp/mix_module_id.txt)
    echo "Unloading virtual sink module id $MIX_MODULE_ID"
    pactl unload-module $MIX_MODULE_ID
    rm /tmp/mix_module_id.txt
fi

if [ -f /tmp/loopback_module_id.txt ]; then
    LOOPBACK_MODULE_ID=$(cat /tmp/loopback_module_id.txt)
    echo "Unloading loopback module id $LOOPBACK_MODULE_ID"
    pactl unload-module $LOOPBACK_MODULE_ID
    rm /tmp/loopback_module_id.txt
fi

sudo killall mpv

echo "✅ Audio cleanup complete!"
