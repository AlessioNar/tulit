import shutil
from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.netherlands import BWBClient
from tulit.parser.exceptions import FileLoadError

SRU_RESPONSE = b'''<?xml version="1.0" encoding="UTF-8"?>
<searchRetrieveResponse xmlns="http://docs.oasis-open.org/ns/search-ws/sruResponse">
  <numberOfRecords>1</numberOfRecords>
  <records><record><recordData>
    <gzd xmlns="http://standaarden.overheid.nl/sru" xmlns:dcterms="http://purl.org/dc/terms/"
         xmlns:overheidbwb="http://standaarden.overheid.nl/bwb/terms/">
      <originalData><overheidbwb:meta><owmskern>
        <dcterms:identifier>BWBR0040940</dcterms:identifier>
        <dcterms:title>Uitvoeringswet Algemene verordening gegevensbescherming</dcterms:title>
      </owmskern><bwbipm>
        <overheidbwb:toestand>http://wetten.overheid.nl/id/BWBR0040940/2026-09-01/0</overheidbwb:toestand>
        <overheidbwb:geldigheidsperiode_startdatum>2026-09-01</overheidbwb:geldigheidsperiode_startdatum>
        <overheidbwb:locatie_toestand>https://repository.example/BWBR0040940_2026-09-01_0.xml</overheidbwb:locatie_toestand>
      </bwbipm></overheidbwb:meta></originalData>
    </gzd>
  </recordData></record></records>
</searchRetrieveResponse>'''


@pytest.fixture
def client(tmp_path):
    client = BWBClient(download_dir=str(tmp_path))
    client.session = Mock()
    return client


def test_search_sends_identifier_and_date(client):
    client.session.get.return_value = Mock(content=SRU_RESPONSE)
    record = client.search('BWBR0040940', '2026-10-17')
    assert record['locatie_toestand'] == 'https://repository.example/BWBR0040940_2026-09-01_0.xml'
    assert record['geldigheidsperiode_startdatum'] == '2026-09-01'
    query = client.session.get.call_args.kwargs['params']['query']
    assert query == 'dcterms.identifier==BWBR0040940 and overheidbwb.geldigheidsdatum==2026-10-17'


def test_session_asks_for_xml(tmp_path):
    assert BWBClient(download_dir=str(tmp_path)).session.headers['Accept'] == 'application/xml'


def test_invalid_identifier(client):
    with pytest.raises(ValueError):
        client.search('Wetboek van Strafrecht', '2026-10-17')


def test_download(client, tmp_path):
    client.session.get.side_effect = [Mock(content=SRU_RESPONSE), Mock(content=b'<toestand/>')]
    path, record = client.download('BWBR0040940', '2026-10-17')
    assert path.endswith('BWBR0040940_2026-09-01_0.xml')
    assert open(path, 'rb').read() == b'<toestand/>'


def test_download_without_version(client):
    client.session.get.return_value = Mock(content=SRU_RESPONSE.replace(b'BWBR0040940', b'BWBR0000001'))
    with pytest.raises(FileLoadError):
        client.download('BWBR0040940', '1900-01-01')


def test_fetch_netherlands(data_root, tmp_path):
    fixture = data_root / 'sources' / 'member_states' / 'netherlands' / 'bwb' / 'BWBR0040940.xml'
    target = tmp_path / 'BWBR0040940.xml'
    shutil.copy(fixture, target)
    record = {'toestand': 'http://wetten.overheid.nl/id/BWBR0040940/2026-09-01/0',
              'geldigheidsperiode_startdatum': '2026-09-01'}
    with patch.object(BWBClient, 'download', return_value=(str(target), record)) as download:
        doc = tulit.fetch('https://wetten.overheid.nl/BWBR0040940/2026-09-01', date='2026-10-17',
                          download_dir=str(tmp_path))
    download.assert_called_once_with('BWBR0040940', '2026-10-17')
    assert doc['meta']['jurisdiction'] == 'NL'
    assert doc['meta']['version'] == 'consolidated'
    assert doc['meta']['version_date'] == '2026-09-01'
    assert doc['meta']['source'] == record['toestand']
