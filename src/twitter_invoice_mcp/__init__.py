"""Twitter Developer Portal Invoice MCP Server"""

from .server import main

__all__ = ["main"]


def main_entry():
    """Entry point for the MCP server"""
    import asyncio
    asyncio.run(main())
