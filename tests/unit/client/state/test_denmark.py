import shutil
from unittest.mock import Mock, patch

import pytest
from lxml import etree

import tulit
from tulit.client.state.denmark import (
    RetsinformationClient, consolidated_act, normalise_eli_path
)
from tulit.parser.exceptions import FileLoadError


@pytest.fixture
def folder(data_root):
    return data_root / 'sources' / 'member_states' / 'denmark' / 'retsinformation'


@pytest.fixture
def client(tmp_path):
    return RetsinformationClient(download_dir=str(tmp_path))


@pytest.mark.parametrize('identifier, path', [
    ('lta/2018/502', 'lta/2018/502'),
    ('eli/lta/2018/502', 'lta/2018/502'),
    ('https://www.retsinformation.dk/eli/lta/2018/502/xml', 'lta/2018/502'),
    ('accn/A20180050230', 'accn/A20180050230'),
])
def test_normalise_eli_path(identifier, path):
    assert normalise_eli_path(identifier) == path


def test_normalise_rejects_other_identifiers():
    with pytest.raises(ValueError):
        normalise_eli_path('LOV nr 502')


def test_consolidated_act(folder):
    root = etree.parse(str(folder / 'lta_2024_289.xml')).getroot()
    assert consolidated_act(root) == ('lta/2018/502', '2018-05-23')
    assert consolidated_act(etree.parse(str(folder / 'lta_2018_502.xml')).getroot()) is None


def test_download_saves_xml(client, tmp_path):
    response = Mock(content=b'<?xml version="1.0"?><Dokument/>')
    client.session = Mock()
    client.session.get.return_value = response
    path = client.download('lta/2018/502')
    assert path.endswith('lta_2018_502.xml')
    assert client.session.get.call_args.args[0] == 'https://www.retsinformation.dk/eli/lta/2018/502/xml'


def test_download_rejects_html(client):
    client.session = Mock()
    client.session.get.return_value = Mock(content=b'<!DOCTYPE html><html></html>')
    with pytest.raises(FileLoadError):
        client.download('lta/2018/502')


def test_find_consolidation_checks_the_introduction(client, folder):
    results = [
        {'retsinfoLink': '/eli/lta/2020/1', 'documentTypeEliCode': 'LBKH', 'isHistoryFlag': True},
        {'retsinfoLink': '/eli/lta/2024/289', 'documentTypeEliCode': 'LBKH', 'isHistoryFlag': False},
    ]
    with patch.object(client, 'search', return_value=results), \
            patch.object(client, 'download', return_value=str(folder / 'lta_2024_289.xml')) as download:
        assert client.find_consolidation('lta/2018/502', 'Databeskyttelsesloven') == 'lta/2024/289'
        assert client.find_consolidation('lta/2019/1', 'Databeskyttelsesloven') is None
    download.assert_called_with('lta/2024/289')


class TestDenmarkSource:
    @pytest.fixture
    def downloads(self, folder, tmp_path):
        def fake_download(self, identifier):
            path = normalise_eli_path(identifier)
            target = tmp_path / (path.replace('/', '_') + '.xml')
            shutil.copy(folder / target.name, target)
            return str(target)
        return fake_download

    def test_identifier_decides_version(self, downloads, tmp_path):
        with patch.object(RetsinformationClient, 'download', downloads):
            act = tulit.fetch('lta/2018/502', jurisdiction='DK', download_dir=str(tmp_path))
            consolidation = tulit.fetch('https://www.retsinformation.dk/eli/lta/2024/289',
                                        download_dir=str(tmp_path))
        assert act['meta']['version'] == 'original'
        assert act['meta']['version_date'] == '2018-05-23'
        assert consolidation['meta']['version'] == 'consolidated'
        assert consolidation['meta']['version_date'] == '2024-03-21'
        assert consolidation['meta']['eli'] == 'https://www.retsinformation.dk/eli/lta/2018/502'
        assert consolidation['meta']['source'] == 'https://www.retsinformation.dk/eli/lta/2024/289'

    def test_original_of_a_consolidation(self, downloads, tmp_path):
        with patch.object(RetsinformationClient, 'download', downloads):
            doc = tulit.fetch('lta/2024/289', jurisdiction='DK', version='original',
                              download_dir=str(tmp_path))
        assert doc['meta']['source'] == 'https://www.retsinformation.dk/eli/lta/2018/502'
        assert doc['preamble']['formula'].startswith('VI MARGRETHE')

    def test_consolidation_of_an_act(self, downloads, tmp_path):
        with patch.object(RetsinformationClient, 'download', downloads), \
                patch.object(RetsinformationClient, 'find_consolidation', return_value='lta/2024/289'):
            doc = tulit.fetch('lta/2018/502', jurisdiction='DK', version='consolidated',
                              download_dir=str(tmp_path))
        assert doc['meta']['source'] == 'https://www.retsinformation.dk/eli/lta/2024/289'

    def test_no_consolidation(self, downloads, tmp_path):
        with patch.object(RetsinformationClient, 'download', downloads), \
                patch.object(RetsinformationClient, 'find_consolidation', return_value=None):
            with pytest.raises(FileLoadError, match='original text is the text in force'):
                tulit.fetch('lta/2018/502', jurisdiction='DK', version='consolidated',
                            download_dir=str(tmp_path))

    def test_date_not_supported(self):
        with pytest.raises(ValueError, match='a date cannot be selected'):
            tulit.fetch('lta/2018/502', jurisdiction='DK', date='2020-01-01')
