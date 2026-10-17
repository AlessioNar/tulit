import os
import shutil
from unittest.mock import patch

import pytest

import tulit
from tulit.client.eu.cellar import CellarClient
from tulit.parser.exceptions import FileLoadError, ValidationError

ITEM_ID = 'c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02/DOC_1'
META = {
    'celex': '32024R0903',
    'eli': 'http://data.europa.eu/eli/reg/2024/903/oj',
    'cellar_uuid': 'c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1',
    'date_document': '2024-03-13',
    'in_force': True,
    'amends': [],
    'repeals': [],
    'corrects': [],
}


@pytest.fixture
def cellar_item(data_root, tmp_path):
    """A downloaded Formex item laid out as CellarClient.download leaves it."""
    source = data_root / 'sources' / 'eu' / 'eurlex' / 'formex' / ITEM_ID
    target = tmp_path / ITEM_ID
    shutil.copytree(source, target)
    return target


def test_fetch_returns_validated_legaljson_with_meta(cellar_item, tmp_path):
    with patch.object(CellarClient, 'download', return_value=[str(cellar_item)]) as mock_download, \
            patch.object(CellarClient, 'get_metadata', side_effect=lambda celex: dict(META)):
        doc = tulit.fetch('32024R0903', download_dir=str(tmp_path))

    mock_download.assert_called_once_with('32024R0903', format='fmx4', language='eng')
    assert doc['articles'][0]['eId'] == 'art_1'
    assert len(doc['articles']) == 23
    assert doc['meta']['eli'] == META['eli']
    assert doc['meta']['source'] == 'http://publications.europa.eu/resource/cellar/' + ITEM_ID
    assert doc['meta']['valid'] is True


def test_fetch_without_metadata(cellar_item, tmp_path):
    with patch.object(CellarClient, 'download', return_value=[str(cellar_item)]), \
            patch.object(CellarClient, 'get_metadata') as mock_meta:
        doc = tulit.fetch('32024R0903', download_dir=str(tmp_path), metadata=False)

    mock_meta.assert_not_called()
    assert 'meta' not in doc


def test_fetch_uses_temporary_directory_by_default(data_root):
    source = data_root / 'sources' / 'eu' / 'eurlex' / 'formex' / ITEM_ID
    seen = {}

    def fake_download(self, celex, format, language):
        target = f"{self.download_dir}/{ITEM_ID}"
        shutil.copytree(source, target)
        seen['dir'] = self.download_dir
        return [target]

    with patch.object(CellarClient, 'download', fake_download), \
            patch.object(CellarClient, 'get_metadata', side_effect=lambda celex: dict(META)):
        doc = tulit.fetch('32024R0903')

    assert doc['articles']
    assert not os.path.exists(seen['dir'])


def test_fetch_rejects_unknown_format():
    with pytest.raises(ValueError):
        tulit.fetch('32024R0903', format='pdf')


def test_fetch_raises_when_nothing_downloaded(tmp_path):
    with patch.object(CellarClient, 'download', return_value=[]):
        with pytest.raises(FileLoadError):
            tulit.fetch('39999R9999', download_dir=str(tmp_path))


def test_fetch_raises_on_invalid_output(cellar_item, tmp_path):
    with patch.object(CellarClient, 'download', return_value=[str(cellar_item)]), \
            patch.object(CellarClient, 'get_metadata', side_effect=lambda celex: {**META, 'amends': 'not-a-list'}):
        with pytest.raises(ValidationError, match='meta/amends'):
            tulit.fetch('32024R0903', download_dir=str(tmp_path))
