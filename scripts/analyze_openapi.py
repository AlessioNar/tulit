#!/usr/bin/env python
"""
Analyze the Legifrance OpenAPI specification and print endpoint summary.
"""

import json
from pathlib import Path

def analyze_spec():
    spec_path = Path(__file__).parent.parent / 'docs' / 'legifrance_openapi.json'
    
    with open(spec_path, encoding='utf-8') as f:
        spec = json.load(f)
    
    print(f"API: {spec['info']['title']} v{spec['info']['version']}")
    print(f"Base: {spec['host']}{spec['basePath']}")
    print("=" * 100)
    
    # Group endpoints by controller
    controllers = {}
    for path, details in spec['paths'].items():
        controller = path.split('/')[1]
        if controller not in controllers:
            controllers[controller] = []
        
        # Get the HTTP method (usually post or get)
        method = list(details.keys())[0]
        endpoint_info = details[method]
        
        controllers[controller].append({
            'path': path,
            'method': method.upper(),
            'summary': endpoint_info.get('summary', ''),
            'description': endpoint_info.get('description', ''),
            'operationId': endpoint_info.get('operationId', '')
        })
    
    # Print summary
    total = 0
    for controller, endpoints in sorted(controllers.items()):
        print(f'\n{controller.upper()} Controller: {len(endpoints)} endpoints')
        total += len(endpoints)
        for ep in sorted(endpoints, key=lambda x: x['path']):
            method_str = ep['method'].ljust(4)
            path_str = ep['path'].ljust(50)
            print(f'  {method_str} {path_str} - {ep["summary"]}')
    
    print(f'\n{"=" * 100}')
    print(f'Total endpoints: {total}')
    
    return controllers, spec

if __name__ == '__main__':
    controllers, spec = analyze_spec()
