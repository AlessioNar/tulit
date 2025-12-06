"""
Example usage of the Legifrance Client

This script demonstrates how to use the LegifranceClient to access French legal documents.

Before running this script, set your credentials:
    $env:LEGIFRANCE_CLIENT_ID = "your_client_id"
    $env:LEGIFRANCE_CLIENT_SECRET = "your_client_secret"
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path to import tulit
sys.path.insert(0, str(Path(__file__).parent.parent))

from tulit.client.legifrance import LegifranceClient


def main():
    # Get credentials from environment variables
    client_id = os.environ.get('LEGIFRANCE_CLIENT_ID')
    client_secret = os.environ.get('LEGIFRANCE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("Error: Please set LEGIFRANCE_CLIENT_ID and LEGIFRANCE_CLIENT_SECRET environment variables")
        print("\nExample:")
        print('  $env:LEGIFRANCE_CLIENT_ID = "your_client_id"')
        print('  $env:LEGIFRANCE_CLIENT_SECRET = "your_client_secret"')
        sys.exit(1)
    
    # Initialize client
    client = LegifranceClient(
        client_id=client_id,
        client_secret=client_secret,
        download_dir='./data/france/legifrance',
        log_dir='./logs'
    )
    
    print("=" * 80)
    print("Legifrance Client Examples")
    print("=" * 80)
    
    # Example 1: List available codes
    print("\n[Example 1] Listing first 5 codes...")
    try:
        codes = client.list_codes(page_number=1, page_size=5)
        print(f"Total codes available: {codes.get('totalResults', 'N/A')}")
        print("\nFirst 5 codes:")
        for i, code in enumerate(codes.get('results', [])[:5], 1):
            print(f"  {i}. {code.get('title', 'N/A')} (ID: {code.get('textId', 'N/A')})")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 2: Get Code Civil information
    print("\n[Example 2] Getting Code Civil information...")
    try:
        code_civil_id = "LEGITEXT000006070721"
        code = client.consult_code(code_civil_id)
        print(f"Title: {code.get('title', 'N/A')}")
        print(f"Text ID: {code.get('textId', 'N/A')}")
        print(f"Number of sections: {len(code.get('sections', []))}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 3: Search for documents
    print("\n[Example 3] Searching for 'droit du travail'...")
    try:
        results = client.search("droit du travail", page_number=1, page_size=3)
        print(f"Total results: {results.get('totalResults', 'N/A')}")
        print("\nTop 3 results:")
        for i, result in enumerate(results.get('results', [])[:3], 1):
            print(f"  {i}. {result.get('title', 'N/A')}")
            print(f"     ID: {result.get('textId', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 4: Get autocomplete suggestions
    print("\n[Example 4] Getting suggestions for 'code'...")
    try:
        suggestions = client.suggest("code")
        print("Suggestions:")
        for suggestion in suggestions.get('suggestions', [])[:5]:
            print(f"  - {suggestion}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 5: Download Code Civil (saves to file)
    print("\n[Example 5] Downloading Code Civil to file...")
    try:
        code_civil_id = "LEGITEXT000006070721"
        filepath = client.download_code(code_civil_id)
        print(f"Code Civil downloaded to: {filepath}")
        
        # Display file size
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"File size: {size:,} bytes ({size / 1024:.2f} KB)")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 6: List legislative dossiers
    print("\n[Example 6] Listing recent legislative dossiers...")
    try:
        dossiers = client.list_dossiers_legislatifs(page_number=1, page_size=3)
        print(f"Total dossiers: {dossiers.get('totalResults', 'N/A')}")
        print("\nRecent dossiers:")
        for i, dossier in enumerate(dossiers.get('results', [])[:3], 1):
            print(f"  {i}. {dossier.get('title', 'N/A')}")
            print(f"     ID: {dossier.get('textId', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 7: Get table of contents
    print("\n[Example 7] Getting table of contents for Code Civil...")
    try:
        code_civil_id = "LEGITEXT000006070721"
        toc = client.consult_table_matieres(code_civil_id)
        print("Table of contents structure:")
        for section in toc.get('sections', [])[:3]:
            print(f"  - {section.get('title', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 8: List LODA texts (laws and decrees)
    print("\n[Example 8] Listing recent LODA texts...")
    try:
        loda = client.list_loda(page_number=1, page_size=3)
        print(f"Total LODA texts: {loda.get('totalResults', 'N/A')}")
        print("\nRecent LODA texts:")
        for i, text in enumerate(loda.get('results', [])[:3], 1):
            print(f"  {i}. {text.get('title', 'N/A')}")
            print(f"     ID: {text.get('textId', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
