from fastapi import APIRouter
from Backend.utils.llm_utils import test_azure_openai_connection

router = APIRouter(tags=["health"])


@router.get("/ping", include_in_schema=False)
async def ping():
    """Health check endpoint for Azure App Service health probes."""
    return {"status": "ok"}


@router.get("/azure-openai")
async def azure_openai_health_check():
    """Health check endpoint for Azure OpenAI service"""
    result = await test_azure_openai_connection()
    return result
