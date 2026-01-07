"""
Script to test Digital Dimensions extraction on multiple proposals.
"""
from tulit.parser.html.cellar.proposal import ProposalHTMLParser
import json
from pathlib import Path

# Find proposals with Digital Dimensions
proposals_dir = Path('database/e2e_results/sources/eu/cellar/proposals')
results = []

# Test with several proposals that are known to have Digital Dimensions
test_proposals = [
    # Original 8
    '0761a954-c5f7-11f0-8da2-01aa75ed71a1.0001.03',  # PEPP (rich content)
    '0497e3aa-f5c5-11ef-b7db-01aa75ed71a1.0001.03',  # Euratom (minimal)
    '049d704d-f4fb-11ef-b7db-01aa75ed71a1.0001.03',  # InvestEU
    '0191486b-9561-11f0-97c8-01aa75ed71a1.0001.03',
    '07ccf3ec-fa73-11ef-b7db-01aa75ed71a1.0001.03',
    '080c9db1-3630-11f0-8a44-01aa75ed71a1.0001.03',
    '08ea46f4-0faf-11f0-b1a3-01aa75ed71a1.0001.03',
    '0dc29a24-1394-11f0-b1a3-01aa75ed71a1.0011.03',
    # Additional 10
    '11059782-c52b-11f0-8da2-01aa75ed71a1.0001.03',
    '1a3988fe-9f7a-11f0-97c8-01aa75ed71a1.0001.03',
    '1ab89f00-0fa6-11f0-b1a3-01aa75ed71a1.0020.03',
    '1fd20a2c-c61f-11f0-8da2-01aa75ed71a1.0001.03',
    '20582d73-88d0-11f0-9af8-01aa75ed71a1.0001.03',
    '22480e83-5716-11f0-a9d0-01aa75ed71a1.0001.03',
    '248eff52-20eb-11f0-af23-01aa75ed71a1.0001.03',
    '2966d2f3-3630-11f0-8a44-01aa75ed71a1.0001.03',
    '32a956d0-0fae-11f0-b1a3-01aa75ed71a1.0001.03',
    '32f257ec-16b5-11f0-b1a3-01aa75ed71a1.0001.03',
]

for proposal_id in test_proposals:
    proposal_path = proposals_dir / proposal_id
    if not proposal_path.exists():
        print(f'Skipping {proposal_id}: not found')
        continue
    
    # Find DOC_1.html or first HTML file
    html_files = list(proposal_path.glob('DOC_*.html'))
    if not html_files:
        print(f'Skipping {proposal_id}: no HTML files')
        continue
    
    html_file = html_files[0]
    print(f'Processing {proposal_id} / {html_file.name}...')
    
    try:
        parser = ProposalHTMLParser()
        parser.parse(str(html_file))
        
        result = {
            'proposal_id': proposal_id,
            'file': html_file.name,
            'metadata': parser.metadata,
            'digital_dimensions': parser.digital_dimensions
        }
        results.append(result)
        
        if parser.digital_dimensions:
            dd = parser.digital_dimensions
            subsection_count = len(dd.get('subsections', []))
            print(f'  -> Found {subsection_count} subsections')
        else:
            print(f'  -> No Digital Dimensions')
    except Exception as e:
        print(f'  -> Error: {e}')

# Save results
output_path = Path('database/e2e_results/digital_dimensions_test_results.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f'\nResults saved to {output_path}')
print(f'Total proposals processed: {len(results)}')

# Print summary
print('\n=== SUMMARY ===')
for r in results:
    title = r['metadata'].get('title', 'Unknown')[:60]
    dd = r['digital_dimensions']
    if dd:
        subs = dd.get('subsections', [])
        total_tables = sum(len(s.get('tables', [])) for s in subs)
        total_text = sum(len(s.get('text_content', [])) for s in subs)
        print(f'{r["proposal_id"][:20]}... : {len(subs)} subsections, {total_tables} tables, {total_text} text items')
    else:
        print(f'{r["proposal_id"][:20]}... : No Digital Dimensions')
