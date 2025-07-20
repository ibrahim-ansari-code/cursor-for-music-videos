"""
Script to register tools with the existing Azure Assistant

Run this script to add the custom function tools to your deployed agent.
This follows the Microsoft documentation pattern for updating an existing agent.
"""
import asyncio
import logging
from Backend.llm.agent_service import BrikliAgentService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def register_tools():
    """Register tools with the Azure Assistant"""
    try:
        logger.info("🚀 Starting tool registration...")
        
        # Initialize the agent service
        agent_service = BrikliAgentService()
        
        # Register tools with the assistant
        updated_agent = agent_service.register_tools_with_assistant()
        
        logger.info("✅ Tools registered successfully!")
        logger.info(f"Agent ID: {updated_agent.id}")
        logger.info(f"Tools registered: {len(updated_agent.tools) if hasattr(updated_agent, 'tools') else 'Unknown'}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to register tools: {str(e)}")
        return False


if __name__ == "__main__":
    success = asyncio.run(register_tools())
    if success:
        print("\n🎉 Tool registration complete! Your agent now has access to:")
        print("   • search_properties - Find and filter properties")  
        print("   • get_tenant_info - Get tenant details and lease info")
        print("   • get_financial_summary - View income and expenses")
        print("   • get_maintenance_requests - Check maintenance status")
        print("   • get_lease_expiry_info - See upcoming lease expirations")
        print("   • get_payment_status - Review payment statuses")
        print("   • search_lease_documents - Search document content (placeholder)")
        print("\nYou can now test the agent with queries like:")
        print('   "Show me all my vacant properties"')
        print('   "What\'s my income this month?"')
        print('   "List all maintenance requests"')
    else:
        print("\n❌ Tool registration failed. Check the logs above for details.") 