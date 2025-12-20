import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from tulit.parser.html.cellar import CellarHTMLParser
from tests.conftest import locate_data_dir

DATA_DIR = locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "regulations" / "html"
FILE_PATH = str(DATA_DIR / "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03" / "DOC_1.html")


@pytest.fixture
def cellar_parser():
    """Returns a fresh CellarHTMLParser instance."""
    return CellarHTMLParser()


@pytest.fixture
def parser_with_root(cellar_parser):
    """Returns a parser with root already loaded from test file."""
    if not os.path.exists(FILE_PATH):
        pytest.skip(f"Test file not found at {FILE_PATH}")
    cellar_parser.get_root(FILE_PATH)
    return cellar_parser


class TestCellarHTMLParser:
    """Test suite for CellarHTMLParser."""

    def test_init(self, cellar_parser):
        """Test CellarHTMLParser initialization."""
        assert cellar_parser is not None
        assert isinstance(cellar_parser, CellarHTMLParser)

    def test_normalize_text_unicode_quotes(self, cellar_parser):
        """Test _normalize_text replaces Unicode quotes with ASCII."""
        text = "\u2018single\u2019 \u201cdouble\u201d"
        result = cellar_parser._normalize_text(text)
        assert result == "'single' \"double\""

    def test_normalize_text_non_breaking_space(self, cellar_parser):
        """Test _normalize_text replaces non-breaking space."""
        text = "text\xa0with\xa0nbsp"
        result = cellar_parser._normalize_text(text)
        assert result == "text with nbsp"

    def test_normalize_text_mixed_special_chars(self, cellar_parser):
        """Test _normalize_text handles multiple special characters."""
        text = "\u2018It\u2019s\xa0\u201cgood\u201d"
        result = cellar_parser._normalize_text(text)
        assert result == "'It's \"good\""

    def test_get_root_success(self, cellar_parser):
        """Test get_root successfully loads HTML file."""
        if not os.path.exists(FILE_PATH):
            pytest.skip(f"Test file not found at {FILE_PATH}")
        cellar_parser.get_root(FILE_PATH)
        assert cellar_parser.root is not None

    def test_get_preface_success(self, parser_with_root):
        """Test get_preface extracts eli-main-title div."""
        parser_with_root.get_preface()
        assert parser_with_root.preface is not None
        assert isinstance(parser_with_root.preface, str)

    def test_get_preface_no_element(self, cellar_parser, tmp_path, caplog):
        """Test get_preface when eli-main-title div is missing."""
        html_file = tmp_path / "no_preface.html"
        html_file.write_text(
            '<html><body><div class="other">No preface</div></body></html>',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_preface()
        assert cellar_parser.preface is None
        assert "No preface found" in caplog.text

    def test_get_preface_exception_handling(self, cellar_parser, caplog):
        """Test get_preface handles exceptions gracefully."""
        cellar_parser.root = None
        cellar_parser.get_preface()
        assert "Error extracting preface" in caplog.text

    def test_get_preamble_success(self, parser_with_root):
        """Test get_preamble extracts pbl_1 subdivision."""
        parser_with_root.get_preamble()
        assert parser_with_root.preamble is not None

    def test_get_preamble_removes_anchor_tags(self, cellar_parser, tmp_path):
        """Test get_preamble removes all <a> tags."""
        html_file = tmp_path / "preamble_with_links.html"
        html_file.write_text(
            '''<html><body>
                <div class="eli-subdivision" id="pbl_1">
                    Text with <a href="#">link</a> removed
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_preamble()
        
        # Check that anchor tag was decomposed
        assert cellar_parser.preamble.find('a') is None
        assert 'Text with' in cellar_parser.preamble.get_text()

    def test_get_formula_success(self, parser_with_root):
        """Test get_formula extracts oj-normal paragraph from preamble."""
        parser_with_root.get_preamble()
        parser_with_root.get_formula()
        assert parser_with_root.formula is not None
        assert isinstance(parser_with_root.formula, str)

    def test_get_formula_with_mock(self, cellar_parser):
        """Test get_formula extracts text from oj-normal p tag."""
        mock_p = MagicMock()
        mock_p.text = "Formula text"
        
        cellar_parser.preamble = MagicMock()
        cellar_parser.preamble.find.return_value = mock_p
        
        cellar_parser.get_formula()
        assert cellar_parser.formula == "Formula text"

    def test_get_citations_success(self, parser_with_root):
        """Test get_citations extracts cit_ subdivisions."""
        parser_with_root.get_preamble()
        parser_with_root.get_citations()
        assert isinstance(parser_with_root.citations, list)

    def test_get_citations_with_eId_and_text(self, cellar_parser, tmp_path):
        """Test get_citations extracts eId and normalized text."""
        html_file = tmp_path / "citations.html"
        html_file.write_text(
            '''<html><body>
                <div class="eli-subdivision" id="pbl_1">
                    <div class="eli-subdivision" id="cit_1">First\xa0citation</div>
                    <div class="eli-subdivision" id="cit_2">Second citation</div>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_preamble()
        cellar_parser.get_citations()
        
        assert len(cellar_parser.citations) == 2
        assert cellar_parser.citations[0]['eId'] == 'cit_1'
        assert 'First citation' in cellar_parser.citations[0]['text']
        assert cellar_parser.citations[1]['eId'] == 'cit_2'

    def test_get_citations_empty_list(self, cellar_parser, tmp_path):
        """Test get_citations returns empty list when no citations."""
        html_file = tmp_path / "no_citations.html"
        html_file.write_text(
            '''<html><body>
                <div class="eli-subdivision" id="pbl_1">No citations</div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_preamble()
        cellar_parser.get_citations()
        
        assert cellar_parser.citations == []

    def test_get_recitals_success(self, parser_with_root):
        """Test get_recitals extracts rct_ subdivisions."""
        parser_with_root.get_preamble()
        parser_with_root.get_recitals()
        assert isinstance(parser_with_root.recitals, list)

    def test_get_recitals_with_numbering(self, cellar_parser, tmp_path):
        """Test get_recitals removes leading (1) numbering."""
        html_file = tmp_path / "recitals.html"
        html_file.write_text(
            '''<html><body>
                <div class="eli-subdivision" id="pbl_1">
                    <div class="eli-subdivision" id="rct_1">(1) First recital</div>
                    <div class="eli-subdivision" id="rct_2">(2) Second recital</div>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_preamble()
        cellar_parser.get_recitals()
        
        assert len(cellar_parser.recitals) == 2
        assert cellar_parser.recitals[0]['text'] == 'First recital'
        assert cellar_parser.recitals[1]['text'] == 'Second recital'

    def test_get_recitals_whitespace_normalization(self, cellar_parser, tmp_path):
        """Test get_recitals normalizes whitespace."""
        html_file = tmp_path / "recitals_whitespace.html"
        html_file.write_text(
            '''<html><body>
                <div class="eli-subdivision" id="pbl_1">
                    <div class="eli-subdivision" id="rct_1">Text   with    multiple     spaces</div>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_preamble()
        cellar_parser.get_recitals()
        
        assert '   ' not in cellar_parser.recitals[0]['text']

    def test_get_preamble_final_success(self, parser_with_root):
        """Test get_preamble_final extracts last oj-normal paragraph."""
        parser_with_root.get_preamble()
        parser_with_root.get_preamble_final()
        assert parser_with_root.preamble_final is not None
        assert isinstance(parser_with_root.preamble_final, str)

    def test_get_body_with_enc_prefix(self, cellar_parser, tmp_path):
        """Test get_body finds div with enc_ prefix."""
        html_file = tmp_path / "body_enc.html"
        html_file.write_text(
            '<html><body><div id="enc_1">Body content</div></body></html>',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        
        assert cellar_parser.body is not None
        assert cellar_parser.body.get('id') == 'enc_1'

    def test_get_body_fallback_eli_container(self, cellar_parser, tmp_path, caplog):
        """Test get_body falls back to eli-container."""
        html_file = tmp_path / "body_fallback.html"
        html_file.write_text(
            '<html><body><div class="eli-container">Fallback body</div></body></html>',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        
        assert cellar_parser.body is not None
        assert "Using eli-container as fallback" in caplog.text

    def test_get_body_fallback_root(self, cellar_parser, tmp_path, caplog):
        """Test get_body falls back to root when no body found."""
        html_file = tmp_path / "no_body.html"
        html_file.write_text(
            '<html><body>No body div</body></html>',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        
        assert cellar_parser.body is not None
        assert "Using root as fallback" in caplog.text

    def test_get_body_removes_anchors(self, cellar_parser, tmp_path):
        """Test get_body replaces anchor tags with spaces."""
        html_file = tmp_path / "body_anchors.html"
        html_file.write_text(
            '<html><body><div id="enc_1">Text <a href="#">link</a> more</div></body></html>',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        
        assert cellar_parser.body.find('a') is None

    def test_get_chapters_success(self, parser_with_root, caplog):
        """Test get_chapters extracts cpt_ divs."""
        parser_with_root.get_body()
        parser_with_root.get_chapters()
        assert isinstance(parser_with_root.chapters, list)

    def test_get_chapters_no_body(self, cellar_parser, caplog):
        """Test get_chapters with None body."""
        cellar_parser.body = None
        cellar_parser.get_chapters()
        
        assert cellar_parser.chapters == []
        assert "No body element to extract chapters from" in caplog.text

    def test_get_chapters_with_num_and_title(self, cellar_parser, tmp_path):
        """Test get_chapters extracts chapter number and title."""
        html_file = tmp_path / "chapters.html"
        html_file.write_text(
            '''<html><body>
                <div id="enc_1">
                    <div id="cpt_1">
                        <p class="oj-ti-section-1">Chapter I</p>
                        <div class="eli-title">Introduction</div>
                    </div>
                    <div id="cpt_2">
                        <p class="oj-ti-section-1">Chapter II</p>
                        <div class="eli-title">Methods</div>
                    </div>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_chapters()
        
        assert len(cellar_parser.chapters) == 2
        assert cellar_parser.chapters[0]['eId'] == 'cpt_1'
        assert cellar_parser.chapters[0]['num'] == 'Chapter I'
        assert cellar_parser.chapters[0]['heading'] == 'Introduction'

    def test_get_chapters_skips_nested_with_dot(self, cellar_parser, tmp_path):
        """Test get_chapters skips nested chapters with dots in id."""
        html_file = tmp_path / "chapters_nested.html"
        html_file.write_text(
            '''<html><body>
                <div id="enc_1">
                    <div id="cpt_1">
                        <p class="oj-ti-section-1">Chapter I</p>
                        <div class="eli-title">Main Chapter</div>
                    </div>
                    <div id="cpt_1.1">
                        <p class="oj-ti-section-1">Chapter I.1</p>
                        <div class="eli-title">Nested chapter (should be skipped)</div>
                    </div>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_chapters()
        
        # Only cpt_1 should be extracted, not cpt_1.1
        assert len([c for c in cellar_parser.chapters if c['eId'] == 'cpt_1']) == 1
        assert not any('cpt_1.1' in c['eId'] for c in cellar_parser.chapters)

    def test_get_articles_success(self, parser_with_root, caplog):
        """Test get_articles extracts articles."""
        parser_with_root.get_body()
        parser_with_root.get_articles()
        assert isinstance(parser_with_root.articles, list)

    def test_get_articles_no_body(self, cellar_parser, caplog):
        """Test get_articles with None body."""
        cellar_parser.body = None
        cellar_parser.get_articles()
        
        assert cellar_parser.articles == []
        assert "No body element to extract articles from" in caplog.text

    def test_get_articles_single_article_id(self, cellar_parser, tmp_path):
        """Test get_articles with id='art' (sole article)."""
        html_file = tmp_path / "single_article.html"
        html_file.write_text(
            '''<html><body>
                <div id="art">
                    <p class="oj-ti-art">Article 1</p>
                    <p class="oj-normal">Content here</p>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        assert len(cellar_parser.articles) >= 1
        # Should find article with id='art'
        article_ids = [a['eId'] for a in cellar_parser.articles]
        assert 'art' in article_ids

    def test_get_articles_no_title_element(self, cellar_parser, tmp_path, caplog):
        """Test get_articles skips article with no title element."""
        html_file = tmp_path / "article_no_title.html"
        html_file.write_text(
            '''<html><body>
                <div id="art_1">No title element here</div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        assert "has no article title element, skipping" in caplog.text

    def test_get_articles_consolidated_format(self, cellar_parser, tmp_path):
        """Test get_articles with consolidated format (title-article-norm)."""
        html_file = tmp_path / "article_consolidated.html"
        html_file.write_text(
            '''<html><body>
                <div id="art_1">
                    <p class="title-article-norm">Article 1</p>
                    <p class="stitle-article-norm">Subtitle</p>
                    <p class="norm">Content</p>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        assert len(cellar_parser.articles) >= 1
        article = cellar_parser.articles[0]
        assert article['num'] == 'Article 1'
        assert article['heading'] == 'Subtitle'

    def test_get_articles_no_subtitle(self, cellar_parser, tmp_path):
        """Test get_articles when subtitle element is missing."""
        html_file = tmp_path / "article_no_subtitle.html"
        html_file.write_text(
            '''<html><body>
                <div id="art_1">
                    <p class="oj-ti-art">Article 1</p>
                    <p class="oj-normal">Content</p>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        assert len(cellar_parser.articles) >= 1
        assert cellar_parser.articles[0]['heading'] is None

    def test_get_articles_with_paragraphs(self, cellar_parser, tmp_path):
        """Test get_articles extracts paragraph children."""
        html_file = tmp_path / "article_paragraphs.html"
        html_file.write_text(
            '''<html><body>
                <div id="art_1">
                    <p class="oj-ti-art">Article 1</p>
                    <p class="oj-normal">First paragraph</p>
                    <p class="oj-normal">Second paragraph</p>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        article = cellar_parser.articles[0]
        assert len(article['children']) == 2

    def test_get_articles_with_table_intro(self, cellar_parser, tmp_path):
        """Test get_articles with table and intro paragraph."""
        html_file = tmp_path / "article_table.html"
        html_file.write_text(
            '''<html><body>
                <div id="art_1">
                    <p class="oj-ti-art">Article 1</p>
                    <p class="oj-normal">Intro text</p>
                    <table>
                        <tr><td>(1)</td><td>First item</td></tr>
                        <tr><td>(2)</td><td>Second item</td></tr>
                    </table>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        article = cellar_parser.articles[0]
        children = article['children']
        assert len(children) > 0
        # First child should be intro
        assert 'Intro text' in children[0]['text']

    def test_get_articles_table_numbered_rows(self, cellar_parser, tmp_path):
        """Test get_articles extracts numbered table rows."""
        html_file = tmp_path / "article_table_numbered.html"
        html_file.write_text(
            '''<html><body>
                <div id="art_1">
                    <p class="oj-ti-art">Article 1</p>
                    <p class="oj-normal">Intro</p>
                    <table>
                        <tr><td>(1)</td><td>First row</td></tr>
                        <tr><td>(2)</td><td>Second row</td></tr>
                    </table>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        article = cellar_parser.articles[0]
        # Should have intro + 2 table rows
        assert len(article['children']) == 3

    def test_get_articles_with_subdivisions(self, cellar_parser, tmp_path):
        """Test get_articles with nested div subdivisions."""
        html_file = tmp_path / "article_subdivisions.html"
        html_file.write_text(
            '''<html><body>
                <div id="art_1">
                    <p class="oj-ti-art">Article 1</p>
                    <div id="art_1.1">First subdivision</div>
                    <div id="art_1.2">Second subdivision</div>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        article = cellar_parser.articles[0]
        assert len(article['children']) == 2

    def test_get_articles_norm_div_with_no_parag(self, cellar_parser, tmp_path):
        """Test get_articles with norm divs containing no-parag spans."""
        html_file = tmp_path / "article_norm_parag.html"
        html_file.write_text(
            '''<html><body>
                <div id="art_1">
                    <p class="oj-ti-art">Article 1</p>
                    <div class="norm">
                        <span class="no-parag">(1)</span>
                        <div class="inline-element">First paragraph</div>
                    </div>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        article = cellar_parser.articles[0]
        assert len(article['children']) >= 1
        assert 'First paragraph' in article['children'][0]['text']

    def test_get_articles_norm_p_paragraphs(self, cellar_parser, tmp_path):
        """Test get_articles with simple p.norm paragraphs."""
        html_file = tmp_path / "article_norm_p.html"
        html_file.write_text(
            '''<html><body>
                <div id="art_1">
                    <p class="oj-ti-art">Article 1</p>
                    <p class="norm">Single paragraph content</p>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        article = cellar_parser.articles[0]
        assert len(article['children']) >= 1

    def test_get_articles_generic_fallback(self, cellar_parser, tmp_path):
        """Test get_articles uses generic fallback for complex structures."""
        html_file = tmp_path / "article_complex.html"
        html_file.write_text(
            '''<html><body>
                <div id="art_1">
                    <p class="oj-ti-art">Article 1</p>
                    <div>Complex content without specific structure</div>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        # Fallback should extract something
        article = cellar_parser.articles[0]
        assert len(article['children']) >= 1

    def test_standardize_children_numbering(self, cellar_parser, tmp_path):
        """Test _standardize_children_numbering formats eIds correctly."""
        html_file = tmp_path / "article_numbering.html"
        html_file.write_text(
            '''<html><body>
                <div id="art_3">
                    <p class="oj-ti-art">Article 3</p>
                    <p class="oj-normal">First</p>
                    <p class="oj-normal">Second</p>
                </div>
            </body></html>''',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_body()
        cellar_parser.get_articles()
        
        # After standardization, children should have format 003.001, 003.002
        article = cellar_parser.articles[0]
        assert article['children'][0]['eId'] == '003.001'
        assert article['children'][1]['eId'] == '003.002'

    def test_get_conclusions_success(self, cellar_parser, tmp_path):
        """Test get_conclusions extracts oj-final div."""
        html_file = tmp_path / "conclusions.html"
        html_file.write_text(
            '<html><body><div class="oj-final">Final text</div></body></html>',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_conclusions()
        
        assert cellar_parser.conclusions == 'Final text'

    def test_get_conclusions_no_element(self, cellar_parser, tmp_path):
        """Test get_conclusions when oj-final div is missing."""
        html_file = tmp_path / "no_conclusions.html"
        html_file.write_text(
            '<html><body>No conclusions</body></html>',
            encoding='utf-8'
        )
        cellar_parser.get_root(str(html_file))
        cellar_parser.get_conclusions()
        
        assert cellar_parser.conclusions is None

    def test_parse_with_directory_xhtml(self, cellar_parser, tmp_path):
        """Test parse with directory containing XHTML file."""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        xhtml_file = dir_path / "test.xhtml"
        xhtml_file.write_text(
            '<html><body><div class="eli-main-title">Test</div></body></html>',
            encoding='utf-8'
        )
        
        result = cellar_parser.parse(str(dir_path))
        assert result is not None

    def test_parse_with_directory_html(self, cellar_parser, tmp_path):
        """Test parse with directory containing HTML file."""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        html_file = dir_path / "test.html"
        html_file.write_text(
            '<html><body><div class="eli-main-title">Test</div></body></html>',
            encoding='utf-8'
        )
        
        result = cellar_parser.parse(str(dir_path))
        assert result is not None

    def test_parse_with_directory_no_files(self, cellar_parser, tmp_path, caplog):
        """Test parse with directory containing no XHTML/HTML files."""
        dir_path = tmp_path / "empty_dir"
        dir_path.mkdir()
        
        with caplog.at_level("ERROR"):
            result = cellar_parser.parse(str(dir_path))
        
        assert "No XHTML/HTML files found" in caplog.text

    def test_parse_calls_parent(self, cellar_parser):
        """Test parse calls parent's parse method."""
        if not os.path.exists(FILE_PATH):
            pytest.skip(f"Test file not found at {FILE_PATH}")
        
        result = cellar_parser.parse(FILE_PATH)
        assert result is not None
        assert result == cellar_parser

    def test_full_parse_workflow(self, cellar_parser):
        """Test complete parse workflow."""
        if not os.path.exists(FILE_PATH):
            pytest.skip(f"Test file not found at {FILE_PATH}")
        
        result = cellar_parser.parse(FILE_PATH)
        
        # Verify all attributes populated
        assert cellar_parser.root is not None
        assert cellar_parser.body is not None
        assert cellar_parser.articles is not None
