import pytest

from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser
from tulit.parser.xml.bwb import BWBParser


@pytest.fixture(scope='module')
def uavg(data_root):
    path = data_root / 'sources' / 'member_states' / 'netherlands' / 'bwb' / 'BWBR0040940.xml'
    return BWBParser().parse(str(path)).to_dict()


def test_registered():
    assert isinstance(get_parser('bwb'), BWBParser)


def test_preface_and_preamble(uavg):
    assert uavg['preface'].startswith('Wet van 16 mei 2018, houdende regels ter uitvoering')
    preamble = uavg['preamble']
    assert preamble['formula'].startswith('Wij Willem-Alexander')
    assert preamble['recitals'][0] == {
        'eId': 'rct_1', 'text': 'Allen, die deze zullen zien of horen lezen, saluut! doen te weten:'}
    assert preamble['final'].startswith('Zo is het, dat Wij')


def test_divisions_keep_dotted_numbers(uavg):
    assert [c['eId'] for c in uavg['chapters']] == ['cpt_1', 'cpt_2', 'sbs_2-1', 'sbs_2-2']
    assert uavg['chapters'][2] == {
        'eId': 'sbs_2-1', 'type': 'subsection', 'num': 'Paragraaf 2.1',
        'heading': 'Oprichting en inrichting van de Autoriteit persoonsgegevens', 'parent': 'cpt_2'}


def test_articles_and_paragraphs(uavg):
    articles = {a['eId']: a for a in uavg['articles']}
    art1 = articles['art_1']
    assert (art1['num'], art1['heading'], art1['parent']) == ('Artikel 1', 'Definities', 'cpt_1')
    # an article without numbered paragraphs: the list belongs to the opening sentence
    assert len(art1['children']) == 1
    assert 'bijzondere categorieën van persoonsgegevens' in art1['children'][0]['text']
    numbered = next(a for a in uavg['articles'] if len(a['children']) > 1)
    assert numbered['children'][0]['eId'] == 'par_1'
    assert numbered['children'][0]['text'].startswith('1 ')


def test_metadata_blocks_left_out(uavg):
    text = ' '.join(c['text'] for a in uavg['articles'] for c in a['children'])
    assert 'Stb.' not in text and 'jci1.3' not in text


def test_signatures(uavg):
    signature = uavg['conclusions']['signature']
    assert (signature['place'], signature['date'], signature['signatory']) == (
        'Wassenaar', '2018-05-16', 'Willem-Alexander')
    assert len(signature['signatories']) == 4
    # the publication line (uitgifte) closes the conclusions
    assert 'tweeëntwintigste mei 2018' in uavg['conclusions']['conclusion_text']


def test_valid(uavg):
    assert LegalJSONValidator().validate(uavg)
