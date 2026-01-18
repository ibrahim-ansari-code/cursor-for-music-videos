#!/bin/bash

echo "=== Testing /render_panel directly (simulating Gumloop webhook) ==="
echo ""

cat > /tmp/test_payload.json << 'EOF'
{
  "book_id": "paranorthern",
  "chapter_id": "ch1",
  "panel_id": "p10",
  "character_registry": [
    {
      "character_id": "narrator",
      "name_or_label": "Narrator",
      "voice_requirements": {
        "voice_gender": "neutral",
        "age_range": "adult",
        "pitch": "medium",
        "pacing": "normal",
        "energy": "medium",
        "timbre": "clear",
        "accent_preference": "none"
      }
    }
  ],
  "script_lines": [
    {
      "speaker": "Narrator",
      "text": "This is a test of the audio generation pipeline.",
      "emotion": "calm",
      "intensity_1_to_10": 3,
      "pause_ms_after": 500
    },
    {
      "speaker": "Narrator",
      "text": "If you can hear this, the system is working correctly.",
      "emotion": "neutral",
      "intensity_1_to_10": 2,
      "pause_ms_after": 300
    }
  ]
}
EOF

echo "Sending test payload to /render_panel..."
RESPONSE=$(curl -s -X POST http://localhost:8000/render_panel \
  -H "Content-Type: application/json" \
  -d @/tmp/test_payload.json)

echo "$RESPONSE" | python3 -m json.tool
echo ""

AUDIO_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('audio_id', ''))" 2>/dev/null)

if [ -n "$AUDIO_ID" ] && [ "$AUDIO_ID" != "pending" ]; then
  echo "Audio generated! Audio ID: $AUDIO_ID"
  echo "Access at: http://localhost:8000/audio/$AUDIO_ID.mp3"
  echo "File location:"
  find ./out -name "$AUDIO_ID.mp3" -type f 2>/dev/null
else
  echo "Failed to generate audio"
fi

rm /tmp/test_payload.json
