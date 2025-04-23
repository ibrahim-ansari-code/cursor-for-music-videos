from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/ping", include_in_schema=False)
async def ping():
    """Health check endpoint for Azure App Service health probes."""
    return {"status": "ok"} 