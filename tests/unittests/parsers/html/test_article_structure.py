from tulit.parsers.html.cellar.proposal import ProposalHTMLParser
import json
import os
from tests.conftest import locate_data_dir

# Get the path relative to the project root
DATA_ROOT = locate_data_dir(__file__)
file_path = str(DATA_ROOT / 'sources' / 'eu' / 'eurlex' / 'commission_proposals' / 'COM(2025)6.html')
parser = ProposalHTMLParser()
parser.parse(file_path)

print(f"\nArticles extracted: {len(parser.articles)}")
print("\nFirst 3 articles structure:")
for i, art in enumerate(parser.articles[:3]):
    print(f"\n{i+1}. Article:")
    print(f"   eId: {art.get('eId')}")
    print(f"   num: {art.get('num')}")
    print(f"   heading: {art.get('heading', 'N/A')}")
    print(f"   children count: {len(art.get('children', []))}")
    if art.get('children'):
        first_child = art['children'][0]
        print(f"   first child eId: {first_child.get('eId')}")
        print(f"   first child text: {first_child['text'][:80]}...")

# Check Article 4 specifically
article_4 = next((a for a in parser.articles if 'art_4' == a.get('eId')), None)
if article_4:
    print(f"\n\nArticle 4 detailed:")
    print(f"  eId: {article_4.get('eId')}")
    print(f"  num: {article_4.get('num')}")
    print(f"  heading: {article_4.get('heading', 'N/A')}")
    print(f"  children count: {len(article_4.get('children', []))}")
    print(f"  All children have eIds: {all('eId' in child for child in article_4.get('children', []))}")
    if article_4.get('children'):
        print(f"  First child eId: {article_4['children'][0].get('eId')}")
        print(f"  Last child eId: {article_4['children'][-1].get('eId')}")

# Save to JSON following the LegalJSON schema
output_data = {
    'preface': parser.preface,
    'preamble': None,  # According to schema, preamble is string or null
    'formula': parser.formula,
    'citations': parser.citations if hasattr(parser, 'citations') else [],
    'recitals': parser.recitals if hasattr(parser, 'recitals') else [],
    'preamble_final': parser.preamble_final if hasattr(parser, 'preamble_final') else None,
    'chapters': parser.chapters if hasattr(parser, 'chapters') else [],
    'articles': parser.articles if hasattr(parser, 'articles') else [],
    'conclusions': parser.conclusions if hasattr(parser, 'conclusions') else None
}

output_path = str(DATA_ROOT / 'results' / 'eu' / 'proposals' / 'COM(2025)6.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2, ensure_ascii=False)
    
print(f"\n\nJSON file updated: {output_path}")
