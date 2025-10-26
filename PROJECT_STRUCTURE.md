# Project Structure

Clean organization of the mcp-fun repository.

## Root Directory

```
mcp-fun/
├── CLAUDE.md                      # Project instructions for Claude Code
├── README.md                      # Main project README
├── TRIPADVISOR_MCP_SETUP.md       # Quick setup guide for TripAdvisor MCP
├── pyproject.toml                 # Python package configuration
├── add_city_to_csv.py             # Helper script to add cities to CSV database
├── twitter_invoice_downloader.py  # Standalone Twitter invoice CLI tool
├── prepare_dataset.ipynb          # Jupyter notebook for dataset work
│
├── src/                           # Source code
│   ├── dataset_analysis/          # Dataset Analysis MCP server
│   ├── tripadvisor_mcp/          # TripAdvisor MCP server
│   └── twitter_invoice_mcp/      # Twitter Invoice MCP server
│
├── data/                          # Data files
│   └── tripadvisor_geo_map/      # City-to-geoID CSV mappings
│       ├── usa.csv               # 294 US cities
│       └── world.csv             # 982 worldwide cities
│
├── docs/                          # Documentation
│   ├── README.md                 # Documentation index
│   ├── FIX_CLAUDE_DESKTOP_INTEGRATION.md
│   ├── GMAIL_MCP_SETUP.md
│   ├── INVOICE_DOWNLOADER_README.md
│   ├── LLM_MATCHING_SUCCESS.md
│   └── archive/                  # Historical docs from development
│
└── tests/                         # Test scripts
    ├── README.md                 # Test documentation
    ├── test_llm_matching.py      # LLM bilingual matching tests
    └── test_mcp_directly.py      # Direct MCP tool tests
```

## Key Files

### Root Level
- **CLAUDE.md**: Instructions for Claude Code when working in this repo
- **TRIPADVISOR_MCP_SETUP.md**: Setup guide for integrating TripAdvisor MCP with Claude Desktop
- **pyproject.toml**: Package metadata and dependencies
- **add_city_to_csv.py**: Utility to manually add cities to the geo mapping database

### Source Code (src/)
Three MCP servers:
1. **tripadvisor_mcp**: Search TripAdvisor China with bilingual support
2. **twitter_invoice_mcp**: Automate Twitter invoice downloads
3. **dataset_analysis**: Analyze Hugging Face datasets

### Data (data/)
- **tripadvisor_geo_map/**: CSV files mapping city names to TripAdvisor geo IDs
  - 294 US cities (usa.csv)
  - 982 worldwide cities (world.csv)

### Documentation (docs/)
- **Main docs**: Setup guides and technical details
- **archive/**: Historical development notes (kept for reference)

### Tests (tests/)
- **test_llm_matching.py**: Tests 12 city name variations (Chinese, English, abbreviations)
- **test_mcp_directly.py**: Direct function call tests to verify MCP tool

## Cleaned Up

The following were removed during cleanup:
- 25+ debug/test Python files (debug_*.py, test_*.py, find_*.py, etc.)
- Duplicate documentation files
- Temporary investigation notes

Useful test files were moved to `tests/`, and documentation was organized into `docs/` with an archive for historical reference.
