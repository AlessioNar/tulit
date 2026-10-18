import shutil
from unittest.mock import MagicMock, patch

import pytest

import tulit
from tulit.client.state.germany import GermanyClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.xml.akomantoso import GermanLegalDocMLParser
from tulit.sources.de import work_eli

WORK = 'eli/bund/bgbl-1/2009/s2704'
EXPRESSION = {
    'legislationIdentifier': f'{WORK}/2025-09-30/1/deu',
    'legislationLegalForce': 'InForce',
    'exampleOfWork': {'legislationIdentifier': WORK, 'legislationDate': '2009-08-10'},
    'encoding': [
        {'encodingFormat': 'text/html', 'contentUrl': f'/v1/legislation/{WORK}/2025-09-30/1/deu/regelungstext-1.html'},
        {'encodingFormat': 'application/xml',
         'contentUrl': f'/v1/legislation/{WORK}/2025-09-30/1/deu/regelungstext-1.xml'},
    ],
}


@pytest.mark.parametrize('identifier', [
    WORK, f'/{WORK}/', f'{WORK}/2025-09-30/1/deu',
    f'https://testphase.rechtsinformationen.bund.de/v1/legislation/{WORK}/2025-09-30/1/deu/regelungstext-1',
])
def test_work_eli(identifier):
    assert work_eli(identifier) == WORK


def test_work_eli_rejects_other_identifiers():
    with pytest.raises(ValueError):
        work_eli('BGBl. I S. 2704')


@pytest.fixture
def g115(data_root, tmp_path):
    target = tmp_path / 'g115.xml'
    shutil.copy(data_root / 'sources' / 'member_states' / 'germany' / 'portal' / 'g115_2025-09-30.xml', target)
    return str(target)


def test_fetch(g115, tmp_path):
    with patch.object(GermanyClient, 'current_expression', return_value=EXPRESSION) as current, \
            patch.object(GermanyClient, 'download_expression_xml', return_value=g115):
        doc = tulit.fetch(f'https://testphase.rechtsinformationen.bund.de/{WORK}', download_dir=str(tmp_path))
    current.assert_called_once_with(WORK)
    meta = doc['meta']
    assert (meta['jurisdiction'], meta['version'], meta['version_date'], meta['in_force']) == (
        'DE', 'consolidated', '2025-09-30', True)
    assert meta['date_document'] == '2009-08-10'
    assert doc['preface'] == 'Gesetz zur Ausführung von Artikel 115 des Grundgesetzes (Artikel 115-Gesetz - G 115)'
    articles = {a['eId']: a for a in doc['articles']}
    assert len(articles) == 10
    first = articles['art_1']
    assert (first['num'], first['heading']) == ('§ 1', 'Kreditermächtigungen')
    # An unnumbered Absatz keeps its list items in document order
    assert [c['eId'] for c in first['children']] == ['unp_1']
    assert '1. zur Deckung von Ausgaben, 2. zur Aufrechterhaltung' in first['children'][0]['text']
    assert first['children'][0]['text'].endswith('fällig werden.')
    assert [c['eId'] for c in articles['art_1a']['children']][:3] == ['par_1', 'par_2', 'par_3']


def test_fetch_rejects_dates(tmp_path):
    with pytest.raises(ValueError):
        tulit.fetch(WORK, jurisdiction='DE', date='2020-01-01', download_dir=str(tmp_path))
    # An act not promulgated in the Federal Law Gazette has no original version
    with pytest.raises(ValueError):
        tulit.fetch('eli/bund/hist/1898/0616-403-5', jurisdiction='DE', version='original',
                    download_dir=str(tmp_path))


def test_fetch_unknown_act(tmp_path):
    with patch.object(GermanyClient, 'current_expression', return_value=None):
        with pytest.raises(FileLoadError):
            tulit.fetch(WORK, jurisdiction='DE', download_dir=str(tmp_path))


def test_current_expression_matches_work(tmp_path):
    client = GermanyClient(download_dir=str(tmp_path))
    other = {'item': {'exampleOfWork': {'legislationIdentifier': 'eli/bund/bgbl-1/2009/s27'}}}
    response = MagicMock()
    response.json.return_value = {'member': [other, {'item': EXPRESSION}]}
    with patch.object(client, '_make_request', return_value=response) as request:
        assert client.current_expression(f'/{WORK}') is EXPRESSION
    assert request.call_args.kwargs['params']['eli'] == WORK


def test_download_expression_xml(tmp_path):
    client = GermanyClient(download_dir=str(tmp_path))
    response = MagicMock(content=b'<akn:akomaNtoso/>')
    with patch.object(client, '_make_request', return_value=response) as request:
        path = client.download_expression_xml(EXPRESSION)
    assert request.call_args.args[0].endswith('/2025-09-30/1/deu/regelungstext-1.xml')
    with open(path, 'rb') as f:
        assert f.read() == b'<akn:akomaNtoso/>'
    with pytest.raises(FileLoadError):
        client.download_expression_xml({'encoding': []})


NORM = 'xmlns:akn="http://rechtsinformationen.bund.de/schema/norm/0.1"'
ANLAGE_HREF = f'https://www.ris.bund.de/{WORK}/2025-09-30/1/deu/2026-01-01/anlage-regelungstext-1.xml'
ACT = f"""<?xml version="1.0" encoding="UTF-8"?>
<akn:akomaNtoso {NORM}><akn:act name="regelungstext">
<akn:preface><akn:longTitle><akn:p><akn:docTitle>Testgesetz</akn:docTitle></akn:p></akn:longTitle></akn:preface>
<akn:body eId="hauptteil-n1">
 <akn:article eId="art-n1"><akn:num eId="art-n1_bezeichnung-n1"/><akn:heading/>
  <akn:paragraph eId="art-n1_abs-z"><akn:num/><akn:content><akn:p>Artikel 1 bis 4</akn:p></akn:content></akn:paragraph>
 </akn:article>
 <akn:section eId="hauptteil-n1_abschnitt-n1"><akn:num>Erster Abschnitt</akn:num><akn:heading>Allgemeines</akn:heading>
  <akn:article eId="art-z5"><akn:num>§ 5</akn:num><akn:heading>Zweck</akn:heading>
   <akn:paragraph eId="art-z5_abs-z"><akn:num/><akn:content><akn:p>Text.</akn:p></akn:content></akn:paragraph>
  </akn:article>
 </akn:section>
 <akn:section eId="hauptteil-n1_abschnitt-n2"><akn:num>Zweiter Abschnitt</akn:num><akn:heading>Schluss</akn:heading>
  <akn:article eId="art-z6"><akn:num>§ 6</akn:num><akn:heading>Inkrafttreten</akn:heading>
   <akn:paragraph eId="art-z6_abs-z"><akn:num/><akn:content><akn:p>Text.</akn:p></akn:content></akn:paragraph>
  </akn:article>
 </akn:section>
</akn:body>
<akn:attachments><akn:attachment><akn:documentRef href="{ANLAGE_HREF}"/></akn:attachment></akn:attachments>
</akn:act></akn:akomaNtoso>"""
ANLAGE = f"""<?xml version="1.0" encoding="UTF-8"?>
<akn:akomaNtoso {NORM}><akn:doc name="anlage-regelungstext">
<akn:preface><akn:block><akn:docTitle>
 <akn:inline refersTo="anlageregelungstext-num">Anlage 1</akn:inline>
 <akn:inline refersTo="anlageregelungstext-bezug">(zu § 5)</akn:inline>
 <akn:inline refersTo="anlageregelungstext-heading">Liste</akn:inline>
</akn:docTitle></akn:block></akn:preface>
<akn:mainBody><akn:p>Vorbemerkung</akn:p>
 <akn:table><akn:tr><akn:td>1</akn:td><akn:td>Milch</akn:td></akn:tr><akn:tr><akn:td>2</akn:td><akn:td>Brot</akn:td></akn:tr></akn:table>
</akn:mainBody></akn:doc></akn:akomaNtoso>"""


def test_annexes_ordinal_divisions_and_designations(tmp_path):
    act = tmp_path / 'v1_legislation_act_regelungstext-1.xml'
    act.write_text(ACT, encoding='utf-8')
    client = GermanyClient(download_dir=str(tmp_path))
    response = MagicMock(content=ANLAGE.encode('utf-8'))
    with patch.object(client, '_make_request', return_value=response) as request:
        paths = client.download_attachments(str(act))
        assert client.download_attachments(str(act)) == paths  # saved once
    request.assert_called_once()
    assert request.call_args.args[0] == (f'https://testphase.rechtsinformationen.bund.de/v1/legislation/{WORK}'
                                         '/2025-09-30/1/deu/2026-01-01/anlage-regelungstext-1.xml')
    assert paths == [str(tmp_path / 'v1_legislation_act_anlage-regelungstext-1.xml')]

    doc = GermanLegalDocMLParser().parse(str(act)).to_dict()
    assert [(c['eId'], c['num']) for c in doc['chapters']] == [
        ('sct_1', 'Erster Abschnitt'), ('sct_2', 'Zweiter Abschnitt')]
    assert [(a['num'], a['parent'], len(a['children'])) for a in doc['articles']] == [
        ('Artikel 1 bis 4', None, 0), ('§ 5', 'sct_1', 1), ('§ 6', 'sct_2', 1)]
    assert [n['eId'] for n in doc['structure'] if n['type'] != 'article'] == ['sct_1', 'sct_2']
    annex = doc['annexes'][0]
    assert (annex['eId'], annex['num'], annex['heading']) == ('anx_1', 'Anlage 1', 'Liste (zu § 5)')
    assert [c['text'] for c in annex['children']] == ['Vorbemerkung', '1 Milch', '2 Brot']
