import asyncio
import logging
from mcp.server.fastmcp import FastMCP

# Import the sub-modules to register their tools
from nano_mcp_suite import auditor, rfp_parser, a2a_router, exo_moonshots, omni_sandbox, leviathan_broker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nano-mcp-suite")

def main():
    # Create the master server that aggregates all tools
    master_mcp = FastMCP("nano-empire-suite")
    
    # Mount tools from sub-servers
    for tool in auditor.mcp._tool_manager._tools.values():
        master_mcp._tool_manager._tools[tool.name] = tool
        
    for tool in rfp_parser.mcp._tool_manager._tools.values():
        master_mcp._tool_manager._tools[tool.name] = tool
        
    for tool in a2a_router.mcp._tool_manager._tools.values():
        master_mcp._tool_manager._tools[tool.name] = tool
        
    for tool in exo_moonshots.mcp._tool_manager._tools.values():
        master_mcp._tool_manager._tools[tool.name] = tool
        
    for tool in omni_sandbox.mcp._tool_manager._tools.values():
        master_mcp._tool_manager._tools[tool.name] = tool
        
    for tool in leviathan_broker.mcp._tool_manager._tools.values():
        master_mcp._tool_manager._tools[tool.name] = tool

    logger.info("Starting Nano Empire MCP Suite (Auditor + RFP + A2A + OmniSandbox)")
    master_mcp.run()

if __name__ == "__main__":
    main()
