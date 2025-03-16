"""
PubChem API Module

Provides functionality for interacting with the PubChem API to retrieve compound data.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Union, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Global cache
_cache: Dict[str, Dict[str, str]] = {}


def create_session() -> requests.Session:
    """Create a requests session with retry functionality"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_pubchem_data(query: str, format: str = 'JSON', include_3d: bool = False) -> str:
    """
    Get PubChem compound data
    
    Args:
        query: Compound name or PubChem CID
        format: Output format, options: "JSON", "CSV", or "XYZ", default: "JSON"
        include_3d: Whether to include 3D structure information (only valid when format is "XYZ"), default: False
        
    Returns:
        Formatted compound data string
    """
    from .xyz_utils import get_xyz_structure
    
    logger.info(f"Received query request: query={query}, format={format}, include_3d={include_3d}")
    
    if not query or not query.strip():
        return "Error: query cannot be empty."
    
    query_str = query.strip()
    is_cid = re.match(r'^\d+$', query_str) is not None
    cache_key = f"cid:{query_str}" if is_cid else f"name:{query_str.lower()}"
    identifier_path = f"cid/{query_str}" if is_cid else f"name/{query_str}"
    cid = query_str if is_cid else None
    
    logger.info(f"Query path: {identifier_path}")
    
    # Check cache
    if cache_key in _cache:
        logger.info("Getting data from cache")
        data = _cache[cache_key]
        if not cid:
            cid = data.get('CID')
            if not cid:
                return "Error: Could not find CID in cached data"
    else:
        # Define properties to retrieve
        properties = [
            'IUPACName',
            'MolecularFormula',
            'MolecularWeight',
            'CanonicalSMILES',
            'InChI',
            'InChIKey'
        ]
        
        # Build API URL
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{identifier_path}/property/{','.join(properties)}/JSON"
        
        try:
            session = create_session()
            response = session.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()
            props = result.get('PropertyTable', {}).get('Properties', [{}])[0]
            
            if not props:
                return "Error: compound not found or no data available."
            
            if not cid:
                cid = str(props.get('CID'))
                if not cid:
                    return "Error: Could not find CID in the response"
            
            # Create data dictionary
            data = {
                'IUPACName': props.get('IUPACName', ''),
                'MolecularFormula': props.get('MolecularFormula', ''),
                'MolecularWeight': str(props.get('MolecularWeight', '')),
                'CanonicalSMILES': props.get('CanonicalSMILES', ''),
                'InChI': props.get('InChI', ''),
                'InChIKey': props.get('InChIKey', ''),
                'CID': cid
            }
            
            # Update cache
            _cache[cache_key] = data
            if cid and f"cid:{cid}" != cache_key:
                _cache[f"cid:{cid}"] = data
                
        except requests.exceptions.RequestException as e:
            error_msg = getattr(e.response, 'json', lambda: {})().get('Fault', {}).get('Details', [{}])[0].get('Message', str(e))
            return f"Error: {error_msg}"
    
    # Handle different output formats
    fmt = format.upper()
    
    # XYZ format - 3D structure
    if fmt == 'XYZ':
        if include_3d:
            try:
                # Get compound information
                compound_info = {
                    'id': data['CID'],
                    'name': data['IUPACName'],
                    'formula': data['MolecularFormula'],
                    'smiles': data['CanonicalSMILES'],
                    'inchikey': data['InChIKey']
                }
                
                # Get XYZ structure
                xyz_structure = get_xyz_structure(data['CID'], data['CanonicalSMILES'], compound_info)
                
                if xyz_structure:
                    return xyz_structure
                else:
                    return "Error: Failed to generate 3D structure."
            except Exception as e:
                return f"Error generating 3D structure: {str(e)}"
        else:
            return "Error: include_3d parameter must be true for XYZ format."
    
    # CSV format
    elif fmt == 'CSV':
        headers = ['CID', 'IUPACName', 'MolecularFormula', 'MolecularWeight', 
                  'CanonicalSMILES', 'InChI', 'InChIKey']
        values = [data.get(h, '') for h in headers]
        return f"{','.join(headers)}\n{','.join(values)}"
    
    # Default JSON format
    else:
        return json.dumps(data, indent=2)
