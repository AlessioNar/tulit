"""
Quick test script to check which Legifrance API endpoints work in sandbox
"""
import os
from dotenv import load_dotenv
from tulit.client.legifrance import LegifranceClient
import json

load_dotenv()

client = LegifranceClient(
    client_id=os.environ.get('LEGIFRANCE_CLIENT_ID'),
    client_secret=os.environ.get('LEGIFRANCE_CLIENT_SECRET'),
    download_dir='./temp',
    log_dir='./logs'
)

print("=" * 80)
print("Testing Legifrance API Endpoints in Sandbox")
print("=" * 80)

endpoints_to_test = [
    {
        'name': 'List Codes',
        'test': lambda: client.list_codes(page_number=1, page_size=3),
        'description': 'Get a list of legal codes'
    },
    {
        'name': 'List LODA (Laws/Decrees)',
        'test': lambda: client.list_loda(page_number=1, page_size=3),
        'description': 'Get a list of laws and decrees'
    },
    {
        'name': 'List Dossiers',
        'test': lambda: client.list_dossiers_legislatifs(page_number=1, page_size=3),
        'description': 'Get a list of legislative dossiers'
    },
    {
        'name': 'List Conventions',
        'test': lambda: client.list_conventions(page_number=1, page_size=3),
        'description': 'Get a list of collective agreements'
    },
    {
        'name': 'Consult Ping',
        'test': lambda: client.consult_ping(),
        'description': 'Test the consult controller'
    },
    {
        'name': 'Suggest',
        'test': lambda: client.suggest("code civil"),
        'description': 'Get autocomplete suggestions'
    },
    {
        'name': 'Consult Code (Code Civil)',
        'test': lambda: client.consult_code("LEGITEXT000006070721"),
        'description': 'Retrieve Code Civil content'
    },
    {
        'name': 'Consult Law/Decree (Declaration 1789)',
        'test': lambda: client.consult_law_decree("LEGITEXT000006071192"),
        'description': 'Retrieve Declaration of Human Rights'
    },
    {
        'name': 'Consult Article',
        'test': lambda: client.consult_article("LEGIARTI000006419283"),
        'description': 'Retrieve a specific article'
    },
    {
        'name': 'Search',
        'test': lambda: client.search("code civil", page_size=3),
        'description': 'Search for documents'
    },
]

results = {}

for endpoint in endpoints_to_test:
    print(f"\n{'─' * 80}")
    print(f"Testing: {endpoint['name']}")
    print(f"Description: {endpoint['description']}")
    print('─' * 80)
    
    try:
        result = endpoint['test']()
        
        # Check if result has meaningful content
        if isinstance(result, dict):
            if 'results' in result:
                count = len(result['results']) if isinstance(result['results'], list) else 0
                print(f"✓ SUCCESS - Got {count} results")
                results[endpoint['name']] = 'SUCCESS'
            elif 'totalResultNumber' in result:
                print(f"✓ SUCCESS - Total results: {result.get('totalResultNumber', 'unknown')}")
                results[endpoint['name']] = 'SUCCESS'
            else:
                print(f"✓ SUCCESS - Response received")
                results[endpoint['name']] = 'SUCCESS'
        else:
            print(f"✓ SUCCESS")
            results[endpoint['name']] = 'SUCCESS'
            
    except Exception as e:
        error_msg = str(e)
        if '500' in error_msg:
            print(f"✗ FAILED - 500 Internal Server Error (sandbox limitation)")
            results[endpoint['name']] = 'FAILED (500)'
        elif '404' in error_msg:
            print(f"✗ FAILED - 404 Not Found")
            results[endpoint['name']] = 'FAILED (404)'
        elif '401' in error_msg or '403' in error_msg:
            print(f"✗ FAILED - Authentication error")
            results[endpoint['name']] = 'FAILED (Auth)'
        else:
            print(f"✗ FAILED - {error_msg}")
            results[endpoint['name']] = f'FAILED ({type(e).__name__})'

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

working = [k for k, v in results.items() if v == 'SUCCESS']
failing = [k for k, v in results.items() if v != 'SUCCESS']

print(f"\n✓ Working endpoints ({len(working)}):")
for endpoint in working:
    print(f"  - {endpoint}")

print(f"\n✗ Failing endpoints ({len(failing)}):")
for endpoint in failing:
    print(f"  - {endpoint}: {results[endpoint]}")

print("\n" + "=" * 80)
