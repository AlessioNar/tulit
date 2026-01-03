import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from tulit.parser.html.cellar.cellar_standard import CellarStandardHTMLParser


@pytest.fixture
def parser():
    """Returns a fresh CellarStandardHTMLParser instance."""
    return CellarStandardHTMLParser()


@pytest.fixture
def sample_standard_html(tmp_path):
    """Creates a sample standard HTML file with TXT_TE format."""
    html_file = tmp_path / "standard_format.html"
    html_file.write_text(
        '''<html>
        <head>
            <meta name="DC.description" content="Test Regulation"/>
        </head>
        <body>
            <TXT_TE>
                <p>THE COUNCIL OF THE EUROPEAN UNION,</p>
                <p>Having regard to the Treaty</p>
                <p>(1) First recital text</p>
                <p>HAS ADOPTED THIS REGULATION:</p>
                <p>Article 1</p>
                <p>This regulation shall apply.</p>
                <p>Article 2 Definitions</p>
                <p>1. First paragraph of article 2</p>
                <p>2. Second paragraph of article 2</p>
            </TXT_TE>
        </body>
        </html>''',
        encoding='utf-8'
    )
    return str(html_file)


@pytest.fixture
def parser_with_root(parser, sample_standard_html):
    """Returns a parser with root already loaded from test file."""
    parser.get_root(sample_standard_html)
    return parser


class TestCellarStandardHTMLParser:
    """Test suite for CellarStandardHTMLParser."""

    def test_init(self, parser):
        """Test CellarStandardHTMLParser initialization."""
        assert parser is not None
        assert isinstance(parser, CellarStandardHTMLParser)
        assert parser.normalizer is not None
        assert parser.article_strategy is not None

    def test_clean_text(self, parser):
        """Test _clean_text method uses normalizer."""
        text = "Test text with spaces"
        result = parser._clean_text(text)
        assert isinstance(result, str)

    def test_extract_article_number_success(self, parser):
        """Test _extract_article_number extracts article number."""
        text = "Article 1 Some heading"
        num, remaining = parser._extract_article_number(text)
        assert num == "1"
        assert remaining == "Some heading"

    def test_extract_article_number_no_match(self, parser):
        """Test _extract_article_number returns None when no article found."""
        text = "Some random text"
        num, remaining = parser._extract_article_number(text)
        assert num is None
        assert remaining == text

    def test_get_preface_from_meta(self, parser, tmp_path):
        """Test get_preface extracts from meta description."""
        html_file = tmp_path / "meta_preface.html"
        html_file.write_text(
            '<html><head><meta name="DC.description" content="Test preface"/></head><body></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preface()
        
        assert parser.preface == "Test preface"

    def test_get_preface_from_h1(self, parser, tmp_path):
        """Test get_preface extracts from h1 when meta missing."""
        html_file = tmp_path / "h1_preface.html"
        html_file.write_text(
            '<html><body><h1>Test heading</h1></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preface()
        
        assert parser.preface == "Test heading"

    def test_get_preface_from_strong(self, parser, tmp_path):
        """Test get_preface extracts from strong tag when h1 missing."""
        html_file = tmp_path / "strong_preface.html"
        html_file.write_text(
            '<html><body><strong>Strong text</strong></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preface()
        
        assert parser.preface == "Strong text"

    def test_get_preface_none_found(self, parser, tmp_path):
        """Test get_preface returns None when nothing found."""
        html_file = tmp_path / "no_preface.html"
        html_file.write_text(
            '<html><body><p>Just text</p></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preface()
        
        assert parser.preface is None

    def test_get_preface_exception_handling(self, parser):
        """Test get_preface handles exceptions."""
        parser.root = None
        parser.get_preface()
        assert parser.preface is None

    def test_get_preamble_txt_te(self, parser, tmp_path):
        """Test get_preamble extracts TXT_TE container."""
        html_file = tmp_path / "txt_te.html"
        html_file.write_text(
            '<html><body><txt_te>Preamble content</txt_te></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        
        assert parser.preamble is not None
        assert parser.txt_te is not None
        assert parser.is_consolidated is False

    def test_get_preamble_uppercase_txt_te(self, parser, tmp_path):
        """Test get_preamble handles uppercase TXT_TE."""
        html_file = tmp_path / "upper_txt_te.html"
        html_file.write_text(
            '<html><body><TXT_TE>Preamble content</TXT_TE></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        
        assert parser.txt_te is not None
        assert parser.is_consolidated is False

    def test_get_preamble_consolidated_format(self, parser, tmp_path):
        """Test get_preamble raises ValueError when no TXT_TE tag found."""
        html_file = tmp_path / "consolidated.html"
        html_file.write_text(
            '<html><body><p>Consolidated content</p></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        with pytest.raises(ValueError, match="No TXT_TE tag found"):
            parser.get_preamble()

    def test_get_preamble_no_container(self, parser, tmp_path):
        """Test get_preamble raises ValueError when no TXT_TE container found."""
        html_file = tmp_path / "no_container.html"
        html_file.write_text('<html><div></div></html>', encoding='utf-8')
        
        parser.get_root(str(html_file))
        with pytest.raises(ValueError, match="No TXT_TE tag found"):
            parser.get_preamble()

    def test_get_preamble_exception(self, parser):
        """Test get_preamble re-raises exceptions when root is None."""
        parser.root = None
        # When root is None, AttributeError is caught, logged, and re-raised
        with pytest.raises(AttributeError):
            parser.get_preamble()

    def test_get_formula_success(self, parser, tmp_path):
        """Test get_formula extracts formula text."""
        html_file = tmp_path / "formula.html"
        html_file.write_text(
            '<html><body><txt_te><p>THE COUNCIL HAS ADOPTED</p></txt_te></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_formula()
        
        assert parser.formula is not None
        assert "COUNCIL" in parser.formula

    def test_get_formula_commission(self, parser, tmp_path):
        """Test get_formula recognizes COMMISSION pattern."""
        html_file = tmp_path / "formula_commission.html"
        html_file.write_text(
            '<html><body><txt_te><p>THE COMMISSION HAS DECIDED</p></txt_te></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_formula()
        
        assert "COMMISSION" in parser.formula

    def test_get_formula_no_container(self, parser):
        """Test get_formula when txt_te not set."""
        parser.get_formula()
        assert parser.formula is None

    def test_get_formula_not_found(self, parser, tmp_path):
        """Test get_formula when no formula pattern found."""
        html_file = tmp_path / "no_formula.html"
        html_file.write_text(
            '<html><body><txt_te><p>Random text</p></txt_te></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_formula()
        
        assert parser.formula is None

    def test_get_citations_success(self, parser, tmp_path):
        """Test get_citations extracts citation paragraphs."""
        html_file = tmp_path / "citations.html"
        html_file.write_text(
            '''<html><body><txt_te>
                <p>Having regard to the Treaty</p>
                <p>Having considered the proposal</p>
            </txt_te></body></html>''',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_citations()
        
        assert len(parser.citations) == 2
        assert parser.citations[0]['eId'] == 'cit_1'
        assert 'regard' in parser.citations[0]['text']

    def test_get_citations_no_container(self, parser):
        """Test get_citations when txt_te not set."""
        parser.get_citations()
        assert parser.citations == []

    def test_get_citations_empty(self, parser, tmp_path):
        """Test get_citations when no citations found."""
        html_file = tmp_path / "no_citations.html"
        html_file.write_text(
            '<html><body><txt_te><p>Random text</p></txt_te></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_citations()
        
        assert parser.citations == []

    def test_extract_table_recital(self, parser):
        """Test _extract_table_recital extracts numbered recital."""
        recital = parser._extract_table_recital("(1)", "Recital text")
        assert recital is not None
        assert recital['eId'] == 'rct_1'
        assert recital['text'] == "Recital text"

    def test_extract_table_recital_no_match(self, parser):
        """Test _extract_table_recital returns None for non-recital."""
        recital = parser._extract_table_recital("Other", "Text")
        assert recital is None

    def test_extract_recitals_from_tables(self, parser, tmp_path):
        """Test _extract_recitals_from_tables extracts from table format."""
        html_file = tmp_path / "table_recitals.html"
        html_file.write_text(
            '''<html><body><txt_te>
                <table>
                    <tr><td>(1)</td><td>First recital</td></tr>
                    <tr><td>(2)</td><td>Second recital</td></tr>
                </table>
            </txt_te></body></html>''',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        recitals = parser._extract_recitals_from_tables()
        
        assert len(recitals) == 2
        assert recitals[0]['eId'] == 'rct_1'

    def test_is_recitals_start(self, parser):
        """Test _is_recitals_start identifies whereas marker."""
        assert parser._is_recitals_start("Whereas:")
        assert parser._is_recitals_start("  Whereas:  ")
        assert not parser._is_recitals_start("Other text")

    def test_is_recitals_end(self, parser):
        """Test _is_recitals_end identifies end markers."""
        assert parser._is_recitals_end("HAS ADOPTED")
        assert parser._is_recitals_end("Article 1")
        assert not parser._is_recitals_end("Random text")

    def test_extract_numbered_recital(self, parser):
        """Test _extract_numbered_recital extracts from numbered format."""
        recital = parser._extract_numbered_recital("(1) First recital text")
        assert recital is not None
        assert recital['eId'] == 'rct_1'
        assert recital['text'] == "First recital text"

    def test_extract_numbered_recital_no_match(self, parser):
        """Test _extract_numbered_recital returns None for non-match."""
        recital = parser._extract_numbered_recital("Not a recital")
        assert recital is None

    def test_extract_recitals_from_paragraphs(self, parser, tmp_path):
        """Test _extract_recitals_from_paragraphs extracts from text format."""
        html_file = tmp_path / "para_recitals.html"
        html_file.write_text(
            '''<html><body><txt_te>
                <p>Whereas:</p>
                <p>(1) First recital</p>
                <p>(2) Second recital</p>
                <p>HAS ADOPTED</p>
            </txt_te></body></html>''',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        recitals = parser._extract_recitals_from_paragraphs()
        
        assert len(recitals) == 2
        assert recitals[0]['text'] == "First recital"

    def test_get_recitals_from_tables(self, parser, tmp_path):
        """Test get_recitals uses table format when available."""
        html_file = tmp_path / "recitals_table.html"
        html_file.write_text(
            '''<html><body><txt_te>
                <table><tr><td>(1)</td><td>Table recital</td></tr></table>
            </txt_te></body></html>''',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_recitals()
        
        assert len(parser.recitals) > 0

    def test_get_recitals_from_paragraphs_fallback(self, parser, tmp_path):
        """Test get_recitals falls back to paragraph format."""
        html_file = tmp_path / "recitals_para.html"
        html_file.write_text(
            '''<html><body><txt_te>
                <p>Whereas:</p>
                <p>(1) Para recital</p>
            </txt_te></body></html>''',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_recitals()
        
        assert len(parser.recitals) > 0

    def test_get_recitals_no_container(self, parser):
        """Test get_recitals when txt_te not set."""
        parser.get_recitals()
        assert parser.recitals == []

    def test_get_preamble_final_success(self, parser, tmp_path):
        """Test get_preamble_final extracts HAS ADOPTED text."""
        html_file = tmp_path / "preamble_final.html"
        html_file.write_text(
            '<html><body><txt_te><p>HAS ADOPTED THIS DECISION:</p></txt_te></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_preamble_final()
        
        assert "ADOPTED" in parser.preamble_final

    def test_get_preamble_final_not_found(self, parser, tmp_path):
        """Test get_preamble_final when not found."""
        html_file = tmp_path / "no_final.html"
        html_file.write_text(
            '<html><body><txt_te><p>Other text</p></txt_te></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_preamble_final()
        
        assert parser.preamble_final is None

    def test_get_body_success(self, parser, tmp_path):
        """Test get_body sets body to txt_te."""
        html_file = tmp_path / "body.html"
        html_file.write_text(
            '<html><body><txt_te>Body content</txt_te></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_body()
        
        assert parser.body is not None

    def test_get_body_no_txt_te(self, parser):
        """Test get_body when txt_te not set."""
        parser.get_body()
        assert parser.body is None

    def test_get_chapters(self, parser):
        """Test get_chapters returns empty list for standard format."""
        parser.get_chapters()
        assert parser.chapters == []

    def test_get_articles_uses_strategy(self, parser, tmp_path):
        """Test get_articles uses CellarStandardArticleStrategy."""
        html_file = tmp_path / "articles.html"
        html_file.write_text(
            '''<html><body><txt_te>
                <p>Article 1</p>
                <p>Article content</p>
            </txt_te></body></html>''',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        
        with patch.object(parser.article_strategy, 'extract_articles', return_value=[]) as mock_extract:
            parser.get_articles()
            mock_extract.assert_called_once()

    def test_get_articles_no_container(self, parser):
        """Test get_articles when txt_te not set."""
        parser.get_articles()
        assert parser.articles == []

    def test_is_signature_section(self, parser):
        """Test _is_signature_section identifies signature patterns."""
        assert parser._is_signature_section("Done at Brussels")
        assert parser._is_signature_section("For the Commission")
        assert parser._is_signature_section("Member of the Commission")
        assert not parser._is_signature_section("Regular text")

    def test_is_footnote(self, parser):
        """Test _is_footnote identifies footnote references."""
        assert parser._is_footnote("(1) OJ L 123")
        assert not parser._is_footnote("(1) Regular text")
        assert not parser._is_footnote("Other text")

    def test_extract_table_text(self, parser, tmp_path):
        """Test _extract_table_text extracts table content."""
        html_file = tmp_path / "table.html"
        html_file.write_text(
            '''<html><body><table>
                <tr><td>Cell 1</td><td>Cell 2</td></tr>
                <tr><td>Cell 3</td><td>Cell 4</td></tr>
            </table></body></html>''',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        table = parser.root.find('table')
        text = parser._extract_table_text(table)
        
        assert "Cell 1 | Cell 2" in text
        assert "Cell 3 | Cell 4" in text

    def test_extract_table_text_empty(self, parser, tmp_path):
        """Test _extract_table_text with empty table."""
        html_file = tmp_path / "empty_table.html"
        html_file.write_text(
            '<html><body><table></table></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        table = parser.root.find('table')
        text = parser._extract_table_text(table)
        
        assert text is None

    def test_finalize_article_with_heading(self, parser):
        """Test _finalize_article uses first paragraph as heading."""
        parser.articles = []
        article = {
            'eId': 'art_1',
            'num': 'Article 1',
            'heading': None,
            'children': []
        }
        paragraphs = ["Short title", "First paragraph.", "Second paragraph."]
        
        parser._finalize_article(article, paragraphs)
        
        assert len(parser.articles) == 1
        assert parser.articles[0]['heading'] == "Short title"
        assert len(parser.articles[0]['children']) == 2

    def test_finalize_article_lettered_points(self, parser):
        """Test _finalize_article groups lettered points together."""
        parser.articles = []
        article = {
            'eId': 'art_1',
            'num': 'Article 1',
            'heading': None,
            'children': []
        }
        paragraphs = [
            "First paragraph.",
            "(a) First point",
            "(b) Second point",
            "Second paragraph."
        ]
        
        parser._finalize_article(article, paragraphs)
        
        # Should have 2 children: first para, grouped (a)+(b), second para
        assert len(parser.articles[0]['children']) >= 2

    def test_get_conclusions_success(self, parser, tmp_path):
        """Test get_conclusions extracts conclusion text."""
        html_file = tmp_path / "conclusions.html"
        html_file.write_text(
            '''<html><body><txt_te>
                <p>Article content</p>
                <p>Done at Brussels, 20 December 2025.</p>
                <p>For the Council</p>
            </txt_te></body></html>''',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_conclusions()
        
        assert parser.conclusions is not None
        assert "Done at Brussels" in parser.conclusions

    def test_get_conclusions_not_found(self, parser, tmp_path):
        """Test get_conclusions when no conclusion found."""
        html_file = tmp_path / "no_conclusions.html"
        html_file.write_text(
            '<html><body><txt_te><p>Article content</p></txt_te></body></html>',
            encoding='utf-8'
        )
        
        parser.get_root(str(html_file))
        parser.get_preamble()
        parser.get_conclusions()
        
        assert parser.conclusions is None

    def test_parse_directory_input(self, parser, tmp_path):
        """Test parse handles directory input."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        html_file = test_dir / "test.html"
        html_file.write_text(
            '<html><body><txt_te><p>Test</p></txt_te></body></html>',
            encoding='utf-8'
        )
        
        result = parser.parse(str(test_dir))
        assert result == parser

    def test_parse_directory_no_html(self, parser, tmp_path):
        """Test parse handles directory with no HTML files."""
        test_dir = tmp_path / "empty_dir"
        test_dir.mkdir()
        
        result = parser.parse(str(test_dir))
        # Should return dict with empty articles
        assert isinstance(result, dict)

    def test_parse_full_workflow(self, parser, sample_standard_html):
        """Test complete parse workflow."""
        result = parser.parse(sample_standard_html)
        
        assert result == parser
        assert parser.root is not None

    def test_parse_without_validation(self, parser, tmp_path):
        """Test parse without validation option."""
        html_file = tmp_path / "no_validate.html"
        html_file.write_text(
            '<html><body><txt_te><p>Test</p></txt_te></body></html>',
            encoding='utf-8'
        )
        
        result = parser.parse(str(html_file), validate=False)
        assert result == parser
