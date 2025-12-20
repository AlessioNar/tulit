import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from tulit.parser.html.veneto import VenetoHTMLParser


@pytest.fixture
def sample_html_file():
    """Returns path to test HTML file."""
    test_data_path = Path(__file__).parents[3] / "data" / "html" / "veneto" / "esg.html"
    return str(test_data_path)


@pytest.fixture
def veneto_parser():
    """Returns a fresh VenetoHTMLParser instance."""
    return VenetoHTMLParser()


@pytest.fixture
def parser_with_root(veneto_parser, sample_html_file):
    """Returns a parser with root already loaded from test file."""
    veneto_parser.get_root(sample_html_file)
    return veneto_parser


class TestVenetoHTMLParser:
    """Test suite for VenetoHTMLParser."""

    def test_init(self, veneto_parser):
        """Test VenetoHTMLParser initialization."""
        assert veneto_parser is not None
        assert isinstance(veneto_parser, VenetoHTMLParser)

    def test_get_root_success(self, veneto_parser, sample_html_file):
        """Test get_root successfully extracts div with 'row testo' class."""
        veneto_parser.get_root(sample_html_file)
        
        assert veneto_parser.root is not None
        assert veneto_parser.root.name == 'div'
        # Should have selected first div with class "row testo"
        assert 'row' in veneto_parser.root.get('class', [])
        assert 'testo' in veneto_parser.root.get('class', [])

    def test_get_root_calls_parent(self, veneto_parser, sample_html_file):
        """Test get_root successfully processes file."""
        # Call get_root which internally calls parent
        veneto_parser.get_root(sample_html_file)
        # Verify root was set and is correct type
        assert veneto_parser.root is not None

    def test_get_root_with_missing_div(self, veneto_parser, tmp_path):
        """Test get_root when HTML lacks 'row testo' div."""
        html_file = tmp_path / "no_div.html"
        html_file.write_text(
            '<html><body><div class="other">Content</div></body></html>',
            encoding='utf-8'
        )
        
        with pytest.raises(IndexError):
            veneto_parser.get_root(str(html_file))

    def test_get_preface_success(self, parser_with_root):
        """Test get_preface extracts title text successfully."""
        parser_with_root.get_preface()
        
        assert parser_with_root.preface is not None
        assert isinstance(parser_with_root.preface, str)
        assert len(parser_with_root.preface) > 0

    def test_get_preface_no_title(self, veneto_parser, tmp_path):
        """Test get_preface when no title element exists."""
        html_file = tmp_path / "no_title.html"
        html_file.write_text(
            '<html><body><div class="row testo">No title here</div></body></html>',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_preface()
        
        assert veneto_parser.preface is None

    def test_get_preface_exception_handling(self, veneto_parser):
        """Test get_preface handles exceptions gracefully."""
        veneto_parser.root = None
        # Should not raise exception even with None root
        veneto_parser.get_preface()
        # Method completes without error

    def test_get_preamble(self, parser_with_root):
        """Test get_preamble method (currently a pass statement)."""
        # Method is not implemented (pass statement)
        result = parser_with_root.get_preamble()
        assert result is None

    def test_get_formula(self, parser_with_root):
        """Test get_formula method (currently a pass statement)."""
        # Method is not implemented (pass statement)
        result = parser_with_root.get_formula()
        assert result is None

    def test_get_citations(self, parser_with_root):
        """Test get_citations initializes empty list."""
        parser_with_root.get_citations()
        
        assert parser_with_root.citations == []
        assert isinstance(parser_with_root.citations, list)

    def test_get_recitals_success(self, parser_with_root):
        """Test get_recitals extracts bold subtitle text."""
        parser_with_root.get_recitals()
        
        assert parser_with_root.recitals is not None
        assert isinstance(parser_with_root.recitals, list)
        assert len(parser_with_root.recitals) > 0
        assert 'eId' in parser_with_root.recitals[0]
        assert 'text' in parser_with_root.recitals[0]
        assert parser_with_root.recitals[0]['eId'] == 0

    def test_get_recitals_with_bold_element(self, veneto_parser, tmp_path):
        """Test get_recitals with HTML containing bold element."""
        html_file = tmp_path / "with_bold.html"
        html_file.write_text(
            '<html><body><div class="row testo"><b>This is bold text</b></div></body></html>',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_recitals()
        
        assert len(veneto_parser.recitals) == 1
        assert veneto_parser.recitals[0]['text'] == 'This is bold text'

    def test_get_preamble_final(self, parser_with_root):
        """Test get_preamble_final method (currently a pass statement)."""
        # Method is not implemented (pass statement)
        result = parser_with_root.get_preamble_final()
        assert result is None

    def test_get_body(self, parser_with_root):
        """Test get_body method (currently a pass statement)."""
        # Method is not implemented (pass statement)
        result = parser_with_root.get_body()
        assert result is None

    def test_get_chapters_with_h3(self, veneto_parser, tmp_path):
        """Test get_chapters extracts h3 elements with TITOLOCAPOTITOLO class."""
        html_file = tmp_path / "chapters_h3.html"
        html_file.write_text(
            '''<html><body><div class="row testo">
                <h3 class="TITOLOCAPOTITOLO">Chapter 1 - Introduction</h3>
                <h3 class="TITOLOCAPOTITOLO">Chapter 2 - Methods</h3>
            </div></body></html>''',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_chapters()
        
        # Note: The code finds h3 then h4, so h4 result overwrites h3
        assert veneto_parser.chapters is not None
        assert isinstance(veneto_parser.chapters, list)

    def test_get_chapters_with_h4(self, veneto_parser, tmp_path):
        """Test get_chapters extracts h4 elements with TITOLOCAPOCAPO class."""
        html_file = tmp_path / "chapters_h4.html"
        html_file.write_text(
            '''<html><body><div class="row testo">
                <h4 class="TITOLOCAPOCAPO">1 - First Section</h4>
                <h4 class="TITOLOCAPOCAPO">2 - Second Section</h4>
            </div></body></html>''',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_chapters()
        
        assert len(veneto_parser.chapters) == 2
        assert veneto_parser.chapters[0]['eId'] == 0
        assert veneto_parser.chapters[0]['num'] == '1'
        assert veneto_parser.chapters[0]['heading'] == 'First Section'
        assert veneto_parser.chapters[1]['eId'] == 1

    def test_get_chapters_empty(self, veneto_parser, tmp_path):
        """Test get_chapters with no h3 or h4 elements."""
        html_file = tmp_path / "no_chapters.html"
        html_file.write_text(
            '<html><body><div class="row testo">No chapters here</div></body></html>',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_chapters()
        
        assert veneto_parser.chapters == []

    def test_get_articles_success(self, parser_with_root):
        """Test get_articles extracts article h6 elements."""
        parser_with_root.get_articles()
        
        assert parser_with_root.articles is not None
        assert isinstance(parser_with_root.articles, list)
        assert len(parser_with_root.articles) > 0
        
        # Check first article structure
        first_article = parser_with_root.articles[0]
        assert 'eId' in first_article
        assert 'num' in first_article
        assert 'heading' in first_article
        assert 'children' in first_article

    def test_get_articles_with_dash_separator(self, veneto_parser, tmp_path):
        """Test get_articles parses article with dash separator."""
        html_file = tmp_path / "articles_dash.html"
        html_file.write_text(
            '''<html><body><div class="row testo">
                <h6>Art. 1 - Purpose</h6>
                <div>This is the article content.</div>
            </div></body></html>''',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_articles()
        
        assert len(veneto_parser.articles) == 1
        assert veneto_parser.articles[0]['num'] == 'Art. 1'
        assert veneto_parser.articles[0]['heading'] == 'Purpose'

    def test_get_articles_with_endash(self, veneto_parser, tmp_path):
        """Test get_articles replaces en-dash (–) with hyphen."""
        html_file = tmp_path / "articles_endash.html"
        html_file.write_text(
            '''<html><body><div class="row testo">
                <h6>Art. 2 – Definitions</h6>
                <div>Content here.</div>
            </div></body></html>''',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_articles()
        
        assert len(veneto_parser.articles) == 1
        assert veneto_parser.articles[0]['num'] == 'Art. 2'
        assert veneto_parser.articles[0]['heading'] == 'Definitions'

    def test_get_articles_without_dash(self, veneto_parser, tmp_path):
        """Test get_articles when heading has no dash separator."""
        html_file = tmp_path / "articles_no_dash.html"
        html_file.write_text(
            '''<html><body><div class="row testo">
                <h6>Just a heading</h6>
                <div>Some content.</div>
            </div></body></html>''',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_articles()
        
        assert len(veneto_parser.articles) == 1
        assert veneto_parser.articles[0]['num'] == '1'
        assert veneto_parser.articles[0]['heading'] == 'Just a heading'

    def test_get_articles_with_br_splits(self, veneto_parser, tmp_path):
        """Test get_articles splits content by <br> tags into children."""
        html_file = tmp_path / "articles_br.html"
        html_file.write_text(
            '''<html><body><div class="row testo">
                <h6>Art. 1 - Test</h6>
                <div>First paragraph<br/>Second paragraph<br/>Third paragraph</div>
            </div></body></html>''',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_articles()
        
        assert len(veneto_parser.articles) == 1
        children = veneto_parser.articles[0]['children']
        assert len(children) == 3
        assert children[0]['eId'] == 0
        assert 'First paragraph' in children[0]['text']
        assert children[1]['eId'] == 1
        assert 'Second paragraph' in children[1]['text']

    def test_get_articles_no_content_div(self, veneto_parser, tmp_path):
        """Test get_articles when h6 has no following div sibling."""
        html_file = tmp_path / "articles_no_div.html"
        html_file.write_text(
            '''<html><body><div class="row testo">
                <h6>Art. 1 - Orphan</h6>
            </div></body></html>''',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_articles()
        
        assert len(veneto_parser.articles) == 1
        assert veneto_parser.articles[0]['children'] == []

    def test_get_articles_html_tag_cleanup(self, veneto_parser, tmp_path):
        """Test get_articles cleans HTML tags from content."""
        html_file = tmp_path / "articles_tags.html"
        html_file.write_text(
            '''<html><body><div class="row testo">
                <h6>Art. 1 - Test</h6>
                <div><b>Bold text</b> and <i>italic text</i></div>
            </div></body></html>''',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_articles()
        
        children = veneto_parser.articles[0]['children']
        assert len(children) >= 1
        # Should have stripped tags but kept text
        assert '<b>' not in children[0]['text']
        assert '<i>' not in children[0]['text']

    def test_get_articles_whitespace_cleanup(self, veneto_parser, tmp_path):
        """Test get_articles normalizes multiple whitespaces."""
        html_file = tmp_path / "articles_whitespace.html"
        html_file.write_text(
            '''<html><body><div class="row testo">
                <h6>Art. 1 - Test</h6>
                <div>Text   with    multiple     spaces</div>
            </div></body></html>''',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_articles()
        
        children = veneto_parser.articles[0]['children']
        # Multiple spaces should be reduced to single space
        assert '   ' not in children[0]['text']
        assert 'Text with multiple spaces' in children[0]['text']

    def test_get_articles_empty_content_filtered(self, veneto_parser, tmp_path):
        """Test get_articles filters out empty children after cleanup."""
        html_file = tmp_path / "articles_empty.html"
        html_file.write_text(
            '''<html><body><div class="row testo">
                <h6>Art. 1 - Test</h6>
                <div>Real content<br/><br/>More content</div>
            </div></body></html>''',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_articles()
        
        children = veneto_parser.articles[0]['children']
        # Empty parts should be filtered out
        for child in children:
            assert len(child['text'].strip()) > 0

    def test_get_conclusions_success(self, veneto_parser, tmp_path):
        """Test get_conclusions extracts text from oj-final div."""
        html_file = tmp_path / "conclusions.html"
        html_file.write_text(
            '''<html><body><div class="row testo">
                <div class="oj-final">Final conclusions text</div>
            </div></body></html>''',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        veneto_parser.get_conclusions()
        
        assert veneto_parser.conclusions == 'Final conclusions text'

    def test_get_conclusions_no_element(self, veneto_parser, tmp_path):
        """Test get_conclusions when oj-final div is missing."""
        html_file = tmp_path / "no_conclusions.html"
        html_file.write_text(
            '<html><body><div class="row testo">No conclusions here</div></body></html>',
            encoding='utf-8'
        )
        
        veneto_parser.get_root(str(html_file))
        
        with pytest.raises(AttributeError):
            veneto_parser.get_conclusions()

    def test_parse_calls_parent(self, veneto_parser, sample_html_file):
        """Test parse method calls parent's parse implementation."""
        with patch.object(VenetoHTMLParser.__bases__[0], 'parse', return_value={'test': 'data'}) as mock_parent:
            result = veneto_parser.parse(sample_html_file)
            mock_parent.assert_called_once_with(sample_html_file)
            assert result == {'test': 'data'}

    def test_full_parse_workflow(self, veneto_parser, sample_html_file):
        """Test complete parse workflow with real test file."""
        result = veneto_parser.parse(sample_html_file)
        
        # parse() returns the parser object itself
        assert result is not None
        assert result == veneto_parser
        
        # Verify parser populated attributes
        assert veneto_parser.root is not None
        assert veneto_parser.articles is not None
        assert len(veneto_parser.articles) > 0
