"""Gmail MCP Server - Secure Gmail integration for Claude Desktop"""

__version__ = "0.1.0"


def main_entry():
    """Entry point for gmail-mcp command"""
    import asyncio
    from .server import main
    asyncio.run(main())
