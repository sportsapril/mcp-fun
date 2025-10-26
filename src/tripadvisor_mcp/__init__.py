"""TripAdvisor MCP Server for travel search and recommendations."""

__version__ = "0.1.0"


def main_entry():
    """Entry point for the tripadvisor-mcp command."""
    import asyncio
    from .server import main

    asyncio.run(main())
