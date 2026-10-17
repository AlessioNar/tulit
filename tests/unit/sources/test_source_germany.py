import shutil
from unittest.mock import MagicMock, patch

import pytest

import tulit
from tulit.client.state.germany import GermanyClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.de import work_eli

WORK = 'eli/bund/bgbl-1/2009/s2704'
EXPRESSION = {
    'legislationIdentifier': f'{WORK}/2025-09-30/1/deu',
    'legislationLegalForce': 'InForce',
    'exampleOfWork': {'legislationIdentifier': WORK, 'legislationDate': '2009-08-10'},
    'encoding': [
        {'encodingFormat': 'text/html', 'contentUrl': f'/v1/legislation/{WORK}/2025-09-30/1/deu/regelungstext-1.html'},
        {'encodingFormat': 'application/xml', 'contentUrl': f'/v1/legislation/{WORK}/2025-09-30/1/deu/regelungstext-1.xml'},
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


def test_fetch_rejects_dates_and_originals(tmp_path):
    with pytest.raises(ValueError):
        tulit.fetch(WORK, jurisdiction='DE', date='2020-01-01', download_dir=str(tmp_path))
    with pytest.raises(ValueError):
        tulit.fetch(WORK, jurisdiction='DE', version='original', download_dir=str(tmp_path))


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
