import shutil
from unittest.mock import patch

import pytest

import tulit
from tulit.client.state.irishstatutebook import IrishStatuteBookClient
from tulit.sources.ie import act_number


@pytest.mark.parametrize('identifier', ['7/2018', 'Act 7 of 2018', 'No. 7 of 2018', 'eli/2018/act/7',
                                        'http://www.irishstatutebook.ie/eli/2018/act/7/enacted/en/html'])
def test_act_number(identifier):
    assert act_number(identifier) == ('2018', '7')


@pytest.fixture
def folder(data_root, tmp_path):
    source = data_root / 'sources' / 'member_states' / 'ireland' / 'isb'
    target = tmp_path / 'isb'
    shutil.copytree(source, target)
    return target


def test_enacted(folder, tmp_path):
    with patch.object(IrishStatuteBookClient, 'download',
                      return_value=str(folder / '2018_act_7_enacted.xml')) as download:
        doc = tulit.fetch('7/2018', jurisdiction='IE', download_dir=str(tmp_path))
    download.assert_called_once_with('2018', '7', status='enacted')
    meta = doc['meta']
    assert (meta['version'], meta['version_date'], meta['eli']) == (
        'original', '2018-05-24', 'http://www.irishstatutebook.ie/eli/2018/act/7')


def test_revised(folder, tmp_path):
    with patch.object(IrishStatuteBookClient, 'download',
                      return_value=str(folder / '2018_act_7_revised.xml')) as download:
        doc = tulit.fetch('http://www.irishstatutebook.ie/eli/2018/act/7', version='consolidated',
                          download_dir=str(tmp_path))
    download.assert_called_once_with('2018', '7', status='revised')
    assert doc['meta']['version_date'] == '2026-07-16'
    assert doc['meta']['source'].startswith('https://revisedacts.lawreform.ie/eli/2018/act/7/revised')


def test_revised_url(tmp_path):
    client = IrishStatuteBookClient(download_dir=str(tmp_path))
    with patch.object(client.session, 'get') as get:
        get.return_value.headers = {'Content-Type': 'application/xml'}
        get.return_value.content = b'<act/>'
        client.download('2018', '7', status='revised')
    assert get.call_args.args[0] == 'https://revisedacts.lawreform.ie/eli/2018/act/7/revised/en/xml'
