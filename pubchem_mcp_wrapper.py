#!/usr/bin/env python3
"""
PubChem MCP Wrapper Script (Improved Version)

An improved wrapper script that directly utilizes the PubChem MCP server's
asynchronous processing capabilities to handle requests without timing out.
"""

import json
import sys
import logging
import asyncio
import time
import signal
import os
import traceback
from typing import Dict, Any, Optional

# Configure logging to file for debugging
log_dir = os.path.expanduser("~/.pubchem-mcp")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "pubchem_mcp_wrapper.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Starting PubChem MCP Wrapper. Logging to {log_file}")

# Try to import MCP server components
try:
    from pubchem_mcp_server.pubchem_api import get_pubchem_data
    from pubchem_mcp_server.async_processor import get_processor, AsyncRequestProcessor
    
    MODULES_AVAILABLE = True
    logger.info("Successfully imported PubChem MCP server modules")
except ImportError as e:
    logger.error(f"Could not import PubChem MCP server modules: {e}")
    MODULES_AVAILABLE = False

# Global state
processor: Optional[AsyncRequestProcessor] = None
should_exit = False

def signal_handler(sig, frame):
    """Handle interrupt signals"""
    global should_exit
    logger.info("Received interrupt signal, shutting down...")
    should_exit = True
    sys.exit(0)

def setup():
    """Setup environment"""
    global processor
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize processor
    if MODULES_AVAILABLE:
        try:
            processor = get_processor()
            logger.info("Initialized async request processor")
        except Exception as e:
            logger.error(f"Failed to initialize async processor: {e}")
            logger.error(traceback.format_exc())
    else:
        logger.warning("Async processor not available")

def process_direct(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a request directly using the PubChem API
    
    This is a fallback if async processing is not available
    """
    try:
        query = request.get("query")
        if not query:
            return {"error": "Missing required parameter: query"}
        
        format_param = request.get("format", "JSON")
        include_3d = request.get("include_3d", False)
        
        # Validate format and include_3d
        if format_param.upper() == "XYZ" and not include_3d:
            return {"error": "When using XYZ format, the include_3d parameter must be set to true"}
        
        # Call PubChem API
        result = get_pubchem_data(query, format_param, include_3d)
        return {"result": result}
    except Exception as e:
        logger.error(f"Error in direct processing: {e}")
        return {"error": str(e)}

def process_mcp_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process an MCP request and return the response"""
    global processor
    
    try:
        # Log the full request for debugging
        logger.debug(f"Request data: {json.dumps(request_data)}")
        
        # Extract request type and parameters
        request_type = request_data.get("type", "")
        request_id = request_data.get("id", "")
        method = request_data.get("method", "")
        params = request_data.get("params", {})
        
        logger.info(f"Processing request: type={request_type}, id={request_id}, method={method}")
        
        # Handle initialize request - this is critical for MCP protocol
        if method == "initialize":
            logger.info("Handling initialize request")
            response = {
                "id": request_id,
                "result": {
                    "name": "pubchem-server",
                    "version": "1.0.0",
                    "capabilities": {
                        "tools": {}
                    }
                }
            }
            logger.debug(f"Initialize response: {json.dumps(response)}")
            return response
            
        # Handle different types of requests
        if request_type == "request":
            if method == "list_tools":
                # Return available tools
                return {
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "get_pubchem_data",
                                "description": "Retrieve compound structure and property data",
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
                            },
                        ]
                    }
                }
            
            elif method == "call_tool":
                # Handle tool calls
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                
                if not tool_name:
                    return {
                        "id": request_id,
                        "error": {
                            "code": -32602,
                            "message": "Invalid params: missing tool name"
                        }
                    }
                
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
                    
                    try:
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
                        
                        # Call PubChem API with timeout
                        result = get_pubchem_data(
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
                                        "text": result,
                                    },
                                ],
                            }
                        }
                    except Exception as e:
                        logger.error(f"Error in get_pubchem_data: {e}")
                        logger.error(traceback.format_exc())
                        return {
                            "id": request_id,
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"Error: {str(e)}",
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
                    
                    try:
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
                    
                    try:
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
                    return {
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {tool_name}"
                        }
                    }
            else:
                return {
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
        else:
            return {
                "id": request_id,
                "error": {
                    "code": -32600,
                    "message": f"Invalid request: unknown request type {request_type}"
                }
            }
    except Exception as e:
        logger.error(f"Unhandled exception in process_mcp_request: {e}")
        logger.error(traceback.format_exc())
        return {
            "id": request_id if request_id else None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

def main():
    """Main function"""
    # Setup environment
    setup()
    
    logger.info("Starting main loop")
    
    # Process requests in a loop
    while not should_exit:
        try:
            # Read a line from stdin
            line = sys.stdin.readline()
            if not line:
                # End of input, exit
                logger.info("End of input, exiting")
                break
            
            logger.debug(f"Received line: {line.strip()}")
            
            # Parse JSON request
            request_data = json.loads(line)
            
            # Process request
            response = process_mcp_request(request_data)
            
            # Write response to stdout
            response_json = json.dumps(response)
            logger.debug(f"Sending response: {response_json}")
            sys.stdout.write(response_json + "\n")
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
            logger.debug(f"Sending error response: {error_response}")
            sys.stdout.write(error_response + "\n")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            logger.error(traceback.format_exc())
            # Try to send an error response
            error_response = json.dumps({
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            })
            logger.debug(f"Sending error response: {error_response}")
            sys.stdout.write(error_response + "\n")
            sys.stdout.flush()
    
    # Shutdown
    logger.info("Shutting down")
    if processor:
        processor.shutdown()
    logger.info("Wrapper exited cleanly")

if __name__ == "__main__":
    main()
