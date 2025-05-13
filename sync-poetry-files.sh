#!/bin/bash
# Shell script to sync poetry files from root to Backend directory
# Run this before deploying to Porter

echo "Syncing Poetry files to Backend directory for Docker build..."
cp pyproject.toml Backend/
cp poetry.lock Backend/
echo "Done! Poetry files are now in sync and ready for deployment." 