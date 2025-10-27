import requests

# The cellar ID that works in browser
cellar_id = "e115172d-3ab3-4b14-b0a4-dfdcc9871793.0006.02/DOC_1"
url = f"https://publications.europa.eu/resource/cellar/{cellar_id}"

print("=" * 70)
print("Testing Cellar access with different User-Agents:")
print("=" * 70)
print()

user_agents = [
    ("No User-Agent", {}),
    ("Default Requests", {"User-Agent": requests.utils.default_user_agent()}),
    ("Chrome", {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}),
    ("Firefox", {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"}),
    ("Safari", {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"}),
]

for name, headers in user_agents:
    print(f"{name}")
    if headers:
        print(f"  User-Agent: {headers.get('User-Agent', 'N/A')[:60]}...")
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  Status: {r.status_code}")
        print(f"  Content-Type: {r.headers.get('Content-Type', 'N/A')}")
        print(f"  Size: {len(r.content)} bytes")
        
        if r.status_code == 200:
            if 'html' in r.headers.get('Content-Type', '').lower():
                if len(r.content) > 200:  # Real HTML page, not error
                    print("  ✓ SUCCESS - Got HTML content!")
                else:
                    print("  ⚠ Got small HTML (likely error page)")
            else:
                print("  ✓ SUCCESS - Got real content!")
        else:
            print(f"  ✗ Failed")
            
    except Exception as e:
        print(f"  Error: {e}")
    
    print()

print("=" * 70)
print("\nNow testing with Chrome User-Agent + GET request to download:")
print("=" * 70)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type')}")
    print(f"Content-Length: {len(r.content)} bytes")
    
    if r.status_code == 200 and len(r.content) > 1000:
        print("\n✓ SUCCESS! Got real document content!")
        print(f"\nFirst 200 bytes: {r.content[:200]}")
    else:
        print("\n✗ Still failed")
        print(f"Response: {r.text[:200]}")
        
except Exception as e:
    print(f"Error: {e}")
