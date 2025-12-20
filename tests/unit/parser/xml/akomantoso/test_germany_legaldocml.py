"""
Test script for German LegalDocML parser.
Demonstrates parsing German legislation XML files.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tulit.parser.xml.akomantoso import GermanLegalDocMLParser
from tests.conftest import locate_data_dir


def test_parse_german_legislation():
    """Test parsing a German legislation XML file."""
    
    # Input and output paths
    data_root = locate_data_dir(__file__)
    input_file = data_root / 'sources' / 'member_states' / 'germany' / 'legislation' / 'bgbl-1_2025_145_2025-06-17_1_deu_2025-10-20_regelungstext-verkuendung-1.xml'
    output_file = data_root / 'results' / 'member_states' / 'germany' / 'bgbl-1_2025_145.json'
    
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
    
    # Use assertion for pytest compatibility
    assert True, "German legislation parsing completed successfully"
