# Dataset Analysis MCP Server

An MCP (Model Context Protocol) server for analyzing datasets using the Hugging Face Dataset Viewer API. This server provides comprehensive tools for exploring, searching, and analyzing datasets from the Hugging Face Hub.

## Features

- **Dataset Validation**: Check if datasets are accessible
- **Dataset Information**: Get comprehensive metadata and structure
- **Data Retrieval**: Fetch paginated rows from datasets
- **Search**: Full-text search within datasets
- **Filtering**: SQL-like filtering capabilities
- **Statistics**: Get statistical information about datasets
- **Export**: Access Parquet file URLs for downloads

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd mcp-fun
```

2. Install dependencies using `uv` (recommended) or `pip`:
```bash
uv install
# or
pip install -e .
```

## Usage

### Running the Server

```bash
dataset-analysis
```

### Authentication (Optional)

For private datasets, set your Hugging Face token:
```bash
export HF_TOKEN=your_hugging_face_token_here
```

### Available Tools

1. **validate** - Check dataset accessibility
2. **get_info** - Get dataset metadata and structure
3. **get_rows** - Retrieve paginated dataset rows
4. **search_dataset** - Search for content within datasets
5. **filter** - Apply SQL-like filters to datasets
6. **get_statistics** - Get statistical information
7. **get_parquet** - Get Parquet download URLs

### Example Usage with Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "dataset-analysis": {
      "command": "dataset-analysis"
    }
  }
}
```

### Available Prompts

- **analyze_dataset** - Comprehensive dataset analysis
- **explore_dataset** - Quick dataset exploration

## Requirements

- Python 3.12+
- Dependencies: `mcp>=1.1.2`, `httpx>=0.28.1`

## Examples

### Basic Dataset Info
```
Use the get_info tool with dataset="squad" to get information about the SQuAD dataset.
```

### Search Dataset
```
Use the search_dataset tool with dataset="squad" and query="machine learning" to find relevant entries.
```

### Filter Dataset
```
Use the filter tool with dataset="squad" and where="length(question) > 50" to find longer questions.
```