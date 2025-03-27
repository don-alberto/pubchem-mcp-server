# PubChem MCP Server (Python Version)

> This project is a fork of [PhelanShao/pubchem-mcp-server](https://github.com/PhelanShao/pubchem-mcp-server), enhanced with additional transport options and Docker support.

This is a Python implementation of a Model Context Protocol (MCP) server that provides PubChem compound data retrieval functionality.

## Features

- Retrieve compound data using compound names or PubChem CID
- Support for multiple output formats: JSON, CSV, and XYZ
- Support for 3D structure data retrieval (XYZ format)
- Multiple transport options: stdio and SSE
- Docker support for containerized deployment
- Provides both command-line interface and MCP server interface

## Installation

### Basic Installation

```bash
# Install from source
git clone https://github.com/yourusername/pubchem-mcp-server.git
cd pubchem-mcp-server
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

### Docker Installation

```bash
# Build the Docker image
docker build -t pubchem-mcp-server .

# Run the container with SSE transport
docker run -p 8000:8000 pubchem-mcp-server
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

The server supports two transport modes: stdio and SSE.

#### stdio Transport

1. Start the server:
```bash
python -m pubchem_mcp_server.server
```

2. Add the server to your MCP configuration:
```json
{
  "mcpServers": {
    "pubchem": {
      "command": "python",
      "args": ["-m", "pubchem_mcp_server.server"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

#### SSE Transport

1. Start the server with SSE transport:
```bash
# Direct
python -m pubchem_mcp_server.server --transport sse

# Or using Docker
docker run -p 8000:8000 pubchem-mcp-server
```

2. Add the server to your MCP configuration:
```json
{
  "mcpServers": {
    "pubchem": {
      "transport": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

## API

### Main Functions

- `get_pubchem_data(query, format='JSON', include_3d=False)`: Retrieve PubChem compound data
- `get_xyz_structure(cid, smiles, compound_info)`: Get compound 3D structure in XYZ format

## Dependencies

- Python >= 3.10
- requests >= 2.25.0
- MCP SDK (required for server functionality)
- starlette >= 0.27.0 (for SSE transport)
- uvicorn >= 0.23.0 (for SSE transport)
- rdkit >= 2022.9.1 (optional, for enhanced 3D structure generation)

### About MCP SDK

The MCP SDK is a software development kit for the Model Context Protocol, used to create MCP servers. Since the MCP SDK might not be publicly available on PyPI, you may need to install it manually. If you only want to use the command-line interface to retrieve PubChem data, you don't need to install the MCP SDK.

## License

MIT

## Acknowledgments

- This project is forked from [PhelanShao/pubchem-mcp-server](https://github.com/PhelanShao/pubchem-mcp-server)
- PubChem data is provided by the National Center for Biotechnology Information (NCBI)
