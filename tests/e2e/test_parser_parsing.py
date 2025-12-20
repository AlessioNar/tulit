"""
End-to-end tests for parser parsing functionality.
Tests the complete parsing pipeline from downloaded source files to parsed JSON output.
Uses files downloaded by client e2e tests as fixtures.
"""

import pytest
import os
import json
from pathlib import Path
import logging


@pytest.mark.e2e
@pytest.mark.parser
class TestParserParsing:
    """Test suite for parser parsing functionality."""

    @pytest.mark.slow
    def test_eu_proposal_html_parsing(self, db_paths):
        """Test parsing EU Commission Proposal HTML documents."""
        sources_dir = db_paths['sources'] / 'eu' / 'eurlex' / 'commission_proposals'
        results_dir = db_paths['results'] / 'eu' / 'proposals'
        logs_dir = db_paths['logs']

        # Find downloaded HTML files
        html_files = list(sources_dir.glob('*.html'))
        if not html_files:
            pytest.skip("No EU proposal HTML files found - run client e2e tests first")

        # Test parsing the first available file
        html_file = html_files[0]
        expected_output = results_dir / f"{html_file.stem}.json"

        from tulit.parser.html.cellar.proposal import ProposalHTMLParser
        parser = ProposalHTMLParser()

        # Parse the file
        parser.parse(str(html_file))

        # Verify parsing results
        assert parser.preface is not None, "Preface should be extracted"
        assert parser.formula is not None, "Formula should be extracted"
        assert isinstance(parser.citations, list), "Citations should be a list"
        assert isinstance(parser.recitals, list), "Recitals should be a list"
        assert isinstance(parser.chapters, list), "Chapters should be a list"
        assert isinstance(parser.articles, list), "Articles should be a list"

        # Save results (similar to run_all_parsers.py)
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

        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"

        # Verify output is valid JSON
        with open(expected_output, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        assert 'articles' in loaded_data, "Output should contain articles"

    @pytest.mark.slow
    def test_eu_regulation_html_parsing(self, db_paths):
        """Test parsing EU Regulation HTML documents from Cellar."""
        sources_dir = db_paths['sources'] / 'eu' / 'eurlex' / 'regulations' / 'html'
        results_dir = db_paths['results'] / 'eu' / 'html'
        logs_dir = db_paths['logs']

        # Find downloaded HTML files
        html_files = []
        if sources_dir.exists():
            for subdir in sources_dir.iterdir():
                if subdir.is_dir():
                    html_files.extend(list(subdir.glob('*.html')))

        if not html_files:
            pytest.skip("No EU regulation HTML files found - run client e2e tests first")

        # Test parsing the first available file
        html_file = html_files[0]
        subdir_name = html_file.parent.name
        expected_output = results_dir / f"{subdir_name}_{html_file.stem}.json"

        from tulit.parser.html.cellar.cellar import CellarHTMLParser
        parser = CellarHTMLParser()

        # Parse the file
        parser.parse(str(html_file))

        # Verify parsing results
        assert parser.preface is not None, "Preface should be extracted"
        assert parser.formula is not None, "Formula should be extracted"
        assert isinstance(parser.citations, list), "Citations should be a list"
        assert isinstance(parser.recitals, list), "Recitals should be a list"
        assert isinstance(parser.chapters, list), "Chapters should be a list"
        assert isinstance(parser.articles, list), "Articles should be a list"

        # Save results
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

        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"

    @pytest.mark.slow
    def test_formex_parsing(self, db_paths):
        """Test parsing FORMEX XML documents."""
        sources_dir = db_paths['sources'] / 'eu' / 'eurlex' / 'formex'
        results_dir = db_paths['results'] / 'eu' / 'formex'
        logs_dir = db_paths['logs']

        # Find downloaded FORMEX files
        formex_files = []
        if sources_dir.exists():
            for subdir in sources_dir.iterdir():
                if subdir.is_dir():
                    for doc_dir in subdir.iterdir():
                        if doc_dir.is_dir() and doc_dir.name.startswith('DOC_'):
                            formex_files.extend(list(doc_dir.glob('*.fmx.xml')))

        if not formex_files:
            pytest.skip("No FORMEX files found - run client e2e tests first")

        # Test parsing the first available file
        formex_file = formex_files[0]
        subdir_name = formex_file.parent.parent.name
        expected_output = results_dir / f"{subdir_name}_{formex_file.stem}.json"

        from tulit.parser.xml.formex import Formex4Parser
        parser = Formex4Parser()

        # Parse the file
        parser.parse(str(formex_file))

        # Verify parsing results
        assert parser.preface is not None, "Preface should be extracted"
        assert parser.formula is not None, "Formula should be extracted"
        assert isinstance(parser.citations, list), "Citations should be a list"
        assert isinstance(parser.recitals, list), "Recitals should be a list"
        assert isinstance(parser.chapters, list), "Chapters should be a list"
        assert isinstance(parser.articles, list), "Articles should be a list"

        # Save results
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

        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"

    @pytest.mark.slow
    def test_akn_parsing(self, db_paths):
        """Test parsing Akoma Ntoso XML documents."""
        sources_dir = db_paths['sources'] / 'eu' / 'eurlex' / 'akn'
        results_dir = db_paths['results'] / 'eu' / 'akn'
        logs_dir = db_paths['logs']

        # Find downloaded AKN files
        akn_files = []
        if sources_dir.exists():
            akn_files.extend(list(sources_dir.glob('*.akn')))
            akn_files.extend(list(sources_dir.glob('*.xml')))

        if not akn_files:
            pytest.skip("No AKN files found - run client e2e tests first")

        # Test parsing the first available file
        akn_file = akn_files[0]
        expected_output = results_dir / f"{akn_file.stem}.json"

        from tulit.parser.xml.akomantoso import create_akn_parser
        parser = create_akn_parser(file_path=str(akn_file))

        # Parse the file
        parser.parse(str(akn_file))

        # Verify parsing results
        assert parser.preface is not None, "Preface should be extracted"
        assert parser.formula is not None, "Formula should be extracted"
        assert isinstance(parser.citations, list), "Citations should be a list"
        assert isinstance(parser.recitals, list), "Recitals should be a list"
        assert isinstance(parser.chapters, list), "Chapters should be a list"
        assert isinstance(parser.articles, list), "Articles should be a list"

        # Save results
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

        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"

    @pytest.mark.slow
    def test_finland_finlex_parsing(self, db_paths):
        """Test parsing Finland Finlex XML documents."""
        sources_dir = db_paths['sources'] / 'member_states' / 'finland' / 'finlex'
        results_dir = db_paths['results'] / 'member_states' / 'finland'
        logs_dir = db_paths['logs']

        # Find downloaded XML files
        xml_files = list(sources_dir.glob('*.xml'))
        if not xml_files:
            pytest.skip("No Finland Finlex XML files found - run client e2e tests first")

        # Test parsing the first available file
        xml_file = xml_files[0]
        expected_output = results_dir / f"{xml_file.stem}.json"

        from tulit.parser.xml.akomantoso import create_akn_parser
        parser = create_akn_parser(file_path=str(xml_file))

        # Parse the file
        parser.parse(str(xml_file))

        # Verify parsing results
        assert parser.preface is not None, "Preface should be extracted"
        assert parser.formula is not None, "Formula should be extracted"
        assert isinstance(parser.citations, list), "Citations should be a list"
        assert isinstance(parser.recitals, list), "Recitals should be a list"
        assert isinstance(parser.chapters, list), "Chapters should be a list"
        assert isinstance(parser.articles, list), "Articles should be a list"

        # Save results
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

        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"

    @pytest.mark.slow
    def test_germany_legislation_parsing(self, db_paths):
        """Test parsing German LegalDocML documents."""
        sources_dir = db_paths['sources'] / 'member_states' / 'germany' / 'gesetze' / 'legislation'
        results_dir = db_paths['results'] / 'member_states' / 'germany' / 'legislation'
        logs_dir = db_paths['logs']

        # Find downloaded XML files
        xml_files = list(sources_dir.glob('*.xml'))
        if not xml_files:
            pytest.skip("No German legislation XML files found - run client e2e tests first")

        # Test parsing the first available file
        xml_file = xml_files[0]
        expected_output = results_dir / f"{xml_file.stem}.json"

        from tulit.parser.xml.akomantoso.german import GermanLegalDocMLParser
        parser = GermanLegalDocMLParser()

        # Parse the file
        parser.parse(str(xml_file))

        # Verify parsing results
        assert parser.preface is not None, "Preface should be extracted"
        assert parser.formula is not None, "Formula should be extracted"
        assert isinstance(parser.citations, list), "Citations should be a list"
        assert isinstance(parser.recitals, list), "Recitals should be a list"
        assert isinstance(parser.chapters, list), "Chapters should be a list"
        assert isinstance(parser.articles, list), "Articles should be a list"

        # Save results
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

        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"

    @pytest.mark.slow
    def test_france_legifrance_parsing(self, db_paths):
        """Test parsing France Legifrance JSON documents."""
        sources_dir = db_paths['sources'] / 'member_states' / 'france' / 'legifrance'
        results_dir = db_paths['results'] / 'member_states' / 'france'
        logs_dir = db_paths['logs']

        # Find downloaded JSON files
        json_files = list(sources_dir.glob('*.json'))
        if not json_files:
            pytest.skip("No France Legifrance JSON files found - run client e2e tests first")

        # Test parsing the first available file
        json_file = json_files[0]
        expected_output = results_dir / f"{json_file.stem}.json"

        from tulit.parser.json.legifrance import LegifranceParser
        parser = LegifranceParser(log_dir=str(logs_dir))

        # Parse the file
        output_data = parser.parse_file(str(json_file))

        # Verify parsing results
        assert isinstance(output_data, dict), "Output should be a dictionary"
        assert len(output_data) > 0, "Output should not be empty"

        # Save results (Legifrance parser already returns the data structure)
        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"

    @pytest.mark.slow
    def test_italy_normattiva_parsing(self, db_paths):
        """Test parsing Italy Normattiva XML documents."""
        sources_dir = db_paths['sources'] / 'member_states' / 'italy' / 'normattiva'
        results_dir = db_paths['results'] / 'member_states' / 'italy'
        logs_dir = db_paths['logs']

        # Find downloaded XML files
        xml_files = list(sources_dir.glob('*.xml'))
        if not xml_files:
            pytest.skip("No Italy Normattiva XML files found - run client e2e tests first")

        # Test parsing the first available file
        xml_file = xml_files[0]
        expected_output = results_dir / f"{xml_file.stem}.json"

        from tulit.parser.xml.akomantoso import create_akn_parser
        parser = create_akn_parser(file_path=str(xml_file))

        # Parse the file
        parser.parse(str(xml_file))

        # Verify parsing results
        assert parser.preface is not None, "Preface should be extracted"
        assert parser.formula is not None, "Formula should be extracted"
        assert isinstance(parser.citations, list), "Citations should be a list"
        assert isinstance(parser.recitals, list), "Recitals should be a list"
        assert isinstance(parser.chapters, list), "Chapters should be a list"
        assert isinstance(parser.articles, list), "Articles should be a list"

        # Save results
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

        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"

    @pytest.mark.slow
    def test_luxembourg_legilux_parsing(self, db_paths):
        """Test parsing Luxembourg Legilux XML documents."""
        sources_dir = db_paths['sources'] / 'member_states' / 'luxembourg' / 'legilux'
        results_dir = db_paths['results'] / 'member_states' / 'luxembourg'
        logs_dir = db_paths['logs']

        # Find downloaded XML files
        xml_files = list(sources_dir.glob('*.xml'))
        if not xml_files:
            pytest.skip("No Luxembourg Legilux XML files found - run client e2e tests first")

        # Test parsing the first available file
        xml_file = xml_files[0]
        expected_output = results_dir / f"{xml_file.stem}.json"

        from tulit.parser.xml.akomantoso import create_akn_parser
        parser = create_akn_parser(file_path=str(xml_file))

        # Parse the file
        parser.parse(str(xml_file))

        # Verify parsing results
        assert parser.preface is not None, "Preface should be extracted"
        assert parser.formula is not None, "Formula should be extracted"
        assert isinstance(parser.citations, list), "Citations should be a list"
        assert isinstance(parser.recitals, list), "Recitals should be a list"
        assert isinstance(parser.chapters, list), "Chapters should be a list"
        assert isinstance(parser.articles, list), "Articles should be a list"

        # Save results
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

        expected_output.parent.mkdir(parents=True, exist_ok=True)
        with open(expected_output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Verify output file was created
        assert expected_output.exists(), f"Output file not created: {expected_output}"

    @pytest.mark.slow
    def test_portugal_dre_parsing(self, db_paths):
        """Test parsing Portugal DRE HTML documents."""
        sources_dir = db_paths['sources'] / 'member_states' / 'portugal' / 'dre'
        results_dir = db_paths['results'] / 'member_states' / 'portugal'
        logs_dir = db_paths['logs']

        # Find downloaded HTML files
        html_files = list(sources_dir.glob('*.html'))
        if not html_files:
            pytest.skip("No Portugal DRE HTML files found - run client e2e tests first")

        # Portugal DRE uses HTML format that needs a specific parser
        # For now, skip until HTML parser is implemented
        pytest.skip("Portugal DRE HTML parsing not yet implemented - requires specific HTML parser")