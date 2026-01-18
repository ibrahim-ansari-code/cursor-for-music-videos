#!/bin/bash

echo "=== Audio Files ==="
echo ""

echo "All audio files:"
find ./out -name "*.mp3" -type f -exec ls -lh {} \; 2>/dev/null | awk '{print $9, "(" $5 ")"}'

echo ""
echo "Audio IDs:"
find ./out -name "*.mp3" -type f -exec basename {} .mp3 \; 2>/dev/null

echo ""
echo "To access via API:"
echo "  http://localhost:8000/audio/<audio_id>.mp3"
echo ""
echo "Example:"
AUDIO_ID=$(find ./out -name "*.mp3" -type f -exec basename {} .mp3 \; 2>/dev/null | head -1)
if [ ! -z "$AUDIO_ID" ]; then
    echo "  http://localhost:8000/audio/$AUDIO_ID.mp3"
fi
