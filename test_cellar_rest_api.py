import requests

# Try HTTPS and various Accept headers

celex = "32008R1137"
url_base = f"https://publications.europa.eu/resource/celex/{celex}"

print("=" * 70)
print("Testing with HTTPS and various Accept headers:")
print("=" * 70)
print()

test_cases = [
    ("Accept PDF", {"Accept": "application/pdf"}),
    ("Accept HTML", {"Accept": "text/html"}),
    ("Accept XML", {"Accept": "application/xml"}),
    ("Accept ZIP", {"Accept": "application/zip"}),
    ("Accept Formex", {"Accept": "application/xml;type=fmx4"}),
    ("Accept Any", {"Accept": "*/*"}),
    ("No Accept", {}),
]

for name, headers in test_cases:
    url = f"{url_base}?language=ENG"
    print(f"{name}")
    print(f"  Headers: {headers if headers else 'None'}")
    
    try:
        r = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
        print(f"  Status: {r.status_code}")
        print(f"  Content-Type: {r.headers.get('Content-Type', 'N/A')}")
        print(f"  Size: {len(r.content)} bytes")
        if r.status_code == 200:
            # Check if it's actually HTML or real content
            if r.headers.get('Content-Type', '').startswith('text/html'):
                print("  ⚠ Got HTML (likely error page)")
            else:
                print("  ✓ SUCCESS - Got real content!")
    except Exception as e:
        print(f"  Error: {e}")
    
    print()
