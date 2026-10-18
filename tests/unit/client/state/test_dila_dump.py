import io
import tarfile
from unittest.mock import MagicMock, patch

import pytest

from tulit.client.state.france_dila import DilaClient, _safe_extract
from tulit.parser.exceptions import FileLoadError, UnsupportedError

LISTING = (b'<a href="Freemium_legi_global_20240101-140000.tar.gz">old</a>'
           b'<a href="Freemium_legi_global_20250713-140000.tar.gz">new</a>'
           b'<a href="LEGI_20250714-210000.tar.gz">daily</a>')


def _archive(members: dict) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def test_global_dump(tmp_path):
    client = DilaClient(download_dir=str(tmp_path))
    with patch.object(client, '_get', return_value=LISTING):
        assert client.global_dump('legi') == ('Freemium_legi_global_20250713-140000.tar.gz', '2025-07-13')


def test_download_and_extract(tmp_path):
    archive = _archive({'legi/global/code_et_TNC_en_vigueur/LEGITEXT000006070721.xml': b'<x/>'})
    client = DilaClient(download_dir=str(tmp_path))
    response = MagicMock(status_code=200)
    response.iter_content.return_value = [archive[:100], archive[100:]]
    response.__enter__.return_value = response
    seen = []
    with patch.object(client, '_get', return_value=LISTING), \
            patch.object(client.session, 'head', return_value=MagicMock(headers={'Content-Length': str(len(archive))})), \
            patch.object(client.session, 'get', return_value=response) as get:
        root = client.download_dump('LEGI', str(tmp_path), progress=lambda done, total: seen.append((done, total)))
        assert root.endswith('legi/global')
        assert (tmp_path / 'legi/global/code_et_TNC_en_vigueur/LEGITEXT000006070721.xml').exists()
        assert seen[-1] == (len(archive), len(archive))
        # A complete download is not repeated
        client.download_dump('LEGI', str(tmp_path))
        assert get.call_count == 1


def test_unknown_base(tmp_path):
    with pytest.raises(UnsupportedError, match='choose JORF or LEGI'):
        DilaClient(download_dir=str(tmp_path)).download_dump('KALI', str(tmp_path))


def test_unsafe_archive(tmp_path):
    with tarfile.open(fileobj=io.BytesIO(_archive({'../escape.xml': b'<x/>'})), mode='r:gz') as tar:
        with pytest.raises((FileLoadError, tarfile.TarError)):
            _safe_extract(tar, str(tmp_path / 'dump'))
    assert not (tmp_path / 'escape.xml').exists()
