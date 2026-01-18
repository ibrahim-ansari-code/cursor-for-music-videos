#!/bin/bash
cd /Users/ibrahimansari/Desktop/autoscroll/backend-audio-gen
source ../venv/bin/activate
uvicorn main:app --reload --port 8000 --host 0.0.0.0
