"""
Script to run all parsers on documents in the database directory.
This script processes documents from database/sources/ and saves 
parsed results to database/results/ following the same hierarchy.
"""

import subprocess
import sys
import logging
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Database directories (outside the package)
DB_BASE = Path(__file__).parent.parent / 'database'
DB_SOURCES = DB_BASE / 'sources'
DB_RESULTS = DB_BASE / 'results'

failed_parsers = []

def ensure_dirs():
    """Ensure results directory structure exists"""
    dirs = [
        DB_RESULTS / 'eu' / 'proposals',
        DB_RESULTS / 'eu' / 'formex',
        DB_RESULTS / 'eu' / 'html',
        DB_RESULTS / 'eu' / 'akn',
        DB_RESULTS / 'member_states' / 'portugal',
        DB_RESULTS / 'member_states' / 'italy',
        DB_RESULTS / 'member_states' / 'luxembourg',
        DB_RESULTS / 'member_states' / 'france',
        DB_RESULTS / 'member_states' / 'finland',
        DB_RESULTS / 'member_states' / 'malta',
        DB_RESULTS / 'member_states' / 'germany' / 'legislation',
        DB_RESULTS / 'member_states' / 'germany' / 'case-law',
        DB_RESULTS / 'member_states' / 'germany' / 'literature',
        DB_RESULTS / 'regional' / 'italy' / 'veneto',
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

ensure_dirs()

def run_parser(name, parser_type, input_path, output_path):
    """Run a parser on an input file and save to output"""
    try:
        if not input_path.exists():
            logging.warning(f"{name}: Input file not found: {input_path}")
            return
        
        logging.info(f"Parsing {name}: {input_path.name}")
        
        # Import and run the appropriate parser
        if parser_type == 'html_proposal':
            from tulit.parsers.html.proposal import ProposalHTMLParser
            parser = ProposalHTMLParser()
            parser.parse(str(input_path))
            
            output_data = {
                'preface': parser.preface,
                'preamble': None,
                'formula': parser.formula,
                'citations': parser.citations if hasattr(parser, 'citations') else [],
                'recitals': parser.recitals if hasattr(parser, 'recitals') else [],
                'preamble_final': parser.preamble_final if hasattr(parser, 'preamble_final') else None,
                'chapters': parser.chapters if hasattr(parser, 'chapters') else [],
                'articles': parser.articles if hasattr(parser, 'articles') else [],
                'conclusions': parser.conclusions if hasattr(parser, 'conclusions') else None
            }
            
        elif parser_type == 'html_cellar':
            from tulit.parsers.html.cellar import CellarHTMLParser
            parser = CellarHTMLParser()
            parser.parse(str(input_path))
            
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
            
        elif parser_type == 'formex':
            from tulit.parsers.xml.formex import Formex4Parser
            parser = Formex4Parser()
            parser.parse(str(input_path))
            
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
            
        elif parser_type == 'akn':
            from tulit.parsers.xml.akomantoso import AkomaNtosoParser
            parser = AkomaNtosoParser()
            parser.parse(str(input_path))
            
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
        
        elif parser_type == 'akn-de' or parser_type == 'german':
            from tulit.parsers.xml.akomantoso import GermanLegalDocMLParser
            parser = GermanLegalDocMLParser()
            parser.parse(str(input_path))
            
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
                
        # Save output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"✓ {name}: Saved to {output_path}")
        
    except Exception as e:
        logging.error(f"✗ {name}: {e}")
        failed_parsers.append(name)

def main():
    logging.info("Starting parsers...")
    logging.info(f"Source directory: {DB_SOURCES}")
    logging.info(f"Results directory: {DB_RESULTS}")
    
    # Parse EU Commission Proposals (HTML)
    proposals_dir = DB_SOURCES / 'eu' / 'eurlex' / 'commission_proposals'
    if proposals_dir.exists():
        for html_file in proposals_dir.glob('*.html'):
            output_file = DB_RESULTS / 'eu' / 'proposals' / f"{html_file.stem}.json"
            run_parser(f"EU Proposal {html_file.stem}", 'html_proposal', html_file, output_file)
    
    # Parse EU Regulations (HTML from Cellar)
    regulations_dir = DB_SOURCES / 'eu' / 'eurlex' / 'regulations' / 'html'
    if regulations_dir.exists():
        for subdir in regulations_dir.iterdir():
            if subdir.is_dir():
                for html_file in subdir.glob('*.html'):
                    output_file = DB_RESULTS / 'eu' / 'html' / f"{subdir.name}_{html_file.stem}.json"
                    run_parser(f"EU Regulation {html_file.stem}", 'html_cellar', html_file, output_file)
    
    # Parse FORMEX documents
    formex_dir = DB_SOURCES / 'eu' / 'eurlex' / 'formex'
    if formex_dir.exists():
        for subdir in formex_dir.iterdir():
            if subdir.is_dir():
                for xml_file in subdir.glob('*.xml'):
                    output_file = DB_RESULTS / 'eu' / 'formex' / f"{subdir.name}_{xml_file.stem}.json"
                    run_parser(f"FORMEX {xml_file.stem}", 'formex', xml_file, output_file)
    
    # Parse AKN documents
    akn_dir = DB_SOURCES / 'eu' / 'eurlex' / 'akn'
    if akn_dir.exists():
        for akn_file in akn_dir.glob('*.akn'):
            output_file = DB_RESULTS / 'eu' / 'akn' / f"{akn_file.stem}.json"
            run_parser(f"AKN {akn_file.stem}", 'akn', akn_file, output_file)
        for xml_file in akn_dir.glob('*.xml'):
            output_file = DB_RESULTS / 'eu' / 'akn' / f"{xml_file.stem}.json"
            run_parser(f"AKN {xml_file.stem}", 'akn', xml_file, output_file)
    
    # Parse German legislation (LegalDocML/AKN format)
    germany_legislation_dir = DB_SOURCES / 'member_states' / 'germany' / 'gesetze' / 'legislation'
    if germany_legislation_dir.exists():
        for xml_file in germany_legislation_dir.glob('*.xml'):
            output_file = DB_RESULTS / 'member_states' / 'germany' / 'legislation' / f"{xml_file.stem}.json"
            run_parser(f"Germany Legislation {xml_file.stem}", 'german', xml_file, output_file)
    
    # Parse German case law (LegalDocML/AKN format)
    germany_caselaw_dir = DB_SOURCES / 'member_states' / 'germany' / 'gesetze' / 'case-law'
    if germany_caselaw_dir.exists():
        for xml_file in germany_caselaw_dir.glob('*.xml'):
            output_file = DB_RESULTS / 'member_states' / 'germany' / 'case-law' / f"{xml_file.stem}.json"
            run_parser(f"Germany Case Law {xml_file.stem}", 'german', xml_file, output_file)
    
    # Parse German literature (LegalDocML/AKN format)
    germany_literature_dir = DB_SOURCES / 'member_states' / 'germany' / 'gesetze' / 'literature'
    if germany_literature_dir.exists():
        for xml_file in germany_literature_dir.glob('*.xml'):
            output_file = DB_RESULTS / 'member_states' / 'germany' / 'literature' / f"{xml_file.stem}.json"
            run_parser(f"Germany Literature {xml_file.stem}", 'german', xml_file, output_file)
    
    # Summary
    print("\n" + "="*60)
    if failed_parsers:
        logging.error(f"Failed parsers: {', '.join(failed_parsers)}")
    else:
        logging.info("✓ All parsers completed successfully!")
    print("="*60)

if __name__ == '__main__':
    main()
