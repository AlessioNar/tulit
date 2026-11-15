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


def _version(norm, date, *paragraphs):
    body = ''.join(f'<p class="{cls}">{text}</p>' for cls, text in paragraphs)
    return f'<version id_norma="{norm}" fecha_publicacion="{date}" fecha_vigencia="{date}">{body}</version>'


def _block(id, kind, title, *versions, expiry=None):
    expiry = f' fecha_caducidad="{expiry}"' if expiry else ''
    return f'<bloque id="{id}" tipo="{kind}" titulo="{title}"{expiry}>{"".join(versions)}</bloque>'


@pytest.fixture
def code(tmp_path):
    # Shaped on the Civil Code (BOE-A-1889-4763) and the Criminal Code (BOE-A-1995-25444)
    act = 'BOE-A-1889-4763'
    old = ('18890816',)
    blocks = [
        _block('pr', 'preambulo', '', _version('BOE-A-1889-9999', *old, ('parrafo', 'Preámbulo corregido.'))),
        _block('ti', 'encabezado', 'TÍTULO I',
               _version(act, *old, ('titulo_num', 'TÍTULO I'), ('titulo_tit', 'De los españoles'))),
        _block('a1', 'precepto', 'Art 1', _version(act, *old, ('articulo', 'Artículo 1.'), ('parrafo', 'Son.'))),
        _block('ss', 'precepto', 'Sección segunda', _version(act, *old, ('seccion', 'Sección segunda. Del registro'))),
        _block('a2', 'precepto', 'Art. 2 bis',
               _version(act, *old, ('articulo', 'Art. 2 bis. Registro.'), ('parrafo', 'Texto.'))),
        _block('a3-6', 'precepto', 'Artículo 3 quáter ',
               _version(act, *old, ('articulo', 'Artículo 3 quáter.'), ('parrafo', 'Texto.'))),
        _block('a4', 'precepto', 'Art 4', _version(act, *old, ('articulo', 'Artículo 4.'), ('parrafo', 'Viejo.')),
               expiry='20000101'),
        _block('as4a6', 'precepto', 'Arts 4 al 6',
               _version('BOE-A-2000-1', '20000101', ('articulo', 'Arts. 4 a 6'), ('parrafo', '(Derogados)'))),
        _block('primera', 'precepto', 'Primera',
               _version(act, *old, ('articulo', 'Primera.'), ('parrafo', 'Transitoria.'))),
        _block('dg', 'encabezado', 'Disposiciones generales',
               _version(act, *old, ('seccion', 'Disposiciones generales'))),
        _block('an', 'encabezado', 'ANEXO 1',
               _version(act, *old, ('anexo_num', 'ANEXO 1'), ('anexo_tit', 'Familias'), ('parrafo', 'Agraria.'),
                        ('parrafo', 'Minera.'))),
    ]
    folder = tmp_path / act
    folder.mkdir()
    (folder / 'texto.xml').write_text(f'<response><data><texto>{"".join(blocks)}</texto></data></response>',
                                      encoding='utf-8')
    (folder / 'metadatos.xml').write_text(
        f'<response><data><metadatos><identificador>{act}</identificador><titulo>Código Civil</titulo>'
        '</metadatos></data></response>', encoding='utf-8')
    return str(folder)


def test_abbreviated_article_titles(code):
    articles = {a['eId']: a for a in parse(code)['articles']}
    assert (articles['art_1']['num'], articles['art_1']['heading'], articles['art_1']['parent']) == (
        'Artículo 1', None, 'tit_I')
    assert (articles['art_2-bis']['num'], articles['art_2-bis']['heading']) == ('Artículo 2 bis', 'Registro')
    assert articles['art_3-quater']['num'] == 'Artículo 3 quáter'
    assert articles['art_primera']['parent'] is None


def test_headings_filed_as_provisions(code):
    doc = parse(code)
    section = doc['chapters'][1]
    assert (section['type'], section['num'], section['heading']) == ('section', 'Sección segunda', 'Del registro')
    assert 'Sección segunda' not in [a['num'] for a in doc['articles']]
    assert {a['eId']: a['parent'] for a in doc['articles']}['art_2-bis'] == section['eId']


def test_unnumbered_heading(code):
    section = parse(code)['chapters'][-1]
    assert (section['num'], section['heading']) == (None, 'Disposiciones generales')


def test_annexes(code):
    annexes = parse(code)['annexes']
    assert [(a['eId'], a['num'], a['heading']) for a in annexes] == [('anx_1', 'ANEXO 1', 'Familias')]
    assert [c['text'] for c in annexes[0]['children']] == ['Agraria.', 'Minera.']


def test_expired_blocks_left_out_of_consolidated(code):
    current = [a['eId'] for a in parse(code)['articles']]
    assert 'art_4' not in current and 'art_4-6' in current
    assert 'art_4' in [a['eId'] for a in parse(code, date='1999-01-01')['articles']]
    original = [a['eId'] for a in parse(code, version='original')['articles']]
    assert 'art_4' in original and 'art_4-6' not in original


def test_original_keeps_corrections_applying_from_the_start(code):
    preamble = parse(code, version='original')['preamble']
    assert [r['text'] for r in preamble['recitals']] == ['Preámbulo corregido.']


GAZETTE = '''<documento><metadatos><identificador>BOE-A-2026-21445</identificador>
<titulo>Real Decreto 824/2026, de 14 de octubre, por el que se modifica el Reglamento.</titulo>
<fecha_publicacion>20261015</fecha_publicacion><fecha_vigencia>20261016</fecha_vigencia></metadatos>
<texto>
<p class="parrafo">El vigente Reglamento necesita cambios.</p>
<p class="parrafo">Por otra parte, se actualizan los módulos.</p>
<p class="centro_redonda">DISPONGO:</p>
<p class="articulo">Artículo único. Modificación del Reglamento de asistencia jurídica gratuita.</p>
<p class="parrafo">El Reglamento queda modificado como sigue:</p>
<p class="parrafo_2">Uno. El anexo II se sustituye por el que figura a continuación:</p>
<blockquote class="sangrado"><p class="anexo_num">«ANEXO II</p>
<p class="parrafo">1. Un 70 por 100.»</p></blockquote>
<p class="parrafo_2">Dos. Se suprime el artículo 5.</p>
<p class="articulo">Disposición final única. Entrada en vigor.</p>
<p class="parrafo">Entra en vigor mañana.</p>
<p class="parrafo_2">Dado el 14 de octubre de 2026.</p>
<p class="firma_rey">FELIPE R.</p>
<p class="anexo_num">ANEXO</p>
<p class="anexo_tit">Módulos</p>
<p class="parrafo">Abogacía: 100 euros.</p>
</texto></documento>'''


@pytest.fixture
def gazette(tmp_path):
    path = tmp_path / 'BOE-A-2026-21445.xml'
    path.write_text(GAZETTE, encoding='utf-8')
    return str(path)


def test_gazette(gazette):
    doc = parse(gazette, version='original')
    assert doc['preface'].startswith('Real Decreto 824/2026')
    assert doc['preamble']['formula'] is None
    assert doc['preamble']['recitals'][0]['text'] == 'El vigente Reglamento necesita cambios.'
    articles = {a['eId']: a for a in doc['articles']}
    assert list(articles) == ['art_unico', 'art_df-unica']
    assert articles['art_df-unica']['heading'] == 'Entrada en vigor'
    assert doc['conclusions']['signature']['date'] == '14 de octubre de 2026'
    assert [(a['num'], a['heading']) for a in doc['annexes']] == [('ANEXO', 'Módulos')]


def test_amendments_keep_quoted_text(gazette):
    children = parse(gazette, version='original')['articles'][0]['children']
    assert [c['eId'] for c in children] == ['unp_1', 'par_uno', 'par_dos']
    replace, delete = children[1]['amendment'], children[2]['amendment']
    assert (replace['action'], replace['amended_act']) == ('substitute', 'Reglamento de asistencia jurídica gratuita')
    assert replace['quoted'] == [{'kind': 'text', 'text': 'ANEXO II 1. Un 70 por 100.'}]
    assert (delete['action'], delete['quoted']) == ('delete', [])
    assert children[0]['amendment'] is None


def test_single_amendment_and_false_positives():
    from tulit.parser.xml.boe_consolidated import _mark_amendments
    children = [{'text': 'La Ley 41/2002 queda modificada como sigue:', 'amendment': None},
                {'text': 'Se incluye una nueva letra l) en el apartado 1: «l) El respeto.»', 'amendment': None}]
    _mark_amendments('Modificación de la Ley 41/2002, de 14 de noviembre', children)
    assert children[0]['amendment'] is None
    assert children[1]['amendment']['action'] == 'insert'
    assert children[1]['amendment']['quoted'] == [{'kind': 'text', 'text': 'l) El respeto.'}]
    other = [{'text': 'Se modifica el plazo: «diez días».', 'amendment': None}]
    _mark_amendments('Plazos', other)
    assert other[0]['amendment'] is None


def test_royal_formula_without_preamble_heading(gazette, tmp_path):
    path = tmp_path / 'ley.xml'
    path.write_text(GAZETTE.replace('<p class="parrafo">El vigente', '<p class="centro_redonda">FELIPE VI</p>'
                                    '<p class="parrafo">Sabed: Que las Cortes Generales han aprobado.</p>'
                                    '<p class="parrafo">El vigente'), encoding='utf-8')
    preamble = parse(str(path), version='original')['preamble']
    assert preamble['formula'] == 'FELIPE VI Sabed: Que las Cortes Generales han aprobado.'
    assert preamble['recitals'][0]['text'] == 'El vigente Reglamento necesita cambios.'
