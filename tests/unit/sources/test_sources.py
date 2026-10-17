import shutil
from unittest.mock import patch

import pytest

import tulit
from tulit.client.eu.cellar import CellarClient
from tulit.client.state.austria import AustriaRISClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources import (
    Retrieval, Source, eli_pattern, get_source, list_sources, register_source, source_for_eli
)
from tulit.sources import registry
from tulit.sources.eu import EUSource

FORMEX_ITEM = 'c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02/DOC_1'
META = {'celex': '32024R0903', 'eli': 'http://data.europa.eu/eli/reg/2024/903/oj',
        'cellar_uuid': 'c008bcb6', 'date_document': '2024-03-13', 'in_force': True,
        'amends': [], 'repeals': [], 'corrects': []}


@pytest.fixture
def formex_item(data_root, tmp_path):
    source = data_root / 'sources' / 'eu' / 'eurlex' / 'formex' / FORMEX_ITEM
    shutil.copytree(source, tmp_path / FORMEX_ITEM)
    return tmp_path / FORMEX_ITEM


@pytest.fixture
def austrian_law(data_root, tmp_path):
    source = data_root / 'sources' / 'member_states' / 'austria' / 'ris' / '10001597'
    target = tmp_path / 'AT' / '10001597' / '2026-10-17'
    shutil.copytree(source, target)
    return target


class TestRegistry:
    def test_builtin_sources(self):
        assert {'EU', 'AT'} <= set(list_sources())
        assert get_source('eu').code == 'EU'

    def test_unknown_jurisdiction(self):
        with pytest.raises(ValueError, match="Unsupported jurisdiction 'ZZ'"):
            get_source('ZZ')

    def test_eu_eli_dispatch(self):
        source, identifier = source_for_eli('https://data.europa.eu/eli/reg/2016/679/oj/')
        assert source.code == 'EU'
        assert identifier == 'https://data.europa.eu/eli/reg/2016/679/oj'

    def test_register_custom_source(self):
        class Dummy(Source):
            code = 'XX'
            name = 'Dummy'
            eli_patterns = (eli_pattern('https://example.org/eli/', r'act/\d+'),)

            def retrieve(self, *args, **kwargs):
                raise NotImplementedError

        register_source(Dummy())
        try:
            assert get_source('xx').name == 'Dummy'
            assert source_for_eli('http://example.org/eli/act/7')[1] == 'act/7'
            assert Dummy().default_version == 'original'
        finally:
            registry._sources.pop('XX', None)


class TestFetchValidation:
    def test_version_not_published(self):
        with pytest.raises(ValueError, match='does not publish the original version'):
            tulit.fetch('10001597', jurisdiction='AT', version='original')

    def test_unknown_version(self):
        with pytest.raises(ValueError, match="Unknown version 'latest'"):
            tulit.fetch('32024R0903', version='latest')

    def test_language_not_published(self):
        with pytest.raises(ValueError, match="publishes in deu, not 'fra'"):
            tulit.fetch('10001597', jurisdiction='AT', language='fra')

    def test_option_for_other_source(self):
        with pytest.raises(ValueError, match='Unsupported option'):
            tulit.fetch('10001597', jurisdiction='AT', format='xhtml')

    def test_eli_of_wrong_jurisdiction(self):
        with pytest.raises(ValueError, match='is not an ELI of Austria'):
            tulit.fetch('http://data.europa.eu/eli/reg/2016/679/oj', jurisdiction='AT')


class TestEUSource:
    def test_consolidated_version(self, formex_item, tmp_path):
        with patch.object(CellarClient, 'get_consolidated_celex',
                          return_value=('02024R0903-20250101', '2025-01-01')) as mock_cons, \
                patch.object(CellarClient, 'download', return_value=[str(formex_item)]) as mock_download, \
                patch.object(CellarClient, 'get_metadata', side_effect=lambda celex: dict(META)):
            doc = tulit.fetch('32024R0903', version='consolidated', date='2025-06-01',
                              download_dir=str(tmp_path))

        mock_cons.assert_called_once_with('32024R0903', '2025-06-01')
        mock_download.assert_called_once_with('02024R0903-20250101', format='fmx4', language='eng')
        assert doc['meta']['version'] == 'consolidated'
        assert doc['meta']['version_date'] == '2025-01-01'
        assert doc['meta']['celex'] == '32024R0903'
        assert doc['meta']['jurisdiction'] == 'EU'

    def test_no_consolidated_version(self, tmp_path):
        with patch.object(CellarClient, 'get_consolidated_celex', return_value=None):
            with pytest.raises(FileLoadError, match='No consolidated version'):
                tulit.fetch('32024R0903', version='consolidated', download_dir=str(tmp_path))

    def test_fetch_by_eli(self, formex_item, tmp_path):
        with patch.object(CellarClient, 'celex_from_eli', return_value='32024R0903'), \
                patch.object(CellarClient, 'download', return_value=[str(formex_item)]) as mock_download, \
                patch.object(CellarClient, 'get_metadata', side_effect=lambda celex: dict(META)):
            doc = tulit.fetch('http://data.europa.eu/eli/reg/2024/903/oj', download_dir=str(tmp_path))

        mock_download.assert_called_once_with('32024R0903', format='fmx4', language='eng')
        assert doc['meta']['version'] == 'original'
        assert doc['meta']['version_date'] == '2024-03-13'

    def test_unknown_eli(self, tmp_path):
        with patch.object(CellarClient, 'celex_from_eli', return_value=None):
            with pytest.raises(FileLoadError, match='No act found'):
                EUSource().retrieve('http://data.europa.eu/eli/reg/1/1/oj', 'original', None, None,
                                    str(tmp_path))


class TestAustriaSource:
    def test_fetch_consolidated(self, austrian_law, tmp_path):
        with patch.object(AustriaRISClient, 'download', return_value=str(austrian_law)) as mock_download:
            doc = tulit.fetch('10001597', jurisdiction='AT', date='2026-10-17',
                              download_dir=str(tmp_path))

        mock_download.assert_called_once_with('10001597', '2026-10-17')
        assert doc['articles'][0]['eId'] == 'art_1'
        assert doc['meta']['eli'] == 'https://www.ris.bka.gv.at/eli/bgbl/i/1999/165'
        assert doc['meta']['version'] == 'consolidated'
        assert doc['meta']['version_date'] == '2026-10-17'
        assert doc['meta']['language'] == 'deu'
        assert doc['meta']['jurisdiction'] == 'AT'


class TestCellarLookups:
    def test_get_consolidated_celex_picks_latest_before_date(self, tmp_path):
        client = CellarClient(download_dir=str(tmp_path))
        bindings = [{'celex': {'value': v}} for v in
                    ('02013R0575-20250101', '02013R0575-20250629', '02013R0575-20270101')]
        with patch.object(client, 'get_results_table', return_value={'results': {'bindings': bindings}}):
            assert client.get_consolidated_celex('32013R0575', '2025-06-30') == \
                ('02013R0575-20250629', '2025-06-29')
            assert client.get_consolidated_celex('32013R0575', '2024-01-01') is None

    def test_celex_from_eli(self, tmp_path):
        client = CellarClient(download_dir=str(tmp_path))
        with patch.object(client, 'get_results_table',
                          return_value={'results': {'bindings': [{'celex': {'value': '32016R0679'}}]}}) as grt:
            assert client.celex_from_eli('https://data.europa.eu/eli/reg/2016/679/oj/') == '32016R0679'
        assert '"http://data.europa.eu/eli/reg/2016/679/oj"' in grt.call_args[0][0]


def test_retrieval_defaults():
    retrieval = Retrieval(path='x', parser='formex', version='original', language='eng')
    assert retrieval.meta == {} and retrieval.parser_options == {}
