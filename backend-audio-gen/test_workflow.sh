#!/bin/bash

echo "=== Testing Full Workflow ==="
echo ""

IMAGE_URL="https://stephaniecooke.ca/wp-content/uploads/2024/06/paranorthern-page-10.png"
BOOK_ID="paranorthern"
CHAPTER_ID="ch1"
PANEL_ID="p10"

echo "1. Sending image URL to Gumloop..."
RESPONSE=$(curl -s -X POST http://localhost:8000/render_from_url \
  -F "image_url=$IMAGE_URL" \
  -F "book_id=$BOOK_ID" \
  -F "chapter_id=$CHAPTER_ID" \
  -F "panel_id=$PANEL_ID")

echo "$RESPONSE" | python3 -m json.tool
echo ""

RUN_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('message', '').split('Run ID: ')[1].split('.')[0] if 'Run ID:' in json.load(sys.stdin).get('message', '') else '')" 2>/dev/null)

if [ -n "$RUN_ID" ]; then
  echo "2. Pipeline started with Run ID: $RUN_ID"
  echo "   Waiting for Gumloop webhook..."
  echo "   Monitor logs: tail -f /tmp/uvicorn.log"
  echo ""
  echo "3. Check Gumloop status:"
  echo "   https://gumloop.com/pipeline?run_id=$RUN_ID&workbook_id=svQNohf2oAbywNFpgjjF8Q"
  echo ""
  echo "4. When webhook arrives, check for audio:"
  echo "   find ./out -name '*.mp3' -type f -newer /tmp/uvicorn.log 2>/dev/null"
else
  echo "Failed to get Run ID from response"
fi
