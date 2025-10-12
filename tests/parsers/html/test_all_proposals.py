"""
Test script to parse all commission proposal HTML files and report statistics.
This script can run in two modes:
1. Unit test mode (default): Tests only a few representative files
2. Full analysis mode: Tests all files when FULL_ANALYSIS environment variable is set
"""
import os
import sys
from pathlib import Path
from tulit.parsers.html.proposal import ProposalHTMLParser

# Path to the commission proposals directory
PROPOSALS_DIR = Path(__file__).parent.parent.parent / "data" / "eurlex" / "commission_proposals_html"

# Representative files for unit testing (instead of all 251 files)
SAMPLE_FILES = [
    "COM(2025)6.html",
    "COM(2025)43.html", 
    "COM(2025)1.html"
]

def test_sample_proposals():
    """Test parsing a sample of proposal files for unit testing."""
    
    # Check if we should run full analysis
    run_full_analysis = os.environ.get("FULL_ANALYSIS", "").lower() in ("true", "1", "yes")
    
    if run_full_analysis:
        return run_full_analysis_mode()
    
    # Unit test mode: only test sample files
    html_files = []
    for sample_file in SAMPLE_FILES:
        file_path = PROPOSALS_DIR / sample_file
        if file_path.exists():
            html_files.append(file_path)
        else:
            print(f"Warning: Sample file {sample_file} not found")
    
    if not html_files:
        print(f"No sample files found in {PROPOSALS_DIR}")
        return False
    
    print(f"Testing {len(html_files)} sample proposal files\n")
    print("=" * 50)
    
    success_count = 0
    error_count = 0
    errors = []
    
    stats = {
        'total_files': len(html_files),
        'with_explanatory_memorandum': 0,
        'with_legal_act': 0,
        'total_sections': 0,
        'total_recitals': 0,
        'total_citations': 0,
        'total_articles': 0,
    }
    
    for i, html_file in enumerate(html_files, 1):
        file_name = html_file.name
        
        try:
            parser = ProposalHTMLParser()
            parser.parse(str(html_file))
            
            # Collect statistics
            if parser.explanatory_memorandum and parser.explanatory_memorandum.get('sections'):
                stats['with_explanatory_memorandum'] += 1
                stats['total_sections'] += len(parser.explanatory_memorandum['sections'])
            
            if parser.recitals:
                stats['with_legal_act'] += 1
                stats['total_recitals'] += len(parser.recitals)
            
            if parser.citations:
                stats['total_citations'] += len(parser.citations)
            
            if parser.articles:
                stats['total_articles'] += len(parser.articles)
            
            success_count += 1
            
            # Print brief status
            print(f"OK [{i}/{len(html_files)}] {file_name}")
            print(f"   Metadata: {parser.metadata.get('com_reference', 'N/A')}")
            print(f"   EM sections: {len(parser.explanatory_memorandum.get('sections', []))}, "
                  f"Recitals: {len(parser.recitals)}, "
                  f"Citations: {len(parser.citations)}, "
                  f"Articles: {len(parser.articles)}")
            
        except Exception as e:
            error_count += 1
            error_msg = f"{file_name}: {str(e)}"
            errors.append(error_msg)
            print(f"ERROR [{i}/{len(html_files)}] {file_name}")
            print(f"   ERROR: {str(e)}")
        
        print()
    
    # Print summary
    print("=" * 80)
    print("\nSUMMARY")
    print("=" * 80)
    print(f"Total files processed: {len(html_files)}")
    print(f"Successfully parsed: {success_count} ({success_count/len(html_files)*100:.1f}%)")
    print(f"Errors: {error_count} ({error_count/len(html_files)*100:.1f}%)")
    print()
    print("STATISTICS")
    print("-" * 80)
    print(f"Files with Explanatory Memorandum: {stats['with_explanatory_memorandum']}")
    print(f"Files with Legal Act (preamble/body): {stats['with_legal_act']}")
    print(f"Total EM sections parsed: {stats['total_sections']}")
    print(f"Total recitals parsed: {stats['total_recitals']}")
    print(f"Total citations parsed: {stats['total_citations']}")
    print(f"Total articles parsed: {stats['total_articles']}")
    
    if stats['with_explanatory_memorandum'] > 0:
        print(f"Average sections per proposal: {stats['total_sections']/stats['with_explanatory_memorandum']:.1f}")
    
    if stats['with_legal_act'] > 0:
        print(f"Average recitals per legal act: {stats['total_recitals']/stats['with_legal_act']:.1f}")
        print(f"Average articles per legal act: {stats['total_articles']/stats['with_legal_act']:.1f}")
    
    if errors:
        print("\nERRORS ENCOUNTERED")
        print("-" * 80)
        for error in errors:
            print(f"  - {error}")
    
    print("\n" + "=" * 50)
    
    return error_count == 0


def run_full_analysis_mode():
    """Run full analysis on all proposal files - use with caution!"""
    
    # Get all HTML files
    html_files = sorted(PROPOSALS_DIR.glob("*.html"))
    
    if not html_files:
        print(f"No HTML files found in {PROPOSALS_DIR}")
        return False
    
    print(f"FULL ANALYSIS MODE: Found {len(html_files)} proposal files to test\n")
    print("=" * 80)
    
    success_count = 0
    error_count = 0
    errors = []
    
    stats = {
        'total_files': len(html_files),
        'with_explanatory_memorandum': 0,
        'with_legal_act': 0,
        'total_sections': 0,
        'total_recitals': 0,
        'total_citations': 0,
        'total_articles': 0,
    }
    
    for i, html_file in enumerate(html_files, 1):
        file_name = html_file.name
        
        try:
            parser = ProposalHTMLParser()
            parser.parse(str(html_file))
            
            # Collect statistics
            if parser.explanatory_memorandum and parser.explanatory_memorandum.get('sections'):
                stats['with_explanatory_memorandum'] += 1
                stats['total_sections'] += len(parser.explanatory_memorandum['sections'])
            
            if parser.recitals:
                stats['with_legal_act'] += 1
                stats['total_recitals'] += len(parser.recitals)
            
            if parser.citations:
                stats['total_citations'] += len(parser.citations)
            
            if parser.articles:
                stats['total_articles'] += len(parser.articles)
            
            success_count += 1
            
            # Print brief status
            print(f"OK [{i}/{len(html_files)}] {file_name}")
            print(f"   Metadata: {parser.metadata.get('com_reference', 'N/A')}")
            print(f"   EM sections: {len(parser.explanatory_memorandum.get('sections', []))}, "
                  f"Recitals: {len(parser.recitals)}, "
                  f"Citations: {len(parser.citations)}, "
                  f"Articles: {len(parser.articles)}")
            
        except Exception as e:
            error_count += 1
            error_msg = f"{file_name}: {str(e)}"
            errors.append(error_msg)
            print(f"ERROR [{i}/{len(html_files)}] {file_name}")
            print(f"   ERROR: {str(e)}")
        
        print()
    
    # Print summary
    print("=" * 80)
    print("\nFULL ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"Total files processed: {len(html_files)}")
    print(f"Successfully parsed: {success_count} ({success_count/len(html_files)*100:.1f}%)")
    print(f"Errors: {error_count} ({error_count/len(html_files)*100:.1f}%)")
    print()
    print("STATISTICS")
    print("-" * 80)
    print(f"Files with Explanatory Memorandum: {stats['with_explanatory_memorandum']}")
    print(f"Files with Legal Act (preamble/body): {stats['with_legal_act']}")
    print(f"Total EM sections parsed: {stats['total_sections']}")
    print(f"Total recitals parsed: {stats['total_recitals']}")
    print(f"Total citations parsed: {stats['total_citations']}")
    print(f"Total articles parsed: {stats['total_articles']}")
    
    if stats['with_explanatory_memorandum'] > 0:
        print(f"Average sections per proposal: {stats['total_sections']/stats['with_explanatory_memorandum']:.1f}")
    
    if stats['with_legal_act'] > 0:
        print(f"Average recitals per legal act: {stats['total_recitals']/stats['with_legal_act']:.1f}")
        print(f"Average articles per legal act: {stats['total_articles']/stats['with_legal_act']:.1f}")
    
    if errors:
        print("\nERRORS ENCOUNTERED")
        print("-" * 80)
        for error in errors:
            print(f"  - {error}")
    
    print("\n" + "=" * 80)
    
    return error_count == 0


if __name__ == "__main__":
    success = test_sample_proposals()
    sys.exit(0 if success else 1)
