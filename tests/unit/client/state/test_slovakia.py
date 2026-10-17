import shutil
from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.slovakia import SlovLexClient, act_path
from tulit.parser.exceptions import FileLoadError

LISTING = b'''<html><body>
<a href="vyhlasene_znenie.html">vyhlasene</a>
<a href="20180525.html"></a><a href="20240701.html"></a><a href="20260818.html"></a>
<a href="../../../ZZ/2026/168/20260818.html">168/2026</a>
</body></html>'''


@pytest.mark.parametrize('identifier, path', [
    ('18/2018', 'SK/ZZ/2018/18'),
    ('18/2018 Z. z.', 'SK/ZZ/2018/18'),
    ('460/1992 Zb.', 'SK/ZZ/1992/460'),
    ('2018/18', 'SK/ZZ/2018/18'),
    ('SK/ZZ/2018/18', 'SK/ZZ/2018/18'),
])
def test_act_path(identifier, path):
    assert act_path(identifier) == path


def test_act_path_rejects_other_identifiers():
    with pytest.raises(ValueError):
        act_path('zákon o ochrane osobných údajov')


@pytest.fixture
def client(tmp_path):
    client = SlovLexClient(download_dir=str(tmp_path))
    client.session = Mock()
    return client


def test_versions_and_version_on(client):
    client.session.get.return_value = Mock(status_code=200, text=LISTING.decode())
    assert client.versions('18/2018') == ['2018-05-25', '2024-07-01', '2026-08-18']
    assert client.version_on('18/2018', '2025-01-01') == '2024-07-01'
    assert client.version_on('18/2018', '2017-01-01') is None
    assert client.session.get.call_args.args[0] == 'https://static.slov-lex.sk/static/SK/ZZ/2018/18/'


def test_download_original_and_version(client):
    client.session.get.return_value = Mock(status_code=200, content=b'<root xmlns="http://www.metalex.eu/metalex/1.0"/>')
    original = client.download('18/2018')
    consolidated = client.download('18/2018', '2026-08-18')
    urls = [call.args[0] for call in client.session.get.call_args_list]
    assert urls == ['https://static.slov-lex.sk/static/xml/SK/ZZ/2018/18/vyhlasene_znenie.xml',
                    'https://static.slov-lex.sk/static/xml/SK/ZZ/2018/18/20260818.xml']
    assert original.endswith('vyhlasene_znenie.xml') and consolidated.endswith('20260818.xml')


def test_download_missing(client):
    client.session.get.return_value = Mock(status_code=404)
    with pytest.raises(FileLoadError):
        client.download('9999/1999')


class TestSlovakiaSource:
    @pytest.fixture
    def fixture(self, data_root, tmp_path):
        source = data_root / 'sources' / 'member_states' / 'slovakia' / 'slovlex' / '18_2018_20260818.xml'
        target = tmp_path / '18_2018.xml'
        shutil.copy(source, target)
        return str(target)

    def test_original(self, fixture, tmp_path):
        with patch.object(SlovLexClient, 'download', return_value=fixture) as download:
            doc = tulit.fetch('18/2018', jurisdiction='SK', download_dir=str(tmp_path))
        download.assert_called_once_with('SK/ZZ/2018/18')
        meta = doc['meta']
        assert (meta['version'], meta['version_date'], meta['date_document']) == (
            'original', '2018-01-30', '2017-11-29')
        assert meta['source'] == 'https://www.slov-lex.sk/ezbierky/pravne-predpisy/SK/ZZ/2018/18'

    def test_consolidated(self, fixture, tmp_path):
        with patch.object(SlovLexClient, 'version_on', return_value='2026-08-18') as version_on, \
                patch.object(SlovLexClient, 'download', return_value=fixture) as download:
            doc = tulit.fetch('18/2018', jurisdiction='SK', version='consolidated', date='2026-10-01',
                              download_dir=str(tmp_path))
        version_on.assert_called_once_with('SK/ZZ/2018/18', '2026-10-01')
        download.assert_called_once_with('SK/ZZ/2018/18', '2026-08-18')
        assert doc['meta']['version_date'] == '2026-08-18'
        assert doc['meta']['source'].endswith('/SK/ZZ/2018/18/20260818')

    def test_no_version_on_date(self, tmp_path):
        with patch.object(SlovLexClient, 'version_on', return_value=None):
            with pytest.raises(FileLoadError, match='No version'):
                tulit.fetch('18/2018', jurisdiction='SK', version='consolidated', date='2000-01-01',
                            download_dir=str(tmp_path))
