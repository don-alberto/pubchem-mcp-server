#!/usr/bin/env python3
"""
PubChem Integrated MCP Server

Combines a stable MCP server implementation with the asynchronous processing for PubChem API calls.
"""

import json
import sys
import logging
import traceback
import signal
import os
import time
from typing import Dict, Any, Optional, List

# Configure logging
log_dir = os.path.expanduser("~/.pubchem-mcp")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "pubchem_server.log")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Try to import PubChem modules
try:
    from pubchem_mcp_server.pubchem_api import get_pubchem_data
    from pubchem_mcp_server.async_processor import get_processor, AsyncRequestProcessor
    
    PUBCHEM_AVAILABLE = True
    logger.info("Successfully imported PubChem modules")
except ImportError as e:
    logger.error(f"Could not import PubChem modules: {e}")
    PUBCHEM_AVAILABLE = False

# Global variables
processor: Optional[AsyncRequestProcessor] = None
should_exit = False

# Signal handler
def signal_handler(sig, frame):
    """Handle interrupt signals"""
    global should_exit
    logger.info("Received interrupt signal, shutting down...")
    should_exit = True
    if processor:
        processor.shutdown()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def setup():
    """Setup environment"""
    global processor
    
    # Initialize processor if PubChem modules are available
    if PUBCHEM_AVAILABLE:
        try:
            processor = get_processor()
            logger.info("Initialized async request processor")
        except Exception as e:
            logger.error(f"Failed to initialize async processor: {e}")
            logger.error(traceback.format_exc())

def handle_pubchem_request(request_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle PubChem API requests"""
    global processor
    
    # Check if PubChem is available
    if not PUBCHEM_AVAILABLE:
        return {
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "PubChem API is not available"
                    }
                ],
                "isError": True
            }
        }
    
    try:
        # Handle get_pubchem_data (direct/synchronous)
        if tool_name == "get_pubchem_data":
            if not arguments.get("query"):
                return {
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: missing required parameter 'query'"
                    }
                }
            
            # Process request directly
            format_param = arguments.get("format", "JSON")
            include_3d = arguments.get("include_3d", False)
            
            # Validate format and include_3d
            if format_param.upper() == "XYZ" and not include_3d:
                return {
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": "When using XYZ format, the include_3d parameter must be set to true",
                            },
                        ],
                        "isError": True,
                    }
                }
            
            try:
                # Use a short timeout for direct requests
                # Start a timer
                start_time = time.time()
                logger.info(f"Starting direct PubChem request for {arguments.get('query')}")
                
                # Call PubChem API
                result = get_pubchem_data(
                    arguments.get("query"),
                    format_param,
                    include_3d
                )
                
                # Log completion time
                elapsed_time = time.time() - start_time
                logger.info(f"Completed direct PubChem request in {elapsed_time:.2f} seconds")
                
                return {
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result,
                            },
                        ],
                    }
                }
            except Exception as e:
                logger.error(f"Error in get_pubchem_data: {e}")
                logger.error(traceback.format_exc())
                
                # If error is timeout or connection related, suggest using async request
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "connect" in error_msg.lower():
                    suggestion = (" Try using submit_pubchem_request for this query, which " +
                                 "processes the request asynchronously to avoid timeouts.")
                    error_msg += suggestion
                
                return {
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: {error_msg}",
                            },
                        ],
                        "isError": True,
                    }
                }
                
        # Handle submit_pubchem_request (asynchronous)
        elif tool_name == "submit_pubchem_request":
            if not arguments.get("query"):
                return {
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: missing required parameter 'query'"
                    }
                }
            
            # Check if async processor is available
            if not processor:
                return {
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": "Async processor is not available",
                            },
                        ],
                        "isError": True,
                    }
                }
            
            # Validate format and include_3d
            format_param = arguments.get("format", "JSON")
            include_3d = arguments.get("include_3d", False)
            
            if format_param.upper() == "XYZ" and not include_3d:
                return {
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": "When using XYZ format, the include_3d parameter must be set to true",
                            },
                        ],
                        "isError": True,
                    }
                }
            
            # Submit to async processor
            try:
                logger.info(f"Submitting async request for {arguments.get('query')}")
                req_id = processor.submit_request(
                    arguments.get("query"),
                    format_param,
                    include_3d
                )
                
                return {
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "request_id": req_id,
                                    "message": "Request submitted successfully. Use get_request_status with this request_id to check the status."
                                }, indent=2),
                            },
                        ],
                    }
                }
            except Exception as e:
                logger.error(f"Error in submit_pubchem_request: {e}")
                logger.error(traceback.format_exc())
                return {
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error submitting request: {str(e)}",
                            },
                        ],
                        "isError": True,
                    }
                }
        
        # Handle get_request_status
        elif tool_name == "get_request_status":
            if not arguments.get("request_id"):
                return {
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: missing required parameter 'request_id'"
                    }
                }
            
            # Check if async processor is available
            if not processor:
                return {
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": "Async processor is not available",
                            },
                        ],
                        "isError": True,
                    }
                }
            
            # Get status from processor
            try:
                logger.info(f"Getting status for request {arguments.get('request_id')}")
                status = processor.get_status(arguments.get("request_id"))
                
                if status is None:
                    return {
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Request ID not found: {arguments.get('request_id')}",
                                },
                            ],
                            "isError": True,
                        }
                    }
                
                # Return status
                return {
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(status, indent=2),
                            },
                        ],
                    }
                }
            except Exception as e:
                logger.error(f"Error in get_request_status: {e}")
                logger.error(traceback.format_exc())
                return {
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error getting request status: {str(e)}",
                            },
                        ],
                        "isError": True,
                    }
                }
        else:
            # If tool name is not recognized, return hello_world as a fallback
            if tool_name == "hello_world":
                name = arguments.get("name", "World")
                return {
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
                return {
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {tool_name}"
                    }
                }
    except Exception as e:
        logger.error(f"Unhandled exception in handle_pubchem_request: {e}")
        logger.error(traceback.format_exc())
        return {
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"Internal error: {str(e)}",
                    },
                ],
                "isError": True,
            }
        }

def get_tools_list() -> List[Dict[str, Any]]:
    """Get list of available tools"""
    tools = [
        # Always include hello_world as a basic tool to verify connectivity
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
    
    # Add PubChem tools if available
    if PUBCHEM_AVAILABLE:
        tools.extend([
            {
                "name": "get_pubchem_data",
                "description": "Retrieve compound structure and property data (synchronous)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Compound name or PubChem CID",
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format, options: 'JSON', 'CSV', or 'XYZ', default: 'JSON'",
                            "enum": ["JSON", "CSV", "XYZ"],
                        },
                        "include_3d": {
                            "type": "boolean",
                            "description": "Whether to include 3D structure information (only valid when format is 'XYZ'), default: false",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "submit_pubchem_request",
                "description": "Submit asynchronous request for PubChem data (useful for slower queries)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Compound name or PubChem CID",
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format, options: 'JSON', 'CSV', or 'XYZ', default: 'JSON'",
                            "enum": ["JSON", "CSV", "XYZ"],
                        },
                        "include_3d": {
                            "type": "boolean",
                            "description": "Whether to include 3D structure information (only valid when format is 'XYZ'), default: false",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_request_status",
                "description": "Get status of an asynchronous PubChem data request",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "request_id": {
                            "type": "string",
                            "description": "Request ID returned from submit_pubchem_request",
                        },
                    },
                    "required": ["request_id"],
                },
            }
        ])
    
    return tools

def main():
    """Main function"""
    # Setup environment
    setup()
    
    logger.info("Starting integrated PubChem MCP server")
    
    # Process requests in a loop
    while not should_exit:
        try:
            # Read a line from stdin
            line = sys.stdin.readline()
            if not line:
                logger.info("End of input, exiting")
                break
            
            # Parse JSON request
            try:
                request = json.loads(line)
                request_id = request.get("id")
                method = request.get("method")
                
                logger.info(f"Received request: {method} (id: {request_id})")
                
                # Handle different requests
                response = None
                
                if method == "initialize":
                    # Basic initialize response
                    response = {
                        "id": request_id,
                        "result": {
                            "name": "pubchem-integrated-server",
                            "version": "1.0.0",
                            "capabilities": {
                                "tools": {}
                            }
                        }
                    }
                elif method == "list_tools":
                    # Return available tools
                    response = {
                        "id": request_id,
                        "result": {
                            "tools": get_tools_list()
                        }
                    }
                elif method == "call_tool":
                    # Handle tool call
                    params = request.get("params", {})
                    tool_name = params.get("name", "")
                    arguments = params.get("arguments", {})
                    
                    if not tool_name:
                        response = {
                            "id": request_id,
                            "error": {
                                "code": -32602,
                                "message": "Invalid params: missing tool name"
                            }
                        }
                    else:
                        # Handle PubChem-related requests
                        response = handle_pubchem_request(request_id, tool_name, arguments)
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
                    # Log response summary
                    if "error" in response:
                        logger.info(f"Sending error response for {method}: {response['error'].get('message', '')}")
                    else:
                        logger.info(f"Sending success response for {method}")
                    
                    # Write to stdout
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON input: {e}")
                logger.error(f"Input was: {line.strip()}")
                # Try to send an error response
                error_response = json.dumps({
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                })
                sys.stdout.write(error_response + "\n")
                sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            logger.error(traceback.format_exc())
            # Try to send an error response
            try:
                error_response = json.dumps({
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                })
                sys.stdout.write(error_response + "\n")
                sys.stdout.flush()
            except Exception:
                pass
    
    # Shutdown
    logger.info("Shutting down")
    if processor:
        processor.shutdown()
    logger.info("Server exited cleanly")

if __name__ == "__main__":
    main()
