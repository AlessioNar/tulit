import json
from unittest.mock import patch

import pytest

from tulit import __version__
from tulit.cli import main


@pytest.fixture
def akn_file(data_root):
    return str(data_root / 'sources' / 'eu' / 'eurlex' / 'akn' / '32014L0092.akn')


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(['--version'])
    assert exit_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_formats_lists_registry(capsys):
    assert main(['formats']) == 0
    out = capsys.readouterr().out
    assert 'formex  (fmx4, formex4)' in out
    assert 'cellar-xhtml  (xhtml)' in out


def test_parse_to_stdout(akn_file, capsys):
    assert main(['parse', '-f', 'akn', akn_file]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc['articles'][0]['eId'] == 'art_1'


def test_parse_to_file(akn_file, tmp_path):
    output = tmp_path / 'out.json'
    assert main(['parse', '-f', 'akomantoso', akn_file, '-o', str(output), '--indent', '0']) == 0
    assert json.loads(output.read_text(encoding='utf-8'))['articles']


def test_parse_unknown_format(akn_file, capsys):
    assert main(['parse', '-f', 'nope', akn_file]) == 1
    assert "No parser registered for format 'nope'" in capsys.readouterr().err


def test_get_passes_options_to_fetch(tmp_path, capsys):
    with patch('tulit.cli.fetch', return_value={'articles': []}) as mock_fetch:
        code = main(['get', '32024R0903', '-f', 'xhtml', '-l', 'fra', '--no-meta',
                     '--no-validate', '--download-dir', str(tmp_path)])

    assert code == 0
    mock_fetch.assert_called_once_with(
        '32024R0903', format='xhtml', language='fra', download_dir=str(tmp_path),
        metadata=False, validate=False,
    )
    assert json.loads(capsys.readouterr().out) == {'articles': []}


def test_get_reports_errors(capsys):
    from tulit.parser.exceptions import FileLoadError
    with patch('tulit.cli.fetch', side_effect=FileLoadError('nothing found')):
        assert main(['get', '39999R9999']) == 1
    assert 'tulit: error: nothing found' in capsys.readouterr().err
