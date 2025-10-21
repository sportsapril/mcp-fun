#!/usr/bin/env python3

import json
import os
from typing import Any, Dict, List, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import Resource, TextContent, Tool

# Initialize FastMCP server
mcp = FastMCP("dataset-analysis")

class DatasetViewerAPI:
    BASE_URL = "https://datasets-server.huggingface.co"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("HF_TOKEN")
        self.client = httpx.AsyncClient()
        self._cache: Dict[str, Any] = {}

    def _get_headers(self) -> Dict[str, str]:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{endpoint}"
        response = await self.client.get(url, params=params, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def validate_dataset(self, dataset: str) -> bool:
        try:
            await self._make_request("is-valid", {"dataset": dataset})
            return True
        except:
            return False

    async def get_dataset_info(self, dataset: str, config: Optional[str] = None) -> Dict[str, Any]:
        params = {"dataset": dataset}
        if config:
            params["config"] = config
        return await self._make_request("info", params)

api = DatasetViewerAPI()

# Add resources
@mcp.resource("dataset://info")
async def dataset_info_resource() -> str:
    return "This MCP server provides access to Hugging Face datasets through the Dataset Viewer API. Use the available tools to explore, search, and analyze datasets."

# Add tools
@mcp.tool()
async def validate(dataset: str) -> str:
    """Check if a dataset is accessible

    Args:
        dataset: Dataset name (e.g., 'squad', 'microsoft/DialoGPT-medium')
    """
    is_valid = await api.validate_dataset(dataset)
    return f"Dataset '{dataset}' is {'valid' if is_valid else 'invalid'}"

@mcp.tool()
async def get_info(dataset: str, config: Optional[str] = None) -> str:
    """Get comprehensive information about a dataset

    Args:
        dataset: Dataset name
        config: Dataset configuration name (optional)
    """
    info = await api.get_dataset_info(dataset, config)
    return json.dumps(info, indent=2)

# Add prompts
@mcp.prompt()
async def analyze_dataset(dataset: str, config: Optional[str] = None, split: Optional[str] = None) -> str:
    """Get a comprehensive analysis of a dataset including structure, statistics, and sample data

    Args:
        dataset: Dataset name to analyze
        config: Dataset configuration (optional)
        split: Dataset split to analyze (optional)
    """

    prompt_parts = [
        f"Please provide a comprehensive analysis of the dataset '{dataset}'.",
        "Include the following information:",
        "1. Dataset structure and schema",
        "2. Available configurations and splits",
        "3. Statistical summary of the data",
        "4. Sample rows from the dataset",
        "5. Data types and format information"
    ]

    if config:
        prompt_parts.append(f"Focus on configuration: {config}")
    if split:
        prompt_parts.append(f"Focus on split: {split}")

    return "\n".join(prompt_parts)

if __name__ == "__main__":
    mcp.run()