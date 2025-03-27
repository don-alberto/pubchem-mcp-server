"""
PubChem MCP Server

Implements a Model Context Protocol (MCP) server that provides PubChem compound data retrieval functionality.

Note: This module requires the MCP SDK to be installed. Since the MCP SDK may not be publicly available on PyPI,
you may need to install it manually. Please refer to the MCP documentation for how to install the MCP SDK.

If you don't have the MCP SDK installed, you can still use the command line interface (cli.py) to retrieve PubChem data.
"""

import json
import logging
import signal
import sys
import traceback
from typing import Any, Dict, List, Optional, Union

# Try to import MCP SDK, provide a simplified version of the server if not available
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.stdio import stdio_server
    MCP_SDK_AVAILABLE = True
except ImportError as e:
    MCP_SDK_AVAILABLE = False
    print(f"Warning: MCP SDK is not installed, server functionality will not be available. Error: {e}")
    print("You can still use the command line interface (pubchem-mcp) to retrieve PubChem data.")

from .pubchem_api import get_pubchem_data
from .async_processor import get_processor

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Changed to DEBUG for more detailed logging
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class PubChemServer:
    """PubChem MCP Server class"""
    
    def __init__(self):
        """Initialize PubChem MCP server"""
        self.app = FastMCP("pubchem-server", "1.0.0")
        self.setup_tools()
        
        # Error handling
        signal.signal(signal.SIGINT, self.handle_sigint)
    
    def handle_sigint(self, sig, frame):
        """Handle SIGINT signal"""
        logger.info("Received interrupt signal, shutting down server...")
        sys.exit(0)
    
    def setup_tools(self):
        """Set up tools"""
        @self.app.tool("get_pubchem_data")
        async def get_pubchem_data_tool(query: str, format: str = "JSON", include_3d: bool = False):
            """Retrieve compound structure and property data"""
            try:
                # Check if XYZ format requires include_3d parameter
                if format.upper() == "XYZ" and not include_3d:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "When using XYZ format, the include_3d parameter must be set to true",
                            },
                        ],
                        "isError": True,
                    }
                
                result = get_pubchem_data(query, format, include_3d)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": result,
                        },
                    ],
                }
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: {str(e)}",
                        },
                    ],
                    "isError": True,
                }

        @self.app.tool("submit_pubchem_request")
        async def submit_pubchem_request_tool(query: str, format: str = "JSON", include_3d: bool = False):
            """Submit asynchronous request for PubChem data (useful for slower queries)"""
            try:
                # Check if XYZ format requires include_3d parameter
                if format.upper() == "XYZ" and not include_3d:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "When using XYZ format, the include_3d parameter must be set to true",
                            },
                        ],
                        "isError": True,
                    }
                
                # Submit to async processor
                processor = get_processor()
                request_id = processor.submit_request(query, format, include_3d)
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "request_id": request_id,
                                "message": "Request submitted successfully. Use get_request_status with this request_id to check the status."
                            }, indent=2),
                        },
                    ],
                }
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error submitting request: {str(e)}",
                        },
                    ],
                    "isError": True,
                }

        @self.app.tool("get_request_status")
        async def get_request_status_tool(request_id: str):
            """Get status of an asynchronous PubChem data request"""
            try:
                processor = get_processor()
                status = processor.get_status(request_id)
                
                if status is None:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Request ID not found: {request_id}",
                            },
                        ],
                        "isError": True,
                    }
                
                # Return status
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(status, indent=2),
                        },
                    ],
                }
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error getting request status: {str(e)}",
                        },
                    ],
                    "isError": True,
                }
    
    def run(self):
        """Run the server"""
        # Initialize processor
        get_processor()
        
        # Run the server using FastMCP's run method
        self.app.run()
        logger.info("PubChem MCP server running on stdio")


def main():
    """Main function"""
    if not MCP_SDK_AVAILABLE:
        print("Error: MCP SDK is not installed, cannot start server.")
        print("Please install the MCP SDK and try again, or use the command line interface (pubchem-mcp) to retrieve PubChem data.")
        
        # Instead of exiting, try to run the command line interface
        from .cli import main as cli_main
        print("Falling back to command line interface...")
        cli_main()
        return
    
    # Set logging level
    logging.basicConfig(level=logging.DEBUG)  # Changed to DEBUG for more detailed logging
    
    try:
        # Create and run server
        server = PubChemServer()
        server.run()
    except Exception as e:
        print(f"Error starting server: {e}")
        print("Full traceback:")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Shutdown processor if server closes
        try:
            processor = get_processor()
            processor.shutdown()
        except Exception as e:
            print(f"Error during processor shutdown: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
