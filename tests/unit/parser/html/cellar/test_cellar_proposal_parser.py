import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from tulit.parser.html.cellar.proposal import ProposalHTMLParser
from tests.conftest import locate_data_dir

DATA_DIR = locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "commission_proposals"
FILE_PATH_COM6 = str(DATA_DIR / "COM(2025)6.html")
FILE_PATH_COM43 = str(DATA_DIR / "COM(2025)43.html")
FILE_PATH_COM1 = str(DATA_DIR / "COM(2025)1.html")


@pytest.fixture
def proposal_parser():
    """Returns a fresh ProposalHTMLParser instance."""
    return ProposalHTMLParser()


@pytest.fixture
def parser_with_root(proposal_parser):
    """Returns a parser with root loaded from COM(2025)6.html."""
    if not os.path.exists(FILE_PATH_COM6):
        pytest.skip(f"Test file not found at {FILE_PATH_COM6}")
    proposal_parser.get_root(FILE_PATH_COM6)
    return proposal_parser


class TestProposalHTMLParser:
    """Test suite for ProposalHTMLParser."""

    def test_init(self, proposal_parser):
        """Test ProposalHTMLParser initialization."""
        assert proposal_parser is not None
        assert isinstance(proposal_parser, ProposalHTMLParser)
        assert proposal_parser.metadata == {}
        assert proposal_parser.explanatory_memorandum == {}
        assert proposal_parser.article_strategy is not None

    def test_get_root(self, proposal_parser):
        """Test get_root loads HTML file."""
        if not os.path.exists(FILE_PATH_COM6):
            pytest.skip(f"Test file not found at {FILE_PATH_COM6}")
        proposal_parser.get_root(FILE_PATH_COM6)
        assert proposal_parser.root is not None

    def test_get_metadata_institution(self, proposal_parser, tmp_path):
        """Test get_metadata extracts institution name."""
        html_file = tmp_path / "metadata_inst.html"
        html_file.write_text(
            '<html><body><p class="Logo">EUROPEAN COMMISSION</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_metadata()
        
        assert 'institution' in proposal_parser.metadata
        assert proposal_parser.metadata['institution'] == 'EUROPEAN COMMISSION'

    def test_get_metadata_emission_date(self, proposal_parser, tmp_path):
        """Test get_metadata extracts emission date."""
        html_file = tmp_path / "metadata_date.html"
        html_file.write_text(
            '<html><body><p class="Emission">Brussels, 15.1.2025</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_metadata()
        
        assert 'emission_date' in proposal_parser.metadata
        assert 'Brussels' in proposal_parser.metadata['emission_date']

    def test_get_metadata_com_reference(self, proposal_parser, tmp_path):
        """Test get_metadata extracts COM reference number."""
        html_file = tmp_path / "metadata_com.html"
        html_file.write_text(
            '<html><body><p class="Rfrenceinstitutionnelle">COM(2025) 6 final</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_metadata()
        
        assert 'com_reference' in proposal_parser.metadata
        assert 'COM(2025)' in proposal_parser.metadata['com_reference']

    def test_get_metadata_interinstitutional_ref(self, proposal_parser, tmp_path):
        """Test get_metadata extracts interinstitutional reference."""
        html_file = tmp_path / "metadata_interinst.html"
        html_file.write_text(
            '<html><body><p class="Rfrenceinterinstitutionnelle">2025/0001(COD)</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_metadata()
        
        assert 'interinstitutional_reference' in proposal_parser.metadata

    def test_get_metadata_status(self, proposal_parser, tmp_path):
        """Test get_metadata extracts proposal status."""
        html_file = tmp_path / "metadata_status.html"
        html_file.write_text(
            '<html><body><p class="Statut">Proposal for a</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_metadata()
        
        assert 'status' in proposal_parser.metadata
        assert proposal_parser.metadata['status'] == 'Proposal for a'

    def test_get_metadata_document_type(self, proposal_parser, tmp_path):
        """Test get_metadata extracts document type."""
        html_file = tmp_path / "metadata_doctype.html"
        html_file.write_text(
            '<html><body><p class="Typedudocument_cp">COUNCIL DECISION</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_metadata()
        
        assert 'document_type' in proposal_parser.metadata
        assert proposal_parser.metadata['document_type'] == 'COUNCIL DECISION'

    def test_get_metadata_title(self, proposal_parser, tmp_path):
        """Test get_metadata extracts document title."""
        html_file = tmp_path / "metadata_title.html"
        html_file.write_text(
            '<html><body><p class="Titreobjet_cp">on establishing the Digital Decade Programme</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_metadata()
        
        assert 'title' in proposal_parser.metadata
        assert 'Digital Decade' in proposal_parser.metadata['title']

    def test_get_metadata_full(self, parser_with_root):
        """Test get_metadata with real COM document."""
        parser_with_root.get_metadata()
        assert 'com_reference' in parser_with_root.metadata

    def test_get_metadata_exception_handling(self, proposal_parser):
        """Test get_metadata handles exceptions gracefully."""
        proposal_parser.root = None
        proposal_parser.get_metadata()
        # Should not raise exception

    def test_get_deepest_subsection_em_no_content(self, proposal_parser):
        """Test _get_deepest_subsection_em with empty section."""
        section = {'level': 1, 'content': []}
        result = proposal_parser._get_deepest_subsection_em(section)
        assert result == section

    def test_get_deepest_subsection_em_with_level2(self, proposal_parser):
        """Test _get_deepest_subsection_em returns level 2 subsection."""
        section = {
            'level': 1,
            'content': [
                {'level': 2, 'content': []}
            ]
        }
        result = proposal_parser._get_deepest_subsection_em(section)
        assert result['level'] == 2

    def test_get_deepest_subsection_em_with_level3(self, proposal_parser):
        """Test _get_deepest_subsection_em returns level 3 subsection."""
        section = {
            'level': 1,
            'content': [
                {
                    'level': 2,
                    'content': [
                        {'level': 3, 'content': []}
                    ]
                }
            ]
        }
        result = proposal_parser._get_deepest_subsection_em(section)
        assert result['level'] == 3

    def test_process_heading_level1_em(self, proposal_parser, tmp_path):
        """Test _process_heading_level1_em extracts section heading."""
        html_file = tmp_path / "heading1.html"
        html_file.write_text(
            '<html><body><div><span class="num">1.</span><span>Introduction</span></div></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('div')
        
        result = proposal_parser._process_heading_level1_em(element, None, [])
        
        assert result['level'] == 1
        assert result['number'] == '1.'
        assert 'Introduction' in result['heading']

    def test_process_heading_level1_em_no_num(self, proposal_parser, tmp_path):
        """Test _process_heading_level1_em without number span."""
        html_file = tmp_path / "heading1_no_num.html"
        html_file.write_text(
            '<html><body><div><span>Unnumbered Section</span></div></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('div')
        
        result = proposal_parser._process_heading_level1_em(element, None, [])
        
        assert result['number'] is None
        assert 'Unnumbered Section' in result['heading']

    def test_process_heading_level2_em(self, proposal_parser, tmp_path):
        """Test _process_heading_level2_em extracts subsection."""
        html_file = tmp_path / "heading2.html"
        html_file.write_text(
            '<html><body><div><span class="num">1.1</span><span>Background</span></div></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('div')
        
        result = proposal_parser._process_heading_level2_em(element)
        
        assert result['level'] == 2
        assert result['number'] == '1.1'
        assert 'Background' in result['heading']

    def test_process_heading_level3_em(self, proposal_parser, tmp_path):
        """Test _process_heading_level3_em extracts subsection."""
        html_file = tmp_path / "heading3.html"
        html_file.write_text(
            '<html><body><div><span class="num">1.1.1</span><span>Details</span></div></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('div')
        
        result = proposal_parser._process_heading_level3_em(element)
        
        assert result['level'] == 3
        assert result['number'] == '1.1.1'

    def test_process_numbered_paragraph_em(self, proposal_parser, tmp_path):
        """Test _process_numbered_paragraph_em extracts paragraph."""
        html_file = tmp_path / "num_para.html"
        html_file.write_text(
            '<html><body><p><span class="num">(1)</span> First paragraph text</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('p')
        
        result = proposal_parser._process_numbered_paragraph_em(element)
        
        assert result['type'] == 'numbered_paragraph'
        assert result['number'] == '(1)'
        assert 'First paragraph' in result['text']

    def test_process_numbered_paragraph_em_no_num(self, proposal_parser, tmp_path):
        """Test _process_numbered_paragraph_em without number."""
        html_file = tmp_path / "para_no_num.html"
        html_file.write_text(
            '<html><body><p>Paragraph without number</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('p')
        
        result = proposal_parser._process_numbered_paragraph_em(element)
        
        assert result['number'] is None
        assert 'Paragraph without number' in result['text']

    def test_process_normal_paragraph_em(self, proposal_parser, tmp_path):
        """Test _process_normal_paragraph_em extracts text."""
        html_file = tmp_path / "normal_para.html"
        html_file.write_text(
            '<html><body><p>Normal paragraph text</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('p')
        
        result = proposal_parser._process_normal_paragraph_em(element)
        
        assert result['type'] == 'paragraph'
        assert 'Normal paragraph' in result['text']

    def test_process_normal_paragraph_em_empty(self, proposal_parser, tmp_path):
        """Test _process_normal_paragraph_em with empty paragraph."""
        html_file = tmp_path / "empty_para.html"
        html_file.write_text(
            '<html><body><p></p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('p')
        
        result = proposal_parser._process_normal_paragraph_em(element)
        
        assert result is None

    def test_process_table_em(self, proposal_parser, tmp_path):
        """Test _process_table_em extracts table data."""
        html_file = tmp_path / "table.html"
        html_file.write_text(
            '''<html><body><table>
                <tr><td>Cell 1</td><td>Cell 2</td></tr>
                <tr><td>Cell 3</td><td>Cell 4</td></tr>
            </table></body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('table')
        
        result = proposal_parser._process_table_em(element)
        
        assert result['type'] == 'table'
        assert len(result['data']) == 2
        assert result['data'][0] == ['Cell 1', 'Cell 2']

    def test_process_table_em_empty(self, proposal_parser, tmp_path):
        """Test _process_table_em with empty table."""
        html_file = tmp_path / "empty_table.html"
        html_file.write_text(
            '<html><body><table><tr><td></td></tr></table></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('table')
        
        result = proposal_parser._process_table_em(element)
        
        assert result is None

    def test_add_content_to_section_em(self, proposal_parser):
        """Test _add_content_to_section_em adds content."""
        section = {'level': 1, 'content': []}
        content_item = {'type': 'paragraph', 'text': 'Test'}
        
        proposal_parser._add_content_to_section_em(section, content_item)
        
        assert len(section['content']) == 1
        assert section['content'][0] == content_item

    def test_add_content_to_section_em_none(self, proposal_parser):
        """Test _add_content_to_section_em with None section."""
        proposal_parser._add_content_to_section_em(None, {'text': 'test'})
        # Should not raise exception

    def test_get_preface_success(self, parser_with_root):
        """Test get_preface extracts preface."""
        parser_with_root.get_preface()
        assert parser_with_root.preface is not None

    def test_parse_full_workflow_com6(self, proposal_parser):
        """Test full parse with COM(2025)6."""
        if not os.path.exists(FILE_PATH_COM6):
            pytest.skip(f"Test file not found at {FILE_PATH_COM6}")
        result = proposal_parser.parse(FILE_PATH_COM6)
        assert result is not None
        assert proposal_parser.metadata is not None

    def test_parse_full_workflow_com1(self, proposal_parser):
        """Test full parse with COM(2025)1."""
        if not os.path.exists(FILE_PATH_COM1):
            pytest.skip(f"Test file not found at {FILE_PATH_COM1}")
        result = proposal_parser.parse(FILE_PATH_COM1)
        assert result is not None

    def test_parse_full_workflow_com43(self, proposal_parser):
        """Test full parse with COM(2025)43."""
        if not os.path.exists(FILE_PATH_COM43):
            pytest.skip(f"Test file not found at {FILE_PATH_COM43}")
        result = proposal_parser.parse(FILE_PATH_COM43)
        assert result is not None

    def test_parse_calls_get_metadata(self, proposal_parser, tmp_path):
        """Test parse calls get_metadata."""
        html_file = tmp_path / "simple.html"
        html_file.write_text(
            '<html><body><p class="Logo">TEST</p></body></html>',
            encoding='utf-8'
        )
        
        with patch.object(proposal_parser, 'get_metadata') as mock_metadata:
            proposal_parser.parse(str(html_file))
            mock_metadata.assert_called_once()

    def test_parse_calls_get_preface(self, proposal_parser, tmp_path):
        """Test parse calls get_preface."""
        html_file = tmp_path / "simple.html"
        html_file.write_text('<html><body></body></html>', encoding='utf-8')
        
        with patch.object(proposal_parser, 'get_preface') as mock_preface:
            proposal_parser.parse(str(html_file))
            mock_preface.assert_called_once()

    def test_get_explanatory_memorandum_title(self, proposal_parser, tmp_path):
        """Test get_explanatory_memorandum extracts title."""
        html_file = tmp_path / "em_title.html"
        html_file.write_text(
            '<html><body><p class="Exposdesmotifstitre">EXPLANATORY MEMORANDUM</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_explanatory_memorandum()
        
        assert 'title' in proposal_parser.explanatory_memorandum
        assert 'EXPLANATORY' in proposal_parser.explanatory_memorandum['title']

    def test_get_explanatory_memorandum_with_sections(self, proposal_parser, tmp_path):
        """Test get_explanatory_memorandum with sections."""
        html_file = tmp_path / "em_sections.html"
        html_file.write_text(
            '''<html><body>
                <p class="Exposdesmotifstitre">EXPLANATORY MEMORANDUM</p>
                <div class="content">
                    <p class="li ManualHeading1"><span class="num">1.</span><span>Introduction</span></p>
                    <p class="Normal">Some text</p>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_explanatory_memorandum()
        
        assert 'sections' in proposal_parser.explanatory_memorandum
        assert len(proposal_parser.explanatory_memorandum['sections']) > 0

    def test_get_explanatory_memorandum_exception(self, proposal_parser):
        """Test get_explanatory_memorandum handles exceptions."""
        proposal_parser.root = None
        proposal_parser.get_explanatory_memorandum()
        # Should not raise exception

    def test_get_preface_multiple_status(self, proposal_parser, tmp_path):
        """Test get_preface uses second status occurrence."""
        html_file = tmp_path / "multiple_status.html"
        html_file.write_text(
            '''<html><body>
                <p class="Statut">First status</p>
                <p class="Statut">Second status</p>
                <p class="Typedudocument">DIRECTIVE</p>
                <p class="Titreobjet">on something</p>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_preface()
        
        assert 'Second status' in proposal_parser.preface

    def test_get_preface_single_status(self, proposal_parser, tmp_path):
        """Test get_preface uses first status when only one."""
        html_file = tmp_path / "single_status.html"
        html_file.write_text(
            '''<html><body>
                <p class="Statut">Only status</p>
                <p class="Typedudocument">REGULATION</p>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_preface()
        
        assert 'Only status' in proposal_parser.preface
        assert 'REGULATION' in proposal_parser.preface

    def test_get_preface_empty(self, proposal_parser, tmp_path):
        """Test get_preface with no elements."""
        html_file = tmp_path / "no_preface.html"
        html_file.write_text('<html><body></body></html>', encoding='utf-8')
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_preface()
        
        assert proposal_parser.preface is None

    def test_get_preamble_success(self, proposal_parser, tmp_path):
        """Test get_preamble always sets preamble to None for proposals."""
        html_file = tmp_path / "preamble.html"
        html_file.write_text(
            '''<html><body>
                <p class="Rfrenceinterinstitutionnelle">First ref</p>
                <div class="content">
                    <p class="Rfrenceinterinstitutionnelle">Second ref</p>
                    <p>Preamble content</p>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_preamble()
        assert proposal_parser.preamble is None

    def test_get_preamble_single_ref(self, proposal_parser, tmp_path):
        """Test get_preamble with only one reference."""
        html_file = tmp_path / "single_ref.html"
        html_file.write_text(
            '<html><body><p class="Rfrenceinterinstitutionnelle">Only ref</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_preamble()
        
        assert proposal_parser.preamble is None

    def test_get_formula_success(self, proposal_parser, tmp_path):
        """Test get_formula extracts institution."""
        html_file = tmp_path / "formula.html"
        html_file.write_text(
            '''<html><body><div class="content">
                <p class="Institutionquiagit">THE EUROPEAN PARLIAMENT AND THE COUNCIL,</p>
            </div></body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.preamble = proposal_parser.root.find('div', class_='content')
        proposal_parser.get_formula()
        
        assert proposal_parser.formula is not None
        assert 'EUROPEAN PARLIAMENT' in proposal_parser.formula

    def test_get_formula_no_preamble(self, proposal_parser):
        """Test get_formula with no preamble."""
        proposal_parser.preamble = None
        proposal_parser.get_formula()
        
        assert proposal_parser.formula is None

    def test_get_citations_success(self, proposal_parser, tmp_path):
        """Test get_citations extracts citations."""
        html_file = tmp_path / "citations.html"
        html_file.write_text(
            '''<html><body>
                <p class="Institutionquiagit">THE COUNCIL,</p>
                <p class="Normal">Having regard to the Treaty</p>
                <p class="Normal">Having regard to Regulation (EU) No 123/2024</p>
                <p class="Normal">Whereas:</p>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_citations()
        
        assert len(proposal_parser.citations) == 2
        assert 'Treaty' in proposal_parser.citations[0]['text']

    def test_get_citations_no_formula(self, proposal_parser, tmp_path):
        """Test get_citations with no formula element."""
        html_file = tmp_path / "no_formula.html"
        html_file.write_text('<html><body><p>No formula here</p></body></html>', encoding='utf-8')
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_citations()
        
        assert proposal_parser.citations == []

    def test_get_citations_stops_at_whereas(self, proposal_parser, tmp_path):
        """Test get_citations stops at Whereas:."""
        html_file = tmp_path / "whereas_stop.html"
        html_file.write_text(
            '''<html><body>
                <p class="Institutionquiagit">THE COUNCIL,</p>
                <p class="Normal">Having regard to something</p>
                <p class="Normal">Whereas:</p>
                <p class="Normal">Having regard to this should not be included</p>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_citations()
        
        assert len(proposal_parser.citations) == 1

    def test_get_recitals_success(self, proposal_parser, tmp_path):
        """Test get_recitals extracts recitals."""
        html_file = tmp_path / "recitals.html"
        html_file.write_text(
            '''<html><body>
                <p class="li ManualConsidrant"><span class="num">(1)</span> First recital text</p>
                <p class="li ManualConsidrant"><span class="num">(2)</span> Second recital text</p>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_recitals()
        
        assert len(proposal_parser.recitals) == 2
        assert proposal_parser.recitals[0]['num'] == '(1)'
        assert 'First recital' in proposal_parser.recitals[0]['text']

    def test_get_recitals_no_num(self, proposal_parser, tmp_path):
        """Test get_recitals without number span."""
        html_file = tmp_path / "recital_no_num.html"
        html_file.write_text(
            '<html><body><p class="li ManualConsidrant">Unnumbered recital</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_recitals()
        
        assert len(proposal_parser.recitals) == 1
        assert proposal_parser.recitals[0]['num'] is None

    def test_get_preamble_final_success(self, proposal_parser, tmp_path):
        """Test get_preamble_final extracts adoption formula."""
        html_file = tmp_path / "preamble_final.html"
        html_file.write_text(
            '''<html><body><div class="content">
                <p class="Formuledadoption">HAS ADOPTED THIS DECISION:</p>
            </div></body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.preamble = proposal_parser.root.find('div', class_='content')
        proposal_parser.get_preamble_final()
        
        assert 'HAS ADOPTED' in proposal_parser.preamble_final

    def test_get_preamble_final_no_preamble(self, proposal_parser):
        """Test get_preamble_final with no preamble."""
        proposal_parser.preamble = None
        proposal_parser.get_preamble_final()
        
        assert proposal_parser.preamble_final is None

    def test_get_body_success(self, proposal_parser, tmp_path):
        """Test get_body finds body element."""
        html_file = tmp_path / "body.html"
        html_file.write_text(
            '''<html><body><div class="content">
                <p class="Formuledadoption">HAS ADOPTED:</p>
                <p>Body content</p>
            </div></body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.preamble = proposal_parser.root.find('div', class_='content')
        proposal_parser.get_body()
        
        assert proposal_parser.body is not None

    def test_get_body_no_preamble(self, proposal_parser):
        """Test get_body with no preamble."""
        proposal_parser.preamble = None
        proposal_parser.get_body()
        
        assert proposal_parser.body is None

    def test_is_after_fait_true(self, proposal_parser, tmp_path):
        """Test _is_after_fait returns True when article after fait."""
        html_file = tmp_path / "fait_order.html"
        html_file.write_text(
            '''<html><body>
                <p id="fait">Fait</p>
                <p id="article">Article</p>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        fait_elem = proposal_parser.root.find('p', id='fait')
        article_elem = proposal_parser.root.find('p', id='article')
        
        result = proposal_parser._is_after_fait(article_elem, fait_elem)
        assert result is True

    def test_is_after_fait_false(self, proposal_parser, tmp_path):
        """Test _is_after_fait returns False when article before fait."""
        html_file = tmp_path / "fait_order2.html"
        html_file.write_text(
            '''<html><body>
                <p id="article">Article</p>
                <p id="fait">Fait</p>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        fait_elem = proposal_parser.root.find('p', id='fait')
        article_elem = proposal_parser.root.find('p', id='article')
        
        result = proposal_parser._is_after_fait(article_elem, fait_elem)
        assert result is False

    def test_extract_article_number_and_heading_with_br(self, proposal_parser, tmp_path):
        """Test _extract_article_number_and_heading splits by br."""
        html_file = tmp_path / "article_br.html"
        html_file.write_text(
            '<html><body><p><span>Article 1</span><br/><span>Scope</span></p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('p')
        
        num, heading = proposal_parser._extract_article_number_and_heading(element)
        
        assert 'Article 1' in num
        assert heading == 'Scope'

    def test_extract_article_number_and_heading_no_br(self, proposal_parser, tmp_path):
        """Test _extract_article_number_and_heading without br."""
        html_file = tmp_path / "article_no_br.html"
        html_file.write_text(
            '<html><body><p>Article 2</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        element = proposal_parser.root.find('p')
        
        num, heading = proposal_parser._extract_article_number_and_heading(element)
        
        assert 'Article 2' in num
        assert heading is None

    def test_generate_article_eid_with_number(self, proposal_parser):
        """Test _generate_article_eid extracts article number."""
        eid = proposal_parser._generate_article_eid("Article 5 - Title", 0)
        assert eid == "005"

    def test_generate_article_eid_without_number(self, proposal_parser):
        """Test _generate_article_eid uses index when no number."""
        eid = proposal_parser._generate_article_eid("Something else", 3)
        assert eid == "003"

    def test_try_extract_heading_from_next_paragraph(self, proposal_parser, tmp_path):
        """Test _try_extract_heading_from_next_paragraph is not implemented (skip)."""
        import pytest
        pytest.skip("_try_extract_heading_from_next_paragraph is not implemented in ProposalHTMLParser.")

    def test_try_extract_heading_no_following_paragraph(self, proposal_parser, tmp_path):
        """Test _try_extract_heading_from_next_paragraph is not implemented (skip)."""
        import pytest
        pytest.skip("_try_extract_heading_from_next_paragraph is not implemented in ProposalHTMLParser.")

    def test_concatenate_list_items(self, proposal_parser, tmp_path):
        """Test _concatenate_list_items is not implemented (skip)."""
        import pytest
        pytest.skip("_concatenate_list_items is not implemented in ProposalHTMLParser.")

    def test_process_normal_paragraph(self, proposal_parser, tmp_path):
        """Test _process_normal_paragraph is not implemented (skip)."""
        import pytest
        pytest.skip("_process_normal_paragraph is not implemented in ProposalHTMLParser.")

    def test_process_normal_paragraph_heading_match(self, proposal_parser, tmp_path):
        """Test _process_normal_paragraph is not implemented (skip)."""
        import pytest
        pytest.skip("_process_normal_paragraph is not implemented in ProposalHTMLParser.")

    def test_process_numbered_paragraph(self, proposal_parser, tmp_path):
        """Test _process_numbered_paragraph is not implemented (skip)."""
        import pytest
        pytest.skip("_process_numbered_paragraph is not implemented in ProposalHTMLParser.")

    def test_process_list_item(self, proposal_parser, tmp_path):
        """Test _process_list_item is not implemented (skip)."""
        import pytest
        pytest.skip("_process_list_item is not implemented in ProposalHTMLParser.")

    def test_extract_article_content(self, proposal_parser, tmp_path):
        """Test _extract_article_content is not implemented (skip)."""
        import pytest
        pytest.skip("_extract_article_content is not implemented in ProposalHTMLParser.")

    def test_get_articles_success(self, proposal_parser, tmp_path):
        """Test get_articles extracts articles."""
        html_file = tmp_path / "articles.html"
        html_file.write_text(
            '''<html><body>
                <p class="Titrearticle">Article 1<br/>Title</p>
                <p class="Normal">Content text</p>
                <p class="Titrearticle">Article 2</p>
                <p class="Normal">More content</p>
                <p class="Fait">Done at Brussels</p>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_articles()
        
        assert len(proposal_parser.articles) == 2
        assert proposal_parser.articles[0]['eId'] == '001'

    def test_get_articles_stops_at_fait(self, proposal_parser, tmp_path):
        """Test get_articles stops after fait."""
        html_file = tmp_path / "fait_stop.html"
        html_file.write_text(
            '''<html><body>
                <p class="Titrearticle">Article 1</p>
                <p class="Normal">Content</p>
                <p class="Fait">Done</p>
                <p class="Titrearticle">Article 2</p>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_articles()
        
        assert len(proposal_parser.articles) == 1

    def test_get_articles_exception(self, proposal_parser):
        """Test get_articles handles exception."""
        proposal_parser.root = None
        proposal_parser.get_articles()
        
        assert proposal_parser.articles == []

    def test_get_conclusions_with_fait_and_signature(self, proposal_parser, tmp_path):
        """Test get_conclusions with both fait and signature."""
        html_file = tmp_path / "conclusions.html"
        html_file.write_text(
            '''<html><body>
                <p class="Fait">Done at Brussels, 1 January 2025.</p>
                <div class="signature">For the Council</div>
            </body></html>''',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_conclusions()
        
        assert 'Done at Brussels' in proposal_parser.conclusions
        assert 'For the Council' in proposal_parser.conclusions

    def test_get_conclusions_fait_only(self, proposal_parser, tmp_path):
        """Test get_conclusions with fait only."""
        html_file = tmp_path / "fait_only.html"
        html_file.write_text(
            '<html><body><p class="Fait">Done at Brussels</p></body></html>',
            encoding='utf-8'
        )
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_conclusions()
        
        assert 'Done at Brussels' in proposal_parser.conclusions

    def test_get_conclusions_none(self, proposal_parser, tmp_path):
        """Test get_conclusions with no elements."""
        html_file = tmp_path / "no_conclusions.html"
        html_file.write_text('<html><body></body></html>', encoding='utf-8')
        proposal_parser.get_root(str(html_file))
        proposal_parser.get_conclusions()
        
        assert proposal_parser.conclusions is None
