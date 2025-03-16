#!/usr/bin/env python3
"""
PubChem MCP Wrapper Script

A simple wrapper script that accepts query parameters from stdin (in JSON format)
and calls the pubchem-mcp command line tool.
"""

import json
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function"""
    # Read JSON input from stdin
    try:
        input_data = json.loads(sys.stdin.read())
        logger.info(f"Received input: {input_data}")
        
        # Extract query parameters
        query = input_data.get("query")
        if not query:
            print(json.dumps({"error": "Missing required parameter: query"}))
            return
        
        format_param = input_data.get("format", "JSON")
        include_3d = input_data.get("include_3d", False)
        
        # Build command
        cmd = ["pubchem-mcp", query]
        if format_param:
            cmd.extend(["--format", format_param])
        if include_3d:
            cmd.append("--include-3d")
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        # Execute command asynchronously with timeout
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = process.communicate(timeout=60)  # 60 seconds timeout
            
            # Check if command was successful
            if process.returncode == 0:
                print(stdout)
            else:
                print(json.dumps({"error": f"Command failed: {stderr}"}))
        except subprocess.TimeoutExpired:
            process.kill()
            print(json.dumps({"error": "Command timed out"}))
        except Exception as e:
            print(json.dumps({"error": f"Error in subprocess: {str(e)}"}))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {str(e)}"}))
    except Exception as e:
        print(json.dumps({"error": f"Error: {str(e)}"}))

if __name__ == "__main__":
    main()
