import pytest

from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser
from tulit.parser.xml.lexdania import LexDaniaParser


@pytest.fixture(scope='module')
def folder(data_root):
    return data_root / 'sources' / 'member_states' / 'denmark' / 'retsinformation'


@pytest.fixture(scope='module')
def act(folder):
    return LexDaniaParser().parse(str(folder / 'lta_2018_502.xml')).to_dict()


@pytest.fixture(scope='module')
def consolidation(folder):
    return LexDaniaParser().parse(str(folder / 'lta_2024_289.xml')).to_dict()


def test_registered():
    assert isinstance(get_parser('lexdania'), LexDaniaParser)


def test_preface_and_formulas(act, consolidation):
    assert act['preface'].startswith('Lov om supplerende bestemmelser')
    assert act['preamble']['formula'].startswith('VI MARGRETHE DEN ANDEN')
    assert consolidation['preamble']['formula'].startswith('Herved bekendtgøres lov nr. 502')


def test_parts_and_chapters(act):
    assert act['chapters'][:2] == [
        {'eId': 'prt_I', 'type': 'part', 'num': 'Afsnit I', 'heading': 'Indledende bestemmelser',
         'parent': None},
        {'eId': 'cpt_1', 'type': 'chapter', 'num': 'Kapitel 1',
         'heading': 'Lovens materielle anvendelsesområde', 'parent': 'prt_I'},
    ]


def test_paragraphs_and_subsections(act):
    articles = {a['eId']: a for a in act['articles']}
    art5 = articles['art_5']
    assert art5['num'] == '§ 5'
    assert art5['parent'] == 'cpt_3'
    assert [c['eId'] for c in art5['children']] == ['par_1', 'par_2', 'par_3']
    assert art5['children'][1]['text'].startswith('Stk. 2. For at afgøre')


def test_numbered_lists_stay_in_their_subsection(act):
    art4 = next(a for a in act['articles'] if a['eId'] == 'art_4')
    assert '1) udbud af varer' in art4['children'][2]['text']
    assert '2) overvågning' in art4['children'][2]['text']


def test_footnotes_left_out(act):
    assert 'Som bilag til loven er medtaget' not in act['preface']


def test_annex_and_amending_acts(consolidation):
    annexes = {a['eId']: a for a in consolidation['annexes']}
    assert annexes['anx_1']['num'] == 'Bilag 1'
    assert annexes['anx_1']['heading'].startswith('EUROPA-PARLAMENTETS OG RÅDETS FORORDNING')
    assert annexes['att_1']['heading'].startswith('Lov nr. 1783 af 28. december 2023')
    assert annexes['att_1']['children'][0]['text'] == '§ 2 Stk. 1. Loven træder i kraft den 1. januar 2024.'


def test_signature(act, consolidation):
    assert act['conclusions']['signature']['place'] == 'Givet på Amalienborg'
    assert act['conclusions']['signature']['signatories'] == ['MARGRETHE R.', 'Søren Pape Poulsen']
    assert consolidation['conclusions']['signature']['signatory'] == 'Peter Hummelgaard'


def test_valid_legaljson(act, consolidation):
    assert LegalJSONValidator().validate(act)
    assert LegalJSONValidator().validate(consolidation)
