import pytest
import os
from bs4 import BeautifulSoup
from tulit.parser.html.html_parser import HTMLParser
from tulit.parser.html.cellar import CellarHTMLParser
from tests.conftest import locate_data_dir
from unittest.mock import Mock, patch, mock_open
import tempfile

DATA_DIR = locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "regulations" / "html"
file_path = str(DATA_DIR / "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03" / "DOC_1.html")


@pytest.fixture
def parser():
    """Create a CellarHTMLParser instance with root loaded."""
    p = CellarHTMLParser()
    if os.path.exists(file_path):
        p.get_root(file_path)
    return p


def test_get_root_loads_html(parser):
    """Test that get_root loads HTML file and creates BeautifulSoup root."""
    assert os.path.exists(file_path), f"Test file not found at {file_path}"
    assert parser.root is not None
    assert isinstance(parser.root, BeautifulSoup)


def test_get_root_with_nonexistent_file():
    """Test get_root handles missing file gracefully."""
    p = CellarHTMLParser()
    p.get_root("/nonexistent/file.html")
    # Should log error but not raise exception
    assert hasattr(p, 'root')


def test_get_root_with_invalid_html(tmp_path):
    """Test get_root can handle malformed HTML."""
    html_file = tmp_path / "malformed.html"
    html_file.write_text("<html><body><div>no closing", encoding='utf-8')
    
    p = CellarHTMLParser()
    p.get_root(str(html_file))
    
    # BeautifulSoup should still parse it
    assert p.root is not None


def test_parse_calls_all_methods(tmp_path):
    """Test parse() orchestrates all extraction methods."""
    html_file = tmp_path / "test.html"
    html_content = """
    <html><body>
        <div class="eli-main-title">Title</div>
        <div class="eli-subdivision" id="pbl_1">
            <p class="oj-normal">Formula</p>
            <div class="eli-subdivision" id="cit_1">Citation</div>
            <div class="eli-subdivision" id="rct_1">Recital</div>
        </div>
        <div id="body">Body</div>
        <div id="art_1">Article 1</div>
    </body></html>
    """
    html_file.write_text(html_content, encoding='utf-8')
    
    p = CellarHTMLParser()
    result = p.parse(str(html_file))
    
    # Verify parse returns self for chaining
    assert result is p
    # Verify key methods were called (check attributes set)
    assert hasattr(p, 'preface')
    assert hasattr(p, 'preamble')
    assert hasattr(p, 'citations')


def test_parse_handles_get_root_exception():
    """Test parse() continues when get_root fails."""
    p = CellarHTMLParser()
    
    with patch.object(p, 'get_root', side_effect=Exception("Root error")):
        result = p.parse("/some/file.html")
    
    # Should return self despite error
    assert result is p


def test_parse_handles_get_preface_exception(tmp_path):
    """Test parse() continues when get_preface fails."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body></body></html>", encoding='utf-8')
    
    p = CellarHTMLParser()
    
    with patch.object(p, 'get_preface', side_effect=Exception("Preface error")):
        result = p.parse(str(html_file))
    
    assert result is p


def test_parse_handles_get_preamble_exception(tmp_path):
    """Test parse() continues when get_preamble fails."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body></body></html>", encoding='utf-8')
    
    p = CellarHTMLParser()
    
    with patch.object(p, 'get_preamble', side_effect=Exception("Preamble error")):
        result = p.parse(str(html_file))
    
    assert result is p


def test_parse_handles_get_formula_exception(tmp_path):
    """Test parse() continues when get_formula fails."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body></body></html>", encoding='utf-8')
    
    p = CellarHTMLParser()
    
    with patch.object(p, 'get_formula', side_effect=Exception("Formula error")):
        result = p.parse(str(html_file))
    
    assert result is p


def test_parse_handles_get_citations_exception(tmp_path):
    """Test parse() continues when get_citations fails."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body></body></html>", encoding='utf-8')
    
    p = CellarHTMLParser()
    
    with patch.object(p, 'get_citations', side_effect=Exception("Citations error")):
        result = p.parse(str(html_file))
    
    assert result is p


def test_parse_handles_get_recitals_exception(tmp_path):
    """Test parse() continues when get_recitals fails."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body></body></html>", encoding='utf-8')
    
    p = CellarHTMLParser()
    
    with patch.object(p, 'get_recitals', side_effect=Exception("Recitals error")):
        result = p.parse(str(html_file))
    
    assert result is p


def test_parse_handles_get_preamble_final_exception(tmp_path):
    """Test parse() continues when get_preamble_final fails."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body></body></html>", encoding='utf-8')
    
    p = CellarHTMLParser()
    
    with patch.object(p, 'get_preamble_final', side_effect=Exception("Preamble final error")):
        result = p.parse(str(html_file))
    
    assert result is p


def test_parse_handles_get_body_exception(tmp_path):
    """Test parse() continues when get_body fails."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body></body></html>", encoding='utf-8')
    
    p = CellarHTMLParser()
    
    with patch.object(p, 'get_body', side_effect=Exception("Body error")):
        result = p.parse(str(html_file))
    
    assert result is p


def test_parse_handles_get_chapters_exception(tmp_path):
    """Test parse() continues when get_chapters fails."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body></body></html>", encoding='utf-8')
    
    p = CellarHTMLParser()
    
    with patch.object(p, 'get_chapters', side_effect=Exception("Chapters error")):
        result = p.parse(str(html_file))
    
    assert result is p


def test_parse_handles_get_articles_exception(tmp_path):
    """Test parse() continues when get_articles fails."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body></body></html>", encoding='utf-8')
    
    p = CellarHTMLParser()
    
    with patch.object(p, 'get_articles', side_effect=Exception("Articles error")):
        result = p.parse(str(html_file))
    
    assert result is p


def test_parse_handles_get_conclusions_exception(tmp_path):
    """Test parse() continues when get_conclusions fails."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html><body></body></html>", encoding='utf-8')
    
    p = CellarHTMLParser()
    
    with patch.object(p, 'get_conclusions', side_effect=Exception("Conclusions error")):
        result = p.parse(str(html_file))
    
    assert result is p


def test_parse_logs_articles_count(tmp_path, caplog):
    """Test parse() logs article count when successful."""
    html_file = tmp_path / "test.html"
    html_content = """
    <html><body>
        <div class="eli-main-title">Title</div>
    </body></html>
    """
    html_file.write_text(html_content, encoding='utf-8')
    
    p = CellarHTMLParser()
    
    def mock_get_articles():
        p.articles = [{'eId': 1}, {'eId': 2}]
    
    with patch.object(p, 'get_articles', side_effect=mock_get_articles):
        with caplog.at_level('INFO'):
            p.parse(str(html_file))
    
    # Check that article count was logged
    assert any('2' in record.message and 'article' in record.message.lower() 
               for record in caplog.records)


def test_html_parser_initialization():
    """Test HTMLParser initializes with parent Parser attributes."""
    p = CellarHTMLParser()
    assert hasattr(p, 'logger')
    assert p.logger is not None


def test_get_root_with_utf8_content(tmp_path):
    """Test get_root handles UTF-8 encoded content."""
    html_file = tmp_path / "utf8.html"
    html_file.write_text("<html><body>€ § © </body></html>", encoding='utf-8')
    
    p = CellarHTMLParser()
    p.get_root(str(html_file))
    
    assert p.root is not None
    assert '€' in str(p.root) or '\u20ac' in str(p.root)
