import shutil
from unittest.mock import patch

import pytest

import tulit
from tulit.client.state.finlex import FinlexClient
from tulit.parser.exceptions import FileLoadError
from tulit.sources.fi import statute_number


@pytest.mark.parametrize('identifier, expected', [
    ('1050/2018', ('2018', '1050')),
    ('sd/2018/1050', ('2018', '1050')),
    ('http://data.finlex.fi/eli/sd/2018/1050/ajantasa', ('2018', '1050')),
])
def test_statute_number(identifier, expected):
    assert statute_number(identifier) == expected


def test_statute_number_rejects_text():
    with pytest.raises(ValueError):
        statute_number('tietosuojalaki')


@pytest.fixture
def consolidated(data_root, tmp_path):
    source = data_root / 'sources' / 'member_states' / 'finland' / 'finlex' / '1050_2018_consolidated_fin.xml'
    target = tmp_path / 'finlex.xml'
    shutil.copy(source, target)
    return str(target)


def test_fetch_consolidated(consolidated, tmp_path):
    with patch.object(FinlexClient, 'download', return_value=consolidated) as download:
        doc = tulit.fetch('1050/2018', jurisdiction='FI', version='consolidated', download_dir=str(tmp_path))
    download.assert_called_once_with('2018', '1050', consolidated=True, language='fin')
    assert doc['meta']['eli'] == 'http://data.finlex.fi/eli/sd/2018/1050'
    assert doc['meta']['version'] == 'consolidated'
    # chapters are the only divisions; sections are the articles and subsections their paragraphs
    assert [c['eId'] for c in doc['chapters']] == ['cpt_1', 'cpt_2', 'cpt_3', 'cpt_4', 'cpt_5', 'cpt_6']
    assert doc['articles'][1]['parent'] == 'cpt_1'


def test_fetch_by_eli_and_language(consolidated, tmp_path):
    with patch.object(FinlexClient, 'download', return_value=consolidated) as download:
        tulit.fetch('http://data.finlex.fi/eli/sd/2018/1050', language='swe', download_dir=str(tmp_path))
    download.assert_called_once_with('2018', '1050', consolidated=False, language='swe')


def test_missing_statute(tmp_path):
    with patch.object(FinlexClient, 'download', return_value=None):
        with pytest.raises(FileLoadError, match='Finlex has no'):
            tulit.fetch('1/1889', jurisdiction='FI', download_dir=str(tmp_path))


def test_client_sends_user_agent(tmp_path):
    assert 'tulit' in FinlexClient(download_dir=str(tmp_path)).session.headers['User-Agent']
