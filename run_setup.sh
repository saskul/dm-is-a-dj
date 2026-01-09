#!/usr/bin/env bash
# -------------------------
# Audio setup script
# Creates virtual mix sink and routes it to physical speakers
# -------------------------

# Load environment variables from .env
if [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
else
    echo ".env not found!"
    exit 1
fi

# Default names if not in .env
MIX_SINK_NAME=${MIX_SINK_NAME:-mixout}
SPEAKER_SINK=${SPEAKER_SINK:-alsa_output.pci-0000_00_1f.3.analog-stereo}

echo "Setting up virtual mix sink '$MIX_SINK_NAME' → physical sink '$SPEAKER_SINK'"

# 1️⃣ Create virtual null sink
MIX_MODULE_ID=$(pactl load-module module-null-sink sink_name=$MIX_SINK_NAME)
echo "Created virtual sink: $MIX_SINK_NAME (module id $MIX_MODULE_ID)"

# 2️⃣ Create loopback: mixout.monitor → physical speaker
LOOPBACK_MODULE_ID=$(pactl load-module module-loopback source=${MIX_SINK_NAME}.monitor sink=$SPEAKER_SINK latency_msec=10)
echo "Created loopback to speakers (module id $LOOPBACK_MODULE_ID)"

# Optional: store module IDs for cleanup
echo $MIX_MODULE_ID > /tmp/mix_module_id.txt
echo $LOOPBACK_MODULE_ID > /tmp/loopback_module_id.txt

echo "✅ Audio setup complete!"
