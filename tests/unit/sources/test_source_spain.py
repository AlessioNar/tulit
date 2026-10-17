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
    gazette = tmp_path / 'BOE-A-2020-1.xml'  # the parser is mocked, the file is never read
    with patch.object(BOEClient, 'download_consolidated', side_effect=FileLoadError('not consolidated')), \
            patch.object(BOEClient, 'download_gazette', return_value=str(gazette)) as download_gazette:
        with patch('tulit.api.get_parser') as get_parser:
            parser = Mock(valid=None)
            parser.to_dict.return_value = {'preface': 'x', 'preamble': {}, 'articles': []}
            get_parser.return_value = parser
            doc = tulit.fetch('BOE-A-2020-1', jurisdiction='ES', download_dir=str(tmp_path), validate=False)
    download_gazette.assert_called_once_with('BOE-A-2020-1')
    get_parser.assert_called_once_with('boe')
    assert doc['meta']['version'] == 'original'


def test_consolidated_requires_the_database(tmp_path):
    with patch.object(BOEClient, 'download_consolidated', side_effect=FileLoadError('not consolidated')):
        with pytest.raises(FileLoadError):
            tulit.fetch('BOE-A-2020-1', jurisdiction='ES', version='consolidated', download_dir=str(tmp_path))


def test_download_consolidated_sends_accept_header(tmp_path):
    response = Mock(status_code=200, content=b'<response/>')
    with patch('tulit.client.state.boe.requests.get', return_value=response) as get:
        folder = BOEClient(download_dir=str(tmp_path)).download_consolidated('BOE-A-2018-16673')
    assert folder.endswith('BOE-A-2018-16673')
    assert get.call_args.kwargs['headers']['Accept'] == 'application/xml'
    assert [c.args[0].rsplit('/', 1)[-1] for c in get.call_args_list] == ['texto', 'metadatos']


def test_download_consolidated_not_found(tmp_path):
    response = Mock(status_code=404, content=b'<response><status><code>404</code></status></response>')
    with patch('tulit.client.state.boe.requests.get', return_value=response):
        with pytest.raises(FileLoadError):
            BOEClient(download_dir=str(tmp_path)).download_consolidated('BOE-A-2024-99999')


def test_invalid_identifier(tmp_path):
    with pytest.raises(ValueError):
        BOEClient(download_dir=str(tmp_path)).download_consolidated('Ley 3/2018')
