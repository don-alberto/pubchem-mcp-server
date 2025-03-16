#!/usr/bin/env python3
"""
Minimal PubChem MCP Server

A simplified version of the PubChem MCP server that focuses only on connection stability.
"""

import json
import sys
import logging
import traceback
import signal
from typing import Dict, Any

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Handle interrupt signals
def signal_handler(sig, frame):
    """Handle interrupt signals"""
    logger.info("Received interrupt signal, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def main():
    """Main function"""
    logger.info("Starting minimal PubChem MCP server")
    
    while True:
        try:
            # Read a line from stdin
            line = sys.stdin.readline()
            if not line:
                logger.info("End of input, exiting")
                break
            
            # Parse JSON request
            try:
                request = json.loads(line)
                logger.info(f"Received request: {request.get('method')}")
                
                # Extract key fields
                request_id = request.get("id")
                method = request.get("method")
                
                # Handle different requests
                response = None
                
                if method == "initialize":
                    # Basic initialize response
                    response = {
                        "id": request_id,
                        "result": {
                            "name": "pubchem-minimal-server",
                            "version": "1.0.0",
                            "capabilities": {
                                "tools": {}
                            }
                        }
                    }
                elif method == "list_tools":
                    # Return a single simple tool
                    response = {
                        "id": request_id,
                        "result": {
                            "tools": [
                                {
                                    "name": "hello_world",
                                    "description": "A simple hello world function",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "Your name",
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }
                elif method == "call_tool":
                    # Handle tool call - just echo back a greeting
                    tool_name = request.get("params", {}).get("name")
                    arguments = request.get("params", {}).get("arguments", {})
                    
                    if tool_name == "hello_world":
                        name = arguments.get("name", "World")
                        response = {
                            "id": request_id,
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"Hello, {name}!"
                                    }
                                ]
                            }
                        }
                    else:
                        response = {
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {tool_name}"
                            }
                        }
                else:
                    # Unknown method
                    response = {
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                
                # Send response
                if response:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
                    logger.info(f"Sent response for {method}")
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON: {line}")
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.error(traceback.format_exc())
    
    logger.info("Server exited")

if __name__ == "__main__":
    main()
