# PubChem MCP Server (Python Version)

This is a Python implementation of a Model Context Protocol (MCP) server that provides PubChem compound data retrieval functionality.

## Features

- Retrieve compound data using compound names or PubChem CID
- Support for multiple output formats: JSON, CSV, and XYZ
- Support for 3D structure data retrieval (XYZ format)
- Provides both command-line interface and MCP server interface

## Installation

### Basic Installation

```bash
# Install from source
git clone https://github.com/yourusername/pubchem-mcp-server.git
cd pubchem-mcp-server/python_version
pip install .

# Or install directly from PyPI (if published)
pip install pubchem-mcp-server
```

### Installing RDKit Support (Optional)

RDKit is used to enhance 3D structure generation capabilities but is not required:

```bash
pip install "pubchem-mcp-server[rdkit]"
```

Alternatively, you can install RDKit separately:

```bash
conda install -c conda-forge rdkit
# or
pip install rdkit
```

## Usage

### Command Line Interface

```bash
# Basic usage
pubchem-mcp aspirin

# Specify output format
pubchem-mcp aspirin --format CSV

# Get 3D structure (XYZ format)
pubchem-mcp aspirin --format XYZ --include-3d

# View help
pubchem-mcp --help
```

### As an MCP Server

1. Start the server:

```bash
pubchem-mcp-server
```

2. Add the server to your MCP configuration file (typically located at `~/.claude-dev/settings/cline_mcp_settings.json` or `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pubchem": {
      "command": "python",
      "args": ["-m", "pubchem_mcp_server.server"],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

3. Restart your Claude application or Claude development environment, and you'll be able to use the PubChem MCP tools.

## API

### Main Functions

- `get_pubchem_data(query, format='JSON', include_3d=False)`: Retrieve PubChem compound data
- `get_xyz_structure(cid, smiles, compound_info)`: Get compound 3D structure in XYZ format

## Dependencies

- Python >= 3.8
- requests >= 2.25.0
- MCP SDK (optional, for MCP server functionality)
- rdkit >= 2022.9.1 (optional, for enhanced 3D structure generation)

### About MCP SDK

The MCP SDK is a software development kit for the Model Context Protocol, used to create MCP servers. Since the MCP SDK might not be publicly available on PyPI, you may need to install it manually. If you only want to use the command-line interface to retrieve PubChem data, you don't need to install the MCP SDK.

## License

MIT

## Acknowledgments

- PubChem data is provided by the National Center for Biotechnology Information (NCBI)
- Reimplemented based on the original TypeScript version of the PubChem MCP server
