import shutil
from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.legilux import LegiluxClient, act_path
from tulit.parser.exceptions import FileLoadError

ACT = 'etat/leg/loi/2016/07/23/n21'
WORK = {'dateDocument': '2016-07-23', 'publicationDate': '2016-08-05',
        'inForceStatus': 'http://data.legilux.public.lu/resource/authority/application-status/in-force'}


@pytest.mark.parametrize('identifier', [
    ACT, f'eli/{ACT}/jo', f'http://data.legilux.public.lu/eli/{ACT}/jo/fr/xml',
    f'https://legilux.public.lu/eli/{ACT}/consolide/20180820',
])
def test_act_path(identifier):
    assert act_path(identifier) == ACT


@pytest.fixture
def files(data_root, tmp_path):
    folder = data_root / 'sources' / 'member_states' / 'luxembourg' / 'legilux'
    copies = {}
    for name in ('jo', 'consolide-20180820'):
        source = folder / f'eli-etat-leg-loi-2016-07-23-n21-{name}-fr-xml.xml'
        copies[name] = str(shutil.copy(source, tmp_path / source.name))
    return copies


def test_original(files, tmp_path):
    with patch.object(LegiluxClient, 'work_metadata', return_value=WORK), \
            patch.object(LegiluxClient, 'download_version', return_value=files['jo']) as download:
        doc = tulit.fetch(ACT, jurisdiction='LU', download_dir=str(tmp_path))
    download.assert_called_once_with(ACT)
    meta = doc['meta']
    assert (meta['version'], meta['version_date'], meta['date_document'], meta['in_force']) == (
        'original', '2016-08-05', '2016-07-23', True)
    assert doc['articles'][0]['eId'] == 'art_1er'


def test_consolidated_on_date(files, tmp_path):
    with patch.object(LegiluxClient, 'work_metadata', return_value=WORK), \
            patch.object(LegiluxClient, 'consolidation_dates', return_value=['2018-08-20', '2021-01-01']), \
            patch.object(LegiluxClient, 'download_version', return_value=files['consolide-20180820']) as download:
        doc = tulit.fetch(f'http://data.legilux.public.lu/eli/{ACT}/jo', version='consolidated',
                          date='2020-06-01', download_dir=str(tmp_path))
    download.assert_called_once_with(ACT, consolidated='2018-08-20')
    assert doc['meta']['version_date'] == '2018-08-20'
    assert doc['meta']['source'].endswith('/consolide/20180820')


def test_no_consolidation(tmp_path):
    with patch.object(LegiluxClient, 'work_metadata', return_value=WORK), \
            patch.object(LegiluxClient, 'consolidation_dates', return_value=[]):
        with pytest.raises(FileLoadError):
            tulit.fetch(ACT, jurisdiction='LU', version='consolidated', download_dir=str(tmp_path))


def test_download_version_builds_filestore_url(tmp_path):
    response = Mock(status_code=200, content=b'<?xml version="1.0"?><akomaNtoso/>')
    with patch('tulit.client.state.legilux.requests.get', return_value=response) as get:
        LegiluxClient(str(tmp_path)).download_version(ACT, consolidated='2018-08-20')
    assert get.call_args.args[0] == (
        'https://data.legilux.public.lu/filestore/eli/etat/leg/loi/2016/07/23/n21/consolide/20180820/fr/xml/'
        'eli-etat-leg-loi-2016-07-23-n21-consolide-20180820-fr-xml.xml')


def test_consolidation_dates_from_sparql(tmp_path):
    prefix = f'http://data.legilux.public.lu/eli/{ACT}/consolide/'
    rows = [{'s': {'value': prefix + '20180820'}}, {'s': {'value': prefix + '20180820/fr/xml'}},
            {'s': {'value': prefix + '20160101'}}]
    with patch.object(LegiluxClient, '_sparql', return_value=rows):
        assert LegiluxClient(str(tmp_path)).consolidation_dates(ACT) == ['2016-01-01', '2018-08-20']
