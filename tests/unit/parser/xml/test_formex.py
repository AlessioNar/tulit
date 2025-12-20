import pytest
import os
from tulit.parser.xml.formex import Formex4Parser
from pathlib import Path
from tests.conftest import locate_data_dir
import tempfile
from unittest.mock import patch, MagicMock
import builtins
from lxml import etree

file_path = str(locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "formex" / "5cca93ee-e193-46bf-8416-c2f57cbc34c9.0004.05" / "DOC_2.xml")

iopa = str(locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "formex" / "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02" / "DOC_1" / "L_202400903EN.000101.fmx.xml")


@pytest.fixture
def parser():
    """Create a parser instance with root loaded."""
    p = Formex4Parser()
    p.get_root(file_path)
    return p


@pytest.fixture
def iopa_parser():
    """Create a parser instance with IOPA document loaded."""
    p = Formex4Parser()
    p.get_root(iopa)
    return p


def test_get_root(parser):
    """Test parsing and root element retrieval from the Formex file."""
    assert os.path.exists(file_path), f"Test file not found at {file_path}"
    assert parser.root is not None, "Root element should not be None"


def test_get_preface(parser):
    parser.get_preface()
    preface = "Commission Implementing Regulation (EU) No 1319/2011 of 15 December 2011 fixing representative prices in the poultrymeat and egg sectors and for egg albumin, and amending Regulation (EC) No 1484/95"
    assert parser.preface == preface


def test_get_preamble(parser):
    parser.get_preamble()
    assert parser.preamble is not None


def test_get_formula(parser):
    parser.get_preamble()
    parser.get_formula()
    formula = "THE EUROPEAN COMMISSION,"
    assert parser.formula == formula


def test_get_citations(parser):
    parser.get_preamble()
    parser.get_citations()
    citations = [
        {'eId': "cit_1", 'text': "Having regard to the Treaty on the Functioning of the European Union,"},
        {"eId": "cit_2", 'text': "Having regard to Council Regulation (EC) No 1234/2007 of 22 October 2007 establishing a common organisation of agricultural markets and on specific provisions for certain agricultural products (Single CMO Regulation), and in particular Article 143 thereof,"},
        {"eId": "cit_3", 'text': "Having regard to Council Regulation (EC) No 614/2009 of 7 July 2009 on the common system of trade for ovalbumin and lactalbumin, and in particular Article 3(4) thereof,"},
    ]
    assert parser.citations == citations


def test_get_recitals(parser):
    parser.get_preamble()
    parser.get_recitals()
    recitals = [
        {"eId": "rct_1", "text": "Commission Regulation (EC) No 1484/95 lays down detailed rules for implementing the system of additional import duties and fixes representative prices for poultrymeat and egg products and for egg albumin."},
        {"eId": "rct_2", "text": "Regular monitoring of the data used to determine representative prices for poultrymeat and egg products and for egg albumin shows that the representative import prices for certain products should be amended to take account of variations in price according to origin. The representative prices should therefore be published."},
        {"eId": "rct_3", "text": "In view of the situation on the market, this amendment should be applied as soon as possible."},
        {"eId": "rct_4", "text": "The measures provided for in this Regulation are in accordance with the opinion of the Management Committee for the Common Organisation of Agricultural Markets,"},
    ]
    assert parser.recitals == recitals


def test_get_preamble_final(parser):
    parser.get_preamble()
    parser.get_preamble_final()
    preamble_final = "HAS ADOPTED THIS REGULATION:"
    assert parser.preamble_final == preamble_final


def test_get_body(parser):
    parser.get_body()
    assert parser.body is not None, "Body element should not be None"


def test_get_chapters(iopa_parser):
    iopa_parser.get_body()
    iopa_parser.get_chapters()
    expected_chapters = [
        {'eId': "cpt_1", 'num': 'Chapter 1', 'heading': 'General provisions'},
        {'eId': "cpt_2", 'num': 'Chapter 2', 'heading': 'European Interoperability enablers'},
        {'eId': "cpt_3", 'num': 'Chapter 3', 'heading': 'Interoperable Europe support measures'},
        {'eId': "cpt_4", 'num': 'Chapter 4', 'heading': 'Governance of cross-border interoperability'},
        {'eId': "cpt_5", 'num': 'Chapter 5', 'heading': 'Interoperable Europe planning and monitoring'},
        {'eId': "cpt_6", 'num': 'Chapter 6', 'heading': 'Final provisions'},
    ]
    assert iopa_parser.chapters[0] == expected_chapters[0], "Chapters data does not match expected content"


def test_get_articles(parser):
    parser.get_body()
    parser.get_articles()
    expected = [
        {
            "eId": "art_001",
            "num": "Article 1",
            "heading": None,
            "children": [
                {"eId": '001.001', "text": "Annex I to Regulation (EC) No 1484/95 is replaced by the Annex to this Regulation.", "amendment": False}
            ]
        },
        {
            "eId": "art_002",
            "num": "Article 2",
            "heading": None,
            "children": [
                {"eId": "002.001", "text": "This Regulation shall enter into force on the day of its publication in the Official Journal of the European Union.", "amendment": False}
            ]
        }
    ]
    assert parser.articles == expected


def test_get_conclusions(iopa_parser):
    iopa_parser.get_body()
    iopa_parser.get_conclusions()
    conclusions = {
        "conclusion_text": "This Regulation shall be binding in its entirety and directly applicable in all Member States.",
        "signature": {
            "place": "Done at Strasbourg,",
            "date": "13\xa0March 2024",  # Non-breaking space in date
            "signatory": "For the European Parliament",
            "title": "The President"
        }
    }
    assert iopa_parser.conclusions == conclusions


# ========== COVERAGE BOOST TESTS ==========

def test_parse_directory_selects_act_file(tmp_path):
    """Test parse() selects file with ACT tag from directory."""
    p1 = tmp_path / "doc1.xml"
    p2 = tmp_path / "doc2.xml"
    p1.write_text('<ROOT><ACT/></ROOT>', encoding='utf-8')
    p2.write_text('<ROOT><OTHER/></ROOT>', encoding='utf-8')

    called = {}

    def fake_super_parse(self, file, **opts):
        called['file'] = file
        self.root = etree.fromstring('<ROOT/>')

    with patch('tulit.parser.xml.xml.XMLParser.parse', new=fake_super_parse):
        p = Formex4Parser()
        p.parse(str(tmp_path))

    assert 'doc1.xml' in os.path.basename(called['file'])


def test_parse_directory_with_decision_tag(tmp_path):
    """Test parse() selects file with DECISION tag from directory."""
    p1 = tmp_path / "decision.xml"
    p2 = tmp_path / "other.xml"
    p1.write_text('<ROOT><DECISION/></ROOT>', encoding='utf-8')
    p2.write_text('<ROOT><OTHER/></ROOT>', encoding='utf-8')

    called = {}

    def fake_super_parse(self, file, **opts):
        called['file'] = file
        self.root = etree.fromstring('<ROOT/>')

    with patch('tulit.parser.xml.xml.XMLParser.parse', new=fake_super_parse):
        p = Formex4Parser()
        p.parse(str(tmp_path))

    assert 'decision.xml' in os.path.basename(called['file'])


def test_parse_directory_with_cons_act_tag(tmp_path):
    """Test parse() selects file with CONS.ACT tag from directory."""
    p1 = tmp_path / "cons_act.xml"
    p2 = tmp_path / "other.xml"
    p1.write_text('<ROOT><CONS.ACT/></ROOT>', encoding='utf-8')
    p2.write_text('<ROOT><OTHER/></ROOT>', encoding='utf-8')

    called = {}

    def fake_super_parse(self, file, **opts):
        called['file'] = file
        self.root = etree.fromstring('<ROOT/>')

    with patch('tulit.parser.xml.xml.XMLParser.parse', new=fake_super_parse):
        p = Formex4Parser()
        p.parse(str(tmp_path))

    assert 'cons_act.xml' in os.path.basename(called['file'])


def test_parse_directory_fallback_largest_file(tmp_path):
    """Test parse() falls back to largest file when no ACT/DECISION found."""
    small = tmp_path / 'small.xml'
    large = tmp_path / 'large.xml'
    small.write_text('<ROOT>x</ROOT>', encoding='utf-8')
    large.write_text('<ROOT>' + ('x' * 500) + '</ROOT>', encoding='utf-8')

    chosen = {}

    def fake_super_parse(self, file, **opts):
        chosen['file'] = file
        self.root = etree.fromstring('<ROOT/>')

    with patch('tulit.parser.xml.xml.XMLParser.parse', new=fake_super_parse):
        p = Formex4Parser()
        p.parse(str(tmp_path))

    assert os.path.basename(chosen['file']) == 'large.xml'


def test_parse_directory_read_error_skips_bad_file(tmp_path):
    """Test parse() skips files that raise read errors."""
    bad = tmp_path / 'bad.xml'
    good = tmp_path / 'good.xml'
    bad.write_text('<ROOT>bad</ROOT>', encoding='utf-8')
    good.write_text('<ROOT><ACT/></ROOT>', encoding='utf-8')

    real_open = builtins.open

    def open_side_effect(path, *args, **kwargs):
        if 'bad.xml' in str(path):
            raise OSError('cant read')
        return real_open(path, *args, **kwargs)

    chosen = {}

    def fake_super_parse(self, file, **opts):
        chosen['file'] = file
        self.root = etree.fromstring('<ROOT/>')

    with patch('builtins.open', new=open_side_effect):
        with patch('tulit.parser.xml.xml.XMLParser.parse', new=fake_super_parse):
            p = Formex4Parser()
            p.parse(str(tmp_path))

    assert 'good.xml' in os.path.basename(chosen['file'])


def test_parse_directory_no_xml_files(tmp_path):
    """Test parse() handles directory with no XML files gracefully."""
    (tmp_path / "readme.txt").write_text("no xml here")

    def fake_super_parse(self, file, **opts):
        self.root = etree.fromstring('<ROOT/>')

    with patch('tulit.parser.xml.xml.XMLParser.parse', new=fake_super_parse):
        p = Formex4Parser()
        result = p.parse(str(tmp_path))

    # Should return self without error
    assert result is p


def test_parse_annex_preface_clears_articles(tmp_path):
    """Test parse() clears articles when preface indicates annex."""
    def fake_super_parse(self, file, **opts):
        self.preface = 'ANNEX I'
        self.articles = ['will_be_cleared']
        self.root = etree.fromstring('<ROOT/>')

    with patch('tulit.parser.xml.xml.XMLParser.parse', new=fake_super_parse):
        p = Formex4Parser()
        ret = p.parse('somefile.xml')

    assert ret is p
    assert p.articles == []


def test_parse_annex_preface_with_extra_words(tmp_path):
    """Test parse() clears articles for annex with extra words."""
    def fake_super_parse(self, file, **opts):
        self.preface = 'ANNEX VII TO'
        self.articles = ['will_be_cleared']
        self.root = etree.fromstring('<ROOT/>')

    with patch('tulit.parser.xml.xml.XMLParser.parse', new=fake_super_parse):
        p = Formex4Parser()
        ret = p.parse('somefile.xml')

    assert ret is p
    assert p.articles == []


def test_parse_non_annex_preface_keeps_articles(tmp_path):
    """Test parse() keeps articles when preface is not a short annex reference."""
    def fake_super_parse(self, file, **opts):
        self.preface = 'ANNEX I contains provisions for implementation'
        self.articles = ['kept']
        self.root = etree.fromstring('<ROOT/>')

    with patch('tulit.parser.xml.xml.XMLParser.parse', new=fake_super_parse):
        p = Formex4Parser()
        ret = p.parse('somefile.xml')

    assert ret is p
    assert p.articles == ['kept']


def test_get_articles_when_body_is_none(capsys):
    """Test get_articles() returns empty list and prints message when body is None."""
    p = Formex4Parser()
    p.body = None
    result = p.get_articles()

    assert result == []
    captured = capsys.readouterr()
    assert 'No enacting terms XML tag has been found' in captured.out


def test_get_articles_heading_fallback_to_p():
    """Test get_articles() falls back to STI.ART//P when STI.ART has no direct text."""
    p = Formex4Parser()
    body = etree.fromstring('''
    <BODY>
      <ARTICLE IDENTIFIER="1">
        <STI.ART><P>Heading in P</P></STI.ART>
      </ARTICLE>
    </BODY>
    ''')
    p.body = body

    def fake_extract_articles(body_arg, remove_notes=True):
        return [{'eId': 'art_1', 'children': [{'eId': '1'}]}]

    p.article_strategy.extract_articles = fake_extract_articles
    articles = p.get_articles()

    assert articles[0]['heading'] == 'Heading in P'
    assert articles[0]['children'][0]['eId'] == '001.001'


def test__extract_elements_with_identifier():
    """Test _extract_elements() uses IDENTIFIER attribute for eId."""
    p = Formex4Parser()
    parent = etree.fromstring('''
    <ROOT>
      <ARTICLE IDENTIFIER="art123">
        <P>text</P>
      </ARTICLE>
    </ROOT>
    ''')

    children = []
    p._extract_elements(parent, './/ARTICLE', children)

    assert len(children) == 1
    assert children[0]['eId'] == 'art123'
    assert 'text' in children[0]['text']


def test__extract_elements_with_id_fallback():
    """Test _extract_elements() falls back to ID attribute when no IDENTIFIER."""
    p = Formex4Parser()
    parent = etree.fromstring('''
    <ROOT>
      <ELEM ID="elem456">
        <P>content</P>
      </ELEM>
    </ROOT>
    ''')

    children = []
    p._extract_elements(parent, './/ELEM', children)

    assert len(children) == 1
    assert children[0]['eId'] == 'elem456'


def test__extract_elements_with_no_p_fallback():
    """Test _extract_elements() falls back to NO.P attribute."""
    p = Formex4Parser()
    parent = etree.fromstring('''
    <ROOT>
      <ELEM NO.P="789">
        <TXT>data</TXT>
      </ELEM>
    </ROOT>
    ''')

    children = []
    p._extract_elements(parent, './/ELEM', children)

    assert len(children) == 1
    assert children[0]['eId'] == '789'


def test__extract_elements_with_children_count_fallback():
    """Test _extract_elements() uses children list length for eId when no attrs."""
    p = Formex4Parser()
    parent = etree.fromstring('''
    <ROOT>
      <ELEM>
        <P>first</P>
      </ELEM>
      <ELEM>
        <P>second</P>
      </ELEM>
    </ROOT>
    ''')

    children = [{'eId': 'existing'}]  # Start with one existing child
    p._extract_elements(parent, './/ELEM', children)

    assert len(children) == 3
    assert children[1]['eId'] == '002'  # len(children) was 1, +1 = 2, zfill(3) = '002'
    assert children[2]['eId'] == '003'


def test__extract_elements_filters_empty_text():
    """Test _extract_elements() filters out elements with empty text."""
    p = Formex4Parser()
    parent = etree.fromstring('''
    <ROOT>
      <ELEM IDENTIFIER="1">
        <P></P>
      </ELEM>
      <ELEM IDENTIFIER="2">
        <P>real content</P>
      </ELEM>
    </ROOT>
    ''')

    children = []
    p._extract_elements(parent, './/ELEM', children)

    # Only the element with real content should be added
    assert len(children) == 1
    assert children[0]['eId'] == '2'


def test__extract_elements_filters_semicolon():
    """Test _extract_elements() filters out elements with only semicolon."""
    p = Formex4Parser()
    parent = etree.fromstring('''
    <ROOT>
      <ELEM IDENTIFIER="1">
        <P>;</P>
      </ELEM>
      <ELEM IDENTIFIER="2">
        <P>valid</P>
      </ELEM>
    </ROOT>
    ''')

    children = []
    p._extract_elements(parent, './/ELEM', children)

    assert len(children) == 1
    assert children[0]['eId'] == '2'


def test_clean_text_replaces_quot_start():
    """Test clean_text() replaces QUOT.START with single quote."""
    p = Formex4Parser()
    element = etree.fromstring('<P>before<QUOT.START/>quoted</P>')
    
    text = p.clean_text(element)
    
    assert "'" in text
    assert 'quoted' in text


def test_clean_text_replaces_quot_end():
    """Test clean_text() replaces QUOT.END with single quote."""
    p = Formex4Parser()
    element = etree.fromstring('<P>quoted<QUOT.END/>after</P>')
    
    text = p.clean_text(element)
    
    assert "'" in text
    assert 'after' in text


def test_clean_text_replaces_both_quot_tags():
    """Test clean_text() replaces both QUOT.START and QUOT.END."""
    p = Formex4Parser()
    element = etree.fromstring('<P>hello<QUOT.START/>quoted<QUOT.END/>world</P>')
    
    text = p.clean_text(element)
    
    assert text.count("'") >= 2
    assert 'quoted' in text


def test__standardize_children_numbering():
    """Test _standardize_children_numbering() renumbers children correctly."""
    p = Formex4Parser()
    p.articles = [
        {'eId': 'art_2', 'children': [{'eId': 'x'}, {'eId': 'y'}, {'eId': 'z'}]},
        {'eId': 'art_10', 'children': [{'eId': 'a'}]}
    ]
    
    p._standardize_children_numbering()
    
    assert p.articles[0]['children'][0]['eId'] == '002.001'
    assert p.articles[0]['children'][1]['eId'] == '002.002'
    assert p.articles[0]['children'][2]['eId'] == '002.003'
    assert p.articles[1]['children'][0]['eId'] == '010.001'


def test__standardize_children_numbering_no_match():
    """Test _standardize_children_numbering() handles non-matching eId format."""
    p = Formex4Parser()
    p.articles = [
        {'eId': 'weird_format', 'children': [{'eId': 'x'}]}
    ]
    
    p._standardize_children_numbering()
    
    # Should use 0 as article num when regex doesn't match
    assert p.articles[0]['children'][0]['eId'] == '000.001'


def test_get_conclusions_no_final_section():
    """Test get_conclusions() returns empty dict when no FINAL section."""
    p = Formex4Parser()
    p.root = etree.fromstring('<ROOT></ROOT>')
    
    conclusions = p.get_conclusions()
    
    assert conclusions == {}


def test_get_conclusions_final_without_signature():
    """Test get_conclusions() handles FINAL section without SIGNATURE."""
    p = Formex4Parser()
    root = etree.fromstring('''
      <ROOT>
        <FINAL>
          <P>Conclusion only</P>
        </FINAL>
      </ROOT>
    ''')
    p.root = root
    
    conclusions = p.get_conclusions()
    
    assert conclusions['conclusion_text'] == 'Conclusion only'
    assert 'signature' not in conclusions


def test_get_conclusions_with_full_signature():
    """Test get_conclusions() parses complete signature details."""
    p = Formex4Parser()
    root = etree.fromstring('''
      <ROOT>
        <FINAL>
          <P>Final text</P>
          <SIGNATURE>
            <PL.DATE>
              <P>Brussels,</P>
              <P><DATE>2024-12-20</DATE></P>
            </PL.DATE>
            <SIGNATORY>
              <P><HT>Jane Smith</HT></P>
              <P><HT>Director</HT></P>
            </SIGNATORY>
          </SIGNATURE>
        </FINAL>
      </ROOT>
    ''')
    p.root = root
    
    conclusions = p.get_conclusions()
    
    assert conclusions['conclusion_text'] == 'Final text'
    assert conclusions['signature']['place'] == 'Brussels,'
    assert conclusions['signature']['date'] == '2024-12-20'
    assert 'Jane Smith' in conclusions['signature']['signatory']
    assert conclusions['signature']['title'] == 'Director'
