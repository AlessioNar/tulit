import pytest

from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser
from tulit.parser.xml.boe_consolidated import BOEConsolidatedParser


@pytest.fixture(scope='module')
def folder(data_root):
    return str(data_root / 'sources' / 'member_states' / 'spain' / 'boe' / 'BOE-A-2018-16673')


def parse(folder, **options):
    return BOEConsolidatedParser(**options).parse(folder).to_dict()


def test_registered():
    parser = get_parser('boe-consolidated', version='original')
    assert isinstance(parser, BOEConsolidatedParser) and parser.version == 'original'


def test_preface_and_preamble(folder):
    doc = parse(folder)
    assert doc['preface'].startswith('Ley Orgánica 3/2018, de 5 de diciembre')
    assert doc['preamble']['formula'].startswith('FELIPE VI REY DE ESPAÑA')
    assert doc['preamble']['recitals'][0]['eId'] == 'rct_1'


def test_titles_articles_and_paragraphs(folder):
    doc = parse(folder)
    assert doc['chapters'][0] == {'eId': 'tit_I', 'type': 'title', 'num': 'TÍTULO I',
                                  'heading': 'Disposiciones generales', 'parent': None}
    art3 = next(a for a in doc['articles'] if a['eId'] == 'art_3')
    assert (art3['num'], art3['heading'], art3['parent']) == (
        'Artículo 3', 'Datos de las personas fallecidas', 'tit_I')
    assert [c['eId'] for c in art3['children']] == ['par_1', 'par_2', 'par_3']
    # an unnumbered paragraph continues the numbered one before it
    assert 'Como excepción' in art3['children'][0]['text']


def test_provisions_outside_titles(folder):
    doc = parse(folder)
    provisions = {a['eId']: a for a in doc['articles']}
    assert provisions['art_da']['num'] == 'Disposición adicional primera'
    assert provisions['art_da']['parent'] is None
    assert provisions['art_53-bis']['parent'] == 'tit_II'


def test_editorial_notes_left_out(folder):
    text = ' '.join(c['text'] for a in parse(folder)['articles'] for c in a['children'])
    assert 'Se añade el apartado' not in text and 'Se modifica' not in text


def test_versions(folder):
    current = {a['eId']: a for a in parse(folder)['articles']}
    original = {a['eId']: a for a in parse(folder, version='original')['articles']}
    on_2019 = {a['eId']: a for a in parse(folder, date='2019-01-01')['articles']}
    # article 5 bis and the 23rd additional provision were added by later acts
    assert 'art_53-bis' in current and 'art_da-23' in current
    assert 'art_53-bis' not in original and 'art_da-23' not in original
    assert len(current['art_2']['children']) == 5
    assert len(original['art_2']['children']) == len(on_2019['art_2']['children']) == 4


def test_signature(folder):
    signature = parse(folder)['conclusions']['signature']
    assert (signature['place'], signature['date'], signature['signatory']) == (
        'Madrid', '5 de diciembre de 2018', 'FELIPE R.')
    assert signature['signatories'][1] == 'El Presidente del Gobierno, PEDRO SÁNCHEZ PÉREZ-CASTEJÓN'


def test_valid(folder):
    assert LegalJSONValidator().validate(parse(folder))
    assert LegalJSONValidator().validate(parse(folder, version='original'))
