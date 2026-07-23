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

iopa_dir = str(locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "formex" / "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02" / "DOC_1")

iopa_annex = str(locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "formex" / "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02" / "DOC_1" / "L_202400903EN.002601.fmx.xml")


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


def test_parse_single_annex_document_extracts_annex(tmp_path):
    """Test parse() clears articles and extracts the annex when the root is ANNEX."""
    annex_xml = (
        '<ANNEX><TITLE><TI><P>ANNEX I</P></TI><STI><P>Sample heading</P></STI></TITLE>'
        '<CONTENTS><P>First paragraph.</P></CONTENTS></ANNEX>'
    )

    def fake_super_parse(self, file, **opts):
        self.preface = 'ANNEX I'
        self.articles = ['will_be_cleared']
        self.root = etree.fromstring(annex_xml)

    with patch('tulit.parser.xml.xml.XMLParser.parse', new=fake_super_parse):
        p = Formex4Parser()
        ret = p.parse('somefile.xml')

    assert ret is p
    # A standalone annex document carries no articles but exposes the annex content
    assert p.articles == []
    assert len(p.annexes) == 1
    assert p.annexes[0]['eId'] == 'anx_1'
    assert p.annexes[0]['num'] == 'ANNEX I'
    assert p.annexes[0]['heading'] == 'Sample heading'
    assert p.annexes[0]['children'][0]['text'] == 'First paragraph.'


def test_parse_non_annex_root_keeps_articles(tmp_path):
    """Test parse() keeps articles when the document root is not an annex."""
    def fake_super_parse(self, file, **opts):
        self.preface = 'ANNEX VII TO'
        self.articles = ['kept']
        self.root = etree.fromstring('<ROOT/>')

    with patch('tulit.parser.xml.xml.XMLParser.parse', new=fake_super_parse):
        p = Formex4Parser()
        ret = p.parse('somefile.xml')

    assert ret is p
    assert p.articles == ['kept']
    assert p.annexes == []


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


# ---------------------------------------------------------------------------
# Annex extraction
# ---------------------------------------------------------------------------

def test_extract_annex_children_expands_lists():
    """_extract_annex_children() turns top-level Ps and list items into children."""
    p = Formex4Parser()
    contents = etree.fromstring('''
    <CONTENTS>
      <P>Intro paragraph.</P>
      <LIST TYPE="ARAB">
        <ITEM><NP><NO.P>1.</NO.P><TXT>First item</TXT></NP></ITEM>
        <ITEM><NP><NO.P>2.</NO.P><TXT>Second item</TXT></NP></ITEM>
      </LIST>
    </CONTENTS>
    ''')

    children = p._extract_annex_children(contents, annex_index=2)

    assert len(children) == 3
    assert children[0]['eId'] == '002.001'
    assert children[0]['text'] == 'Intro paragraph.'
    assert children[0]['amendment'] is False
    # Numbered points keep their number, separated from the body
    assert children[1]['eId'] == '002.002'
    assert children[1]['text'] == '1. First item'
    assert children[2]['text'] == '2. Second item'


def test_extract_annex_children_renders_tables_with_structure():
    """Tables become one child with row/cell separators and structured rows."""
    p = Formex4Parser()
    contents = etree.fromstring('''
    <CONTENTS>
      <TBL>
        <TITLE><TI><P>List of products</P></TI></TITLE>
        <CORPUS>
          <ROW><CELL>2843909075</CELL><CELL>457-82-4</CELL><CELL>padeliporfin</CELL></ROW>
          <ROW><CELL>2844403012</CELL><CELL>3748-56-1</CELL><CELL>iodofiltic acid</CELL></ROW>
        </CORPUS>
      </TBL>
    </CONTENTS>
    ''')

    children = p._extract_annex_children(contents, annex_index=1)

    assert len(children) == 1
    child = children[0]
    # Cell values never run together in the text rendering
    assert '2843909075 | 457-82-4 | padeliporfin' in child['text']
    assert child['table']['caption'] == 'List of products'
    assert child['table']['rows'] == [
        ['2843909075', '457-82-4', 'padeliporfin'],
        ['2844403012', '3748-56-1', 'iodofiltic acid'],
    ]


def test_extract_annex_children_amendment_flag_and_quotes():
    """Annexes quoting amendment text mirror the article convention."""
    p = Formex4Parser()
    contents = etree.fromstring('''
    <CONTENTS>
      <P>The Annex is amended as follows:</P>
      <LIST TYPE="ARAB">
        <ITEM><NP><NO.P>(1)</NO.P><TXT>entry 73 is replaced by the following:</TXT>
          <QUOT.S LEVEL="1"><P>73 | thiram | 30 April 2017</P></QUOT.S>
        </NP></ITEM>
      </LIST>
    </CONTENTS>
    ''')

    children = p._extract_annex_children(contents, annex_index=1)

    assert all(c['amendment'] is True for c in children)
    point = children[1]
    assert point['text'].startswith('(1) entry 73 is replaced by the following:')
    # Quoted amendment text is kept inline, wrapped in quotes
    assert "'73 | thiram | 30 April 2017'" in point['text']


def test_extract_annex_children_definition_lists():
    """DLIST items join term and definition."""
    p = Formex4Parser()
    contents = etree.fromstring('''
    <CONTENTS>
      <DLIST>
        <DLIST.ITEM><TERM>ESCB</TERM><DEFINITION><P>European System of Central Banks</P></DEFINITION></DLIST.ITEM>
      </DLIST>
    </CONTENTS>
    ''')

    children = p._extract_annex_children(contents, annex_index=1)

    assert children[0]['text'] == 'ESCB — European System of Central Banks'


def test_extract_annex_returns_none_for_non_annex():
    """_extract_annex() returns None when the element is not an ANNEX."""
    p = Formex4Parser()
    assert p._extract_annex(etree.fromstring('<ACT/>'), 1) is None
    assert p._extract_annex(None, 1) is None


def test_get_annexes_skips_unparseable_files(tmp_path):
    """get_annexes() logs and skips files that cannot be parsed."""
    bad = tmp_path / "bad.xml"
    bad.write_text("<ANNEX><TITLE>unclosed")  # malformed
    good = tmp_path / "good.xml"
    good.write_text(
        '<ANNEX><TITLE><TI><P>ANNEX I</P></TI></TITLE>'
        '<CONTENTS><P>Body.</P></CONTENTS></ANNEX>'
    )

    p = Formex4Parser()
    annexes = p.get_annexes([str(bad), str(good)])

    assert len(annexes) == 1
    assert annexes[0]['num'] == 'ANNEX I'


def test_parse_directory_extracts_sibling_annex():
    """parse() on a real DOC directory extracts both articles and sibling annexes."""
    p = Formex4Parser().parse(iopa_dir)

    # The legal act articles are still parsed
    assert len(p.articles) > 0
    # The sibling ANNEX file is extracted into annexes
    assert len(p.annexes) == 1
    annex = p.annexes[0]
    assert annex['eId'] == 'anx_1'
    assert annex['num'] == 'ANNEX'
    assert 'CHECKLIST' in annex['heading'].upper()
    assert len(annex['children']) > 0
    assert all('eId' in c and 'text' in c for c in annex['children'])


def test_parse_single_annex_file_real_fixture():
    """parse() on a standalone annex file populates annexes and clears articles."""
    p = Formex4Parser().parse(iopa_annex)

    assert p.articles == []
    assert len(p.annexes) == 1
    assert p.annexes[0]['num'] == 'ANNEX'


def test_to_dict_includes_annexes():
    """to_dict() exposes the annexes field."""
    p = Formex4Parser()
    p.annexes = [{'eId': 'anx_1', 'num': 'ANNEX I', 'heading': None, 'children': []}]
    result = p.to_dict()

    assert 'annexes' in result
    assert result['annexes'][0]['eId'] == 'anx_1'


# ---------------------------------------------------------------------------
# Annex INCL.ELEMENT resolution and schema validation
# ---------------------------------------------------------------------------

def test_resolve_inclusions_grafts_external_content(tmp_path):
    """get_annexes() resolves INCL.ELEMENT references to sibling files."""
    (tmp_path / "included.xml").write_text(
        '<DOC><BIB.DOC><PROD.ID>meta</PROD.ID></BIB.DOC>'
        '<CONTENTS><P>Included quoted decision text.</P></CONTENTS></DOC>'
    )
    annex_file = tmp_path / "annex.xml"
    annex_file.write_text(
        '<ANNEX><TITLE><TI><P>ANNEX</P></TI></TITLE>'
        '<CONTENTS><QUOT.S LEVEL="1">'
        '<INCL.ELEMENT FILEREF="included.xml" TYPE="FORMEX.DOC"/>'
        '</QUOT.S></CONTENTS></ANNEX>'
    )

    annexes = Formex4Parser().get_annexes([str(annex_file)])

    assert len(annexes) == 1
    children = annexes[0]['children']
    assert len(children) == 1
    assert 'Included quoted decision text.' in children[0]['text']
    # Bibliographic metadata of the included file is not extracted as content
    assert 'meta' not in children[0]['text']


def test_resolve_inclusions_missing_file_is_skipped(tmp_path):
    """get_annexes() does not crash when an INCL.ELEMENT target is missing."""
    annex_file = tmp_path / "annex.xml"
    annex_file.write_text(
        '<ANNEX><TITLE><TI><P>ANNEX</P></TI></TITLE>'
        '<CONTENTS><QUOT.S LEVEL="1">'
        '<INCL.ELEMENT FILEREF="does_not_exist.xml" TYPE="FORMEX.DOC"/>'
        '</QUOT.S></CONTENTS></ANNEX>'
    )

    annexes = Formex4Parser().get_annexes([str(annex_file)])

    assert len(annexes) == 1
    assert annexes[0]['children'] == []


def test_parse_validates_against_bundled_schema():
    """parse() resolves formex4.xsd from the package assets and validates."""
    p = Formex4Parser().parse(iopa)

    assert p.valid is True
    assert p.validation_errors == []


def test_extract_annex_children_inline_quot_start_flags_amendment():
    """Inline QUOT.START/QUOT.END markers also flag amendment, as in articles."""
    p = Formex4Parser()
    contents = etree.fromstring(
        '<CONTENTS><P>the date <QUOT.START/>31 July 2014<QUOT.END/> is replaced by '
        '<QUOT.START/>30 April 2017<QUOT.END/>.</P></CONTENTS>'
    )

    children = p._extract_annex_children(contents, annex_index=1)

    assert children[0]['amendment'] is True


def test_table_notes_are_extracted():
    """GR.NOTES legends are kept in the table text and structured notes."""
    p = Formex4Parser()
    contents = etree.fromstring(
        '<CONTENTS><TBL>'
        '<GR.NOTES><NOTE NOTE.ID="E0001"><P>Quotas available pursuant to Regulation X.</P></NOTE></GR.NOTES>'
        '<CORPUS><ROW><CELL>PT</CELL><CELL>ANE</CELL></ROW></CORPUS>'
        '</TBL></CONTENTS>'
    )

    children = p._extract_annex_children(contents, annex_index=1)

    assert 'Quotas available pursuant to Regulation X.' in children[0]['text']
    assert children[0]['table']['notes'] == ['Quotas available pursuant to Regulation X.']


def test_annex_num_joins_title_paragraphs_and_strips_quotes():
    """Multi-paragraph TI joins with spaces; quote markers do not leak into num."""
    p = Formex4Parser()
    annex = etree.fromstring(
        '<ANNEX><TITLE><TI><P>ANNEX</P><P>to be allocated for September</P></TI></TITLE>'
        '<CONTENTS><P>Body.</P></CONTENTS></ANNEX>'
    )
    assert p._extract_annex(annex, 1)['num'] == 'ANNEX to be allocated for September'

    quoted = etree.fromstring(
        '<ANNEX><TITLE><TI><P><QUOT.START/>ANNEX I</P></TI></TITLE>'
        '<CONTENTS><P>Body.</P></CONTENTS></ANNEX>'
    )
    assert p._extract_annex(quoted, 1)['num'] == 'ANNEX I'


def test_parse_skips_annex_files_referenced_as_inclusions(tmp_path):
    """A sibling annex file that is only an INCL.ELEMENT target is not duplicated."""
    (tmp_path / "act.xml").write_text(
        '<ACT><ENACTING.TERMS><ARTICLE IDENTIFIER="001"><TI.ART>Article 1</TI.ART>'
        '<ALINEA>Text.</ALINEA></ARTICLE></ENACTING.TERMS></ACT>'
    )
    (tmp_path / "annex_wrapper.xml").write_text(
        '<ANNEX><TITLE><TI><P>ANNEX VII</P></TI></TITLE>'
        '<CONTENTS><INCL.ELEMENT FILEREF="annex_content.xml" TYPE="FORMEX.DOC"/></CONTENTS></ANNEX>'
    )
    (tmp_path / "annex_content.xml").write_text(
        '<ANNEX><TITLE><TI><P>ANNEX VII</P></TI></TITLE>'
        '<CONTENTS><P>Part 1 requirements.</P></CONTENTS></ANNEX>'
    )

    p = Formex4Parser().parse(str(tmp_path))

    assert len(p.annexes) == 1
    assert p.annexes[0]['children'][0]['text'] == 'Part 1 requirements.'


def test_annotation_table_notes_are_extracted():
    """GR.NOTES containing GR.ANNOTATION blocks (not just NOTE) are kept."""
    p = Formex4Parser()
    contents = etree.fromstring(
        '<CONTENTS><TBL>'
        '<GR.NOTES><GR.ANNOTATION><ANNOTATION><NP><NO.P>(1)</NO.P>'
        '<TXT>EFSA identified some information as unavailable.</TXT></NP>'
        '</ANNOTATION></GR.ANNOTATION></GR.NOTES>'
        '<CORPUS><ROW><CELL>A</CELL></ROW></CORPUS>'
        '</TBL></CONTENTS>'
    )

    children = p._extract_annex_children(contents, annex_index=1)

    assert 'EFSA identified some information as unavailable.' in children[0]['text']
    assert any('EFSA' in n for n in children[0]['table']['notes'])


def test_titleless_annex_wrapper_adopts_included_title(tmp_path):
    """A wrapper annex without TITLE adopts the included annex's title."""
    (tmp_path / "act.xml").write_text(
        '<ACT><ENACTING.TERMS><ARTICLE IDENTIFIER="001"><TI.ART>Article 1</TI.ART>'
        '<ALINEA>Text.</ALINEA></ARTICLE></ENACTING.TERMS></ACT>'
    )
    (tmp_path / "wrapper.xml").write_text(
        '<ANNEX><CONTENTS><INCL.ELEMENT FILEREF="content.xml" TYPE="FORMEX.DOC"/></CONTENTS></ANNEX>'
    )
    (tmp_path / "content.xml").write_text(
        '<ANNEX><TITLE><TI><P>ANNEX VII</P></TI></TITLE>'
        '<CONTENTS><P>Part 1 requirements.</P></CONTENTS></ANNEX>'
    )

    p = Formex4Parser().parse(str(tmp_path))

    assert len(p.annexes) == 1
    assert p.annexes[0]['num'] == 'ANNEX VII'
    assert p.annexes[0]['children'][0]['text'] == 'Part 1 requirements.'
