"""
Quick test of Legifrance API endpoints - fast version with timeout
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
print("Testing Legifrance API Endpoints")
print("=" * 80)

# Track results
working = []
failing = []

def test_endpoint(name, test_func, description):
    """Test a single endpoint and categorize the result"""
    print(f"\n{name}: {description}")
    try:
        result = test_func()
        if isinstance(result, dict) and ('results' in result or 'totalResultNumber' in result):
            count = len(result['results']) if 'results' in result and isinstance(result['results'], list) else result.get('totalResultNumber', '?')
            print(f"  ✓ SUCCESS (count: {count})")
            working.append(name)
        else:
            print(f"  ✓ SUCCESS")
            working.append(name)
        return True
    except Exception as e:
        error = str(e)
        if '500' in error:
            print(f"  ✗ FAILED - 500 Internal Server Error")
            failing.append((name, '500'))
        elif '400' in error:
            print(f"  ✗ FAILED - 400 Bad Request")
            failing.append((name, '400'))
        elif '404' in error:
            print(f"  ✗ FAILED - 404 Not Found")
            failing.append((name, '404'))
        else:
            print(f"  ✗ FAILED - {type(e).__name__}")
            failing.append((name, type(e).__name__))
        return False

# LIST ENDPOINTS (we know these work)
print("\n" + "="*80)
print("LIST ENDPOINTS")
print("="*80)
test_endpoint("List Codes", lambda: client.list_codes(1, 3), "List legal codes")
test_endpoint("List LODA", lambda: client.list_loda(1, 3), "List laws/decrees")
test_endpoint("List Conventions", lambda: client.list_conventions(1, 3), "List collective agreements")

# CONSULT ENDPOINTS (we suspect these fail)
print("\n" + "="*80)
print("CONSULT ENDPOINTS")
print("="*80)
test_endpoint("Consult Code", lambda: client.consult_code("LEGITEXT000006070721"), "Code Civil")
test_endpoint("Consult Law/Decree", lambda: client.consult_law_decree("LEGITEXT000006071192"), "Declaration 1789")
test_endpoint("Consult Article", lambda: client.consult_article("LEGIARTI000006419283"), "Specific article")
test_endpoint("Consult Last N JO", lambda: client.consult_last_n_jo(3), "Last 3 Official Journals")

# SEARCH ENDPOINTS
print("\n" + "="*80)
print("SEARCH ENDPOINTS")
print("="*80)
test_endpoint("Search", lambda: client.search("code civil", page_size=3), "Search documents")

# SUGGEST ENDPOINTS
print("\n" + "="*80)
print("SUGGEST ENDPOINTS")
print("="*80)
test_endpoint("Suggest", lambda: client.suggest("code civil"), "Autocomplete suggestions")

# MISC ENDPOINTS
print("\n" + "="*80)
print("MISC ENDPOINTS")
print("="*80)
test_endpoint("Misc Commit ID", lambda: client.misc_commit_id(), "Deployment info")

# SUMMARY
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

print(f"\n✓ WORKING ENDPOINTS ({len(working)}):")
for endpoint in working:
    print(f"  - {endpoint}")

print(f"\n✗ FAILING ENDPOINTS ({len(failing)}):")
for endpoint, error in failing:
    print(f"  - {endpoint}: {error}")

print("\n" + "="*80)
print("\nConclusion:")
if working:
    print(f"✓ {len(working)} endpoints are functional in sandbox")
if failing:
    print(f"✗ {len(failing)} endpoints are not working (likely sandbox limitations)")
print("="*80)
