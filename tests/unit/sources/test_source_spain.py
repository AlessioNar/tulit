import shutil
from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.boe import BOEClient
from tulit.parser.exceptions import FileLoadError


@pytest.fixture
def folder(data_root, tmp_path):
    source = data_root / 'sources' / 'member_states' / 'spain' / 'boe' / 'BOE-A-2018-16673'
    target = tmp_path / 'BOE-A-2018-16673'
    shutil.copytree(source, target)
    return str(target)


def test_original(folder, tmp_path):
    with patch.object(BOEClient, 'download_consolidated', return_value=folder):
        doc = tulit.fetch('BOE-A-2018-16673', jurisdiction='ES', download_dir=str(tmp_path))
    meta = doc['meta']
    assert (meta['version'], meta['version_date'], meta['date_document']) == ('original', '2018-12-06', '2018-12-05')
    assert meta['eli'] == 'https://www.boe.es/eli/es/lo/2018/12/05/3'
    assert 'art_53-bis' not in {a['eId'] for a in doc['articles']}


def test_consolidated_on_date(folder, tmp_path):
    with patch.object(BOEClient, 'download_consolidated', return_value=folder):
        doc = tulit.fetch('BOE-A-2018-16673', jurisdiction='ES', version='consolidated', date='2022-01-01',
                          download_dir=str(tmp_path))
    assert doc['meta']['version_date'] == '2021-06-16'
    assert doc['meta']['in_force'] is True


def test_original_falls_back_to_gazette(tmp_path):
    gazette = tmp_path / 'BOE-A-2020-1.xml'  # the parser is mocked
    gazette.write_text('<documento><metadatos><fecha_publicacion>20200102</fecha_publicacion></metadatos></documento>')
    with patch.object(BOEClient, 'download_consolidated', side_effect=FileLoadError('not consolidated')), \
            patch.object(BOEClient, 'download_gazette', return_value=str(gazette)) as download_gazette:
        with patch('tulit.api.get_parser') as get_parser:
            parser = Mock(valid=None)
            parser.to_dict.return_value = {'preface': 'x', 'preamble': {}, 'articles': []}
            get_parser.return_value = parser
            doc = tulit.fetch('BOE-A-2020-1', jurisdiction='ES', download_dir=str(tmp_path), validate=False)
    download_gazette.assert_called_once_with('BOE-A-2020-1')
    get_parser.assert_called_once_with('boe-consolidated', version='original')
    assert (doc['meta']['version'], doc['meta']['version_date']) == ('original', '2020-01-02')


def test_consolidated_requires_the_database(tmp_path):
    with patch.object(BOEClient, 'download_consolidated', side_effect=FileLoadError('not consolidated')):
        with pytest.raises(FileLoadError):
            tulit.fetch('BOE-A-2020-1', jurisdiction='ES', version='consolidated', download_dir=str(tmp_path))


def test_download_consolidated_sends_accept_header(tmp_path):
    response = Mock(status_code=200, content=b'<response/>')
    with patch('tulit.client.state.boe.requests.Session.get', return_value=response) as get:
        folder = BOEClient(download_dir=str(tmp_path)).download_consolidated('BOE-A-2018-16673')
    assert folder.endswith('BOE-A-2018-16673')
    assert get.call_args.kwargs['headers']['Accept'] == 'application/xml'
    assert [c.args[0].rsplit('/', 1)[-1] for c in get.call_args_list] == ['texto', 'metadatos']


def test_download_consolidated_not_found(tmp_path):
    response = Mock(status_code=404, content=b'<response><status><code>404</code></status></response>')
    with patch('tulit.client.state.boe.requests.Session.get', return_value=response):
        with pytest.raises(FileLoadError):
            BOEClient(download_dir=str(tmp_path)).download_consolidated('BOE-A-2024-99999')


def test_invalid_identifier(tmp_path):
    with pytest.raises(ValueError):
        BOEClient(download_dir=str(tmp_path)).download_consolidated('Ley 3/2018')


def test_client_retries_connection_resets(tmp_path):
    adapter = BOEClient(download_dir=str(tmp_path)).session.get_adapter('https://www.boe.es/')
    assert adapter.max_retries.total >= 3 and adapter.max_retries.connect >= 3


def test_resolve_eli(tmp_path):
    page = ('<meta  about="https://www.boe.es/eli/es/lo/2018/12/05/3" '
            'property="http://data.europa.eu/eli/ontology#id_local" content="BOE-A-2018-16673" />')
    response = Mock(status_code=200, text=page)
    with patch('tulit.client.state.boe.requests.Session.get', return_value=response) as get:
        boe_id = BOEClient(download_dir=str(tmp_path)).resolve_eli('https://www.boe.es/eli/es/lo/2018/12/05/3/con')
    assert boe_id == 'BOE-A-2018-16673'
    assert get.call_args.args[0] == 'https://www.boe.es/eli/es/lo/2018/12/05/3'


def test_fetch_by_eli(folder, tmp_path):
    with patch.object(BOEClient, 'resolve_eli', return_value='BOE-A-2018-16673'), \
            patch.object(BOEClient, 'download_consolidated', return_value=folder) as download:
        doc = tulit.fetch('https://www.boe.es/eli/es/lo/2018/12/05/3', download_dir=str(tmp_path))
    download.assert_called_once_with('BOE-A-2018-16673')
    assert doc['meta']['jurisdiction'] == 'ES'
