#!/usr/bin/env python
"""
Count implemented methods in the Legifrance client.
"""

import inspect
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tulit.client.legifrance import LegifranceClient

def count_methods():
    client_methods = [m for m in dir(LegifranceClient) 
                     if not m.startswith('_') and callable(getattr(LegifranceClient, m))]
    
    # Filter out inherited methods from Client base class
    exclude = ['handle_response', 'get_extension_from_content_type', 'extract_zip', 'get_token']
    specific_methods = [m for m in client_methods if m not in exclude]
    
    print(f'Total methods implemented: {len(specific_methods)}')
    print(f'\nMethods by controller:')
    
    controllers = {
        'consult': [m for m in specific_methods if 'consult' in m],
        'list': [m for m in specific_methods if 'list' in m],
        'search': [m for m in specific_methods if 'search' in m],
        'suggest': [m for m in specific_methods if 'suggest' in m],
        'chrono': [m for m in specific_methods if 'chrono' in m],
        'misc': [m for m in specific_methods if 'misc' in m],
        'download': [m for m in specific_methods if 'download' in m]
    }
    
    for controller, methods in controllers.items():
        print(f'  {controller.upper()}: {len(methods)} methods')
        if methods and len(methods) < 20:  # Only show details for smaller lists
            for method in sorted(methods):
                print(f'    - {method}')
    
    api_methods = sum(len(v) for k, v in controllers.items() if k != 'download')
    print(f'\nTotal API-facing methods: {api_methods}')
    print(f'Total download helper methods: {len(controllers["download"])}')
    
    # Calculate coverage
    total_endpoints = 68
    implemented = api_methods
    coverage = (implemented / total_endpoints) * 100
    
    print(f'\n{"="*60}')
    print(f'API Coverage: {implemented}/{total_endpoints} endpoints ({coverage:.1f}%)')
    print(f'{"="*60}')

if __name__ == '__main__':
    count_methods()
