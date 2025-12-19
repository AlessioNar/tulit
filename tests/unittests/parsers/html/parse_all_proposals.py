"""
Utility script to parse all commission proposal HTML files and save them as JSON.
"""
import os
import json
from pathlib import Path
from tulit.parsers.html.cellar.proposal import ProposalHTMLParser

# Paths
PROPOSALS_DIR = Path(__file__).parent.parent.parent / "data" / "eurlex" / "commission_proposals_html"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "json" / "proposals"

def parse_all_proposals():
    """Parse all proposal files and save them as JSON."""
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get all HTML files
    html_files = sorted(PROPOSALS_DIR.glob("*.html"))
    
    if not html_files:
        print(f"No HTML files found in {PROPOSALS_DIR}")
        return
    
    print(f"Found {len(html_files)} proposal files")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Processing...\n")
    
    success_count = 0
    error_count = 0
    
    for i, html_file in enumerate(html_files, 1):
        file_name = html_file.stem  # e.g., "COM(2025)6"
        
        try:
            # Parse the file
            parser = ProposalHTMLParser()
            parser.parse(str(html_file))
            
            # Prepare output following LegalJSON schema
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
            
            # Save to JSON
            output_file = OUTPUT_DIR / f"{file_name}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            success_count += 1
            
            # Print progress every 10 files
            if i % 10 == 0 or i == len(html_files):
                print(f"Processed {i}/{len(html_files)} files...")
            
        except Exception as e:
            error_count += 1
            print(f"ERROR processing {file_name}: {str(e)}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"COMPLETE")
    print(f"{'='*60}")
    print(f"Total files: {len(html_files)}")
    print(f"Successfully parsed: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    parse_all_proposals()
