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
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
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
        
        # Initialize SSE transport
        self.sse = SseServerTransport("/messages")
    
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

    async def handle_sse(self, scope, receive, send):
        """Handle SSE connection"""
        async with self.sse.connect_sse(scope, receive, send) as streams:
            await self.app.run(streams[0], streams[1], self.app.create_initialization_options())

    async def handle_messages(self, scope, receive, send):
        """Handle SSE messages"""
        await self.sse.handle_post_message(scope, receive, send)
    
    def create_starlette_app(self):
        """Create Starlette app with SSE routes"""
        return Starlette(
            routes=[
                Route("/sse", endpoint=self.handle_sse),
                Route("/messages", endpoint=self.handle_messages, methods=["POST"]),
            ]
        )
    
    def run(self, transport="stdio", host="0.0.0.0", port=8000):
        """Run the server with specified transport

        Args:
            transport (str): Transport type ('stdio' or 'sse')
            host (str): Host to bind to when using SSE transport
            port (int): Port to listen on when using SSE transport
        """
        # Initialize processor
        get_processor()
        
        if transport == "stdio":
            # Run with stdio transport
            self.app.run()
            logger.info("PubChem MCP server running on stdio")
        elif transport == "sse":
            # Create and run Starlette app for SSE
            import uvicorn
            app = self.create_starlette_app()
            logger.info(f"PubChem MCP server starting on SSE (http://{host}:{port}/sse)")
            uvicorn.run(app, host=host, port=port)
        else:
            raise ValueError(f"Unsupported transport: {transport}")


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
    logging.basicConfig(level=logging.DEBUG)
    
    try:
        import argparse
        parser = argparse.ArgumentParser(description='PubChem MCP Server')
        parser.add_argument('--transport', default='stdio', choices=['stdio', 'sse'],
                          help='Transport type (stdio or sse)')
        parser.add_argument('--host', default='0.0.0.0',
                          help='Host to bind to when using SSE transport')
        parser.add_argument('--port', type=int, default=8000,
                          help='Port to listen on when using SSE transport')
        args = parser.parse_args()
        
        # Create and run server
        server = PubChemServer()
        server.run(transport=args.transport, host=args.host, port=args.port)
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
