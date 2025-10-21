"""
Test script for German LegalDocML parser.
Demonstrates parsing German legislation XML files.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tulit.parsers.xml.akomantoso import GermanLegalDocMLParser


def test_parse_german_legislation():
    """Test parsing a German legislation XML file."""
    
    # Input and output paths
    input_file = Path(__file__).parent / 'data' / 'sources' / 'member_states' / 'germany' / 'legislation' / 'bgbl-1_2025_145_2025-06-17_1_deu_2025-10-20_regelungstext-verkuendung-1.xml'
    output_file = Path(__file__).parent / 'data' / 'results' / 'member_states' / 'germany' / 'bgbl-1_2025_145.json'
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return False
    
    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"📄 Parsing: {input_file.name}")
    print(f"   Using: GermanLegalDocMLParser")
    
    # Parse the document
    parser = GermanLegalDocMLParser()
    parser.parse(str(input_file))
    
    # Prepare output data
    output_data = {
        'preface': parser.preface,
        'formula': parser.formula,
        'citations': parser.citations,
        'recitals': parser.recitals,
        'preamble_final': parser.preamble_final,
        'chapters': parser.chapters,
        'articles': parser.articles,
        'conclusions': parser.conclusions
    }
    
    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"✓ Successfully parsed German legislation")
    print(f"   Articles: {len(parser.articles) if parser.articles else 0}")
    print(f"   Chapters: {len(parser.chapters) if parser.chapters else 0}")
    print(f"   Preface: {'Yes' if parser.preface else 'No'}")
    print(f"   Output: {output_file}")
    
    # Show sample article
    if parser.articles:
        print(f"\n📝 Sample (First Article):")
        article = parser.articles[0]
        print(f"   eId: {article.get('eId', 'N/A')}")
        print(f"   Number: {article.get('num', 'N/A')}")
        print(f"   Heading: {article.get('heading', 'N/A')}")
        print(f"   Paragraphs: {len(article.get('children', []))}")
        if article.get('children'):
            first_para = article['children'][0]
            text = first_para.get('text', '')
            print(f"   First paragraph: {text[:100]}...")
    
    return True


if __name__ == "__main__":
    print("=" * 80)
    print("German LegalDocML Parser Test")
    print("=" * 80)
    print()
    
    success = test_parse_german_legislation()
    
    print()
    print("=" * 80)
    if success:
        print("✓ Test completed successfully!")
    else:
        print("✗ Test failed")
    print("=" * 80)
    
    sys.exit(0 if success else 1)
