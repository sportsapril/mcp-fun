import asyncio
from .server import mcp

def run_fastmcp():
    mcp.run()

__all__ = ["main"]

def main():
    run_fastmcp()

def main_entry():
    run_fastmcp()

if __name__ == "__main__":
    main_entry()