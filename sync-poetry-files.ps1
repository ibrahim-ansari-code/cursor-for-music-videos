# PowerShell script to sync poetry files from root to Backend directory
# Run this before deploying to Porter

Write-Host "Syncing Poetry files to Backend directory for Docker build..."
Copy-Item -Path pyproject.toml -Destination Backend/ -Force
Copy-Item -Path poetry.lock -Destination Backend/ -Force
Write-Host "Done! Poetry files are now in sync and ready for deployment." 