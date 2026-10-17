import json
from unittest.mock import Mock

import pytest

from tulit.client.state.austria import AustriaRISClient, law_eli
from tulit.parser.exceptions import FileLoadError


def _reference(document_id, unit, kind='Paragraph'):
    return {'Data': {
        'Metadaten': {
            'Technisch': {'ID': document_id},
            'Bundesrecht': {'Kurztitel': 'Datenschutzgesetz', 'Titel': 'Bundesgesetz ...',
                            'Eli': f'https://ris.bka.gv.at/eli/{document_id}',
                            'BrKons': {'ArtikelParagraphAnlage': unit, 'Dokumenttyp': kind,
                                       'StammnormPublikationsorgan': 'BGBl. I Nr.',
                                       'StammnormBgblnummer': '165/1999',
                                       'Inkrafttretensdatum': '2018-05-25'}}},
        'Dokumentliste': {'ContentReference': {
            'ContentType': 'MainDocument',
            'Urls': {'ContentUrl': [
                {'DataType': 'Html', 'Url': f'https://ris/{document_id}.html'},
                {'DataType': 'Xml', 'Url': f'https://ris/{document_id}.xml'}]}}}}}


def _search_response(references, total):
    response = Mock()
    response.json.return_value = {'OgdSearchResult': {'OgdDocumentResults': {
        'Hits': {'#text': str(total)}, 'OgdDocumentReference': references}}}
    return response


def _file_response(content=b'<risdok/>'):
    response = Mock()
    response.content = content
    return response


@pytest.fixture
def client(tmp_path):
    client = AustriaRISClient(download_dir=str(tmp_path))
    client.session = Mock()
    return client


def test_search_follows_pages(client):
    client.session.get.side_effect = [
        _search_response([_reference('NOR1', '§ 0', 'Norm'), _reference('NOR2', '§ 1')], 3),
        _search_response(_reference('NOR3', '§ 2'), 3),
    ]
    references = client.search('10001597', '2026-10-17')

    assert [r['Data']['Metadaten']['Technisch']['ID'] for r in references] == ['NOR1', 'NOR2', 'NOR3']
    first_params = client.session.get.call_args_list[0].kwargs['params']
    assert first_params['Gesetzesnummer'] == '10001597'
    assert first_params['FassungVom'] == '2026-10-17'
    assert client.session.get.call_args_list[1].kwargs['params']['Seitennummer'] == 2


def test_download_writes_units_and_index(client, tmp_path):
    client.session.get.side_effect = [
        _search_response([_reference('NOR1', '§ 0', 'Norm'), _reference('NOR2', 'Art. 2 § 6')], 2),
        _file_response(b'<one/>'),
        _file_response(b'<two/>'),
    ]
    folder = client.download('10001597', '2026-10-17')

    index = json.loads((tmp_path / 'AT' / '10001597' / '2026-10-17' / 'index.json').read_text())
    assert folder.endswith('2026-10-17')
    assert [u['unit'] for u in index['units']] == ['§ 0', 'Art. 2 § 6']
    assert index['units'][1]['file'] == 'NOR2.xml'
    assert (tmp_path / 'AT' / '10001597' / '2026-10-17' / 'NOR2.xml').read_bytes() == b'<two/>'
    assert client.session.get.call_args_list[2].args[0] == 'https://ris/NOR2.xml'


def test_download_unknown_law(client):
    client.session.get.return_value = _search_response([], 0)
    with pytest.raises(FileLoadError):
        client.download('99999999', '2026-10-17')


@pytest.mark.parametrize('gazette, number, eli', [
    ('BGBl. I Nr.', '165/1999', 'https://www.ris.bka.gv.at/eli/bgbl/i/1999/165'),
    ('BGBl. II Nr.', '12/2020', 'https://www.ris.bka.gv.at/eli/bgbl/ii/2020/12'),
    ('JGS Nr.', '946/1811', None),
    ('BGBl. Nr.', '1/1930', None),
    (None, None, None),
])
def test_law_eli(gazette, number, eli):
    assert law_eli(gazette, number) == eli
