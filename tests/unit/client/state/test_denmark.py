import shutil
from unittest.mock import Mock, patch

import pytest
from lxml import etree

import tulit
from tulit.client.state.denmark import (
    RetsinformationClient, consolidated_act, normalise_eli_path
)
from tulit.parser.exceptions import FileLoadError


@pytest.fixture
def folder(data_root):
    return data_root / 'sources' / 'member_states' / 'denmark' / 'retsinformation'


@pytest.fixture
def client(tmp_path):
    return RetsinformationClient(download_dir=str(tmp_path))


@pytest.mark.parametrize('identifier, path', [
    ('lta/2018/502', 'lta/2018/502'),
    ('eli/lta/2018/502', 'lta/2018/502'),
    ('https://www.retsinformation.dk/eli/lta/2018/502/xml', 'lta/2018/502'),
    ('accn/A20180050230', 'accn/A20180050230'),
])
def test_normalise_eli_path(identifier, path):
    assert normalise_eli_path(identifier) == path


def test_normalise_rejects_other_identifiers():
    with pytest.raises(ValueError):
        normalise_eli_path('LOV nr 502')


def test_consolidated_act(folder):
    root = etree.parse(str(folder / 'lta_2024_289.xml')).getroot()
    assert consolidated_act(root) == ('lta/2018/502', '2018-05-23')
    assert consolidated_act(etree.parse(str(folder / 'lta_2018_502.xml')).getroot()) is None


def test_download_saves_xml(client, tmp_path):
    response = Mock(content=b'<?xml version="1.0"?><Dokument/>')
    client.session = Mock()
    client.session.get.return_value = response
    path = client.download('lta/2018/502')
    assert path.endswith('lta_2018_502.xml')
    assert client.session.get.call_args.args[0] == 'https://www.retsinformation.dk/eli/lta/2018/502/xml'


def test_download_rejects_html(client):
    client.session = Mock()
    client.session.get.return_value = Mock(content=b'<!DOCTYPE html><html></html>')
    with pytest.raises(FileLoadError):
        client.download('lta/2018/502')


def test_find_consolidation_checks_the_introduction(client, folder):
    results = [
        {'retsinfoLink': '/eli/lta/2020/1', 'documentTypeEliCode': 'LBKH', 'isHistoryFlag': True},
        {'retsinfoLink': '/eli/lta/2024/289', 'documentTypeEliCode': 'LBKH', 'isHistoryFlag': False},
    ]
    with patch.object(client, 'search', return_value=results), \
            patch.object(client, 'download', return_value=str(folder / 'lta_2024_289.xml')) as download:
        assert client.find_consolidation('lta/2018/502', 'Databeskyttelsesloven') == 'lta/2024/289'
        assert client.find_consolidation('lta/2019/1', 'Databeskyttelsesloven') is None
    download.assert_called_with('lta/2024/289')


class TestDenmarkSource:
    @pytest.fixture
    def downloads(self, folder, tmp_path):
        def fake_download(self, identifier):
            path = normalise_eli_path(identifier)
            target = tmp_path / (path.replace('/', '_') + '.xml')
            shutil.copy(folder / target.name, target)
            return str(target)
        return fake_download

    def test_identifier_decides_version(self, downloads, tmp_path):
        with patch.object(RetsinformationClient, 'download', downloads):
            act = tulit.fetch('lta/2018/502', jurisdiction='DK', download_dir=str(tmp_path))
            consolidation = tulit.fetch('https://www.retsinformation.dk/eli/lta/2024/289',
                                        download_dir=str(tmp_path))
        assert act['meta']['version'] == 'original'
        assert act['meta']['version_date'] == '2018-05-23'
        assert consolidation['meta']['version'] == 'consolidated'
        assert consolidation['meta']['version_date'] == '2024-03-21'
        assert consolidation['meta']['eli'] == 'https://www.retsinformation.dk/eli/lta/2018/502'
        assert consolidation['meta']['source'] == 'https://www.retsinformation.dk/eli/lta/2024/289'

    def test_original_of_a_consolidation(self, downloads, tmp_path):
        with patch.object(RetsinformationClient, 'download', downloads):
            doc = tulit.fetch('lta/2024/289', jurisdiction='DK', version='original',
                              download_dir=str(tmp_path))
        assert doc['meta']['source'] == 'https://www.retsinformation.dk/eli/lta/2018/502'
        assert doc['preamble']['formula'].startswith('VI MARGRETHE')

    def test_consolidation_of_an_act(self, downloads, tmp_path):
        with patch.object(RetsinformationClient, 'download', downloads), \
                patch.object(RetsinformationClient, 'find_consolidation', return_value='lta/2024/289'):
            doc = tulit.fetch('lta/2018/502', jurisdiction='DK', version='consolidated',
                              download_dir=str(tmp_path))
        assert doc['meta']['source'] == 'https://www.retsinformation.dk/eli/lta/2024/289'

    def test_no_consolidation(self, downloads, tmp_path):
        with patch.object(RetsinformationClient, 'download', downloads), \
                patch.object(RetsinformationClient, 'find_consolidation', return_value=None):
            with pytest.raises(FileLoadError, match='original text is the text in force'):
                tulit.fetch('lta/2018/502', jurisdiction='DK', version='consolidated',
                            download_dir=str(tmp_path))

    def test_date_not_supported(self):
        with pytest.raises(ValueError, match='a date cannot be selected'):
            tulit.fetch('lta/2018/502', jurisdiction='DK', date='2020-01-01')

    def test_older_act_read_from_html(self, tmp_path):
        """The Constitution of 1953: the XML has only metadata, the text comes from the HTML."""
        xml = tmp_path / 'lta_1953_169.xml'
        xml.write_text('<Dokument><Meta><DocumentType>Lov</DocumentType><DiesSigni>1953-06-05</DiesSigni>'
                       '<Status>Valid</Status></Meta></Dokument>', encoding='utf-8')
        page = tmp_path / 'lta_1953_169.html'
        page.write_text(GRUNDLOV, encoding='utf-8')
        with patch.object(RetsinformationClient, 'download', return_value=str(xml)), \
                patch.object(RetsinformationClient, 'download_html', return_value=str(page)) as html:
            doc = tulit.fetch('accn/A19530016930', jurisdiction='DK', download_dir=str(tmp_path))
        html.assert_called_once_with('accn/A19530016930')
        assert doc['preface'] == 'Danmarks Riges Grundlov (Grundloven)'
        assert doc['preamble']['formula'].startswith('Vi Frederik den Niende')
        assert [(c['eId'], c['num'], c['heading']) for c in doc['chapters']] == [
            ('cpt_I', 'Kapitel I', None), ('cpt_1', 'Kapitel 1', 'Lovens almindelige anvendelsesområde')]
        first, second = doc['articles']
        assert (first['num'], first['parent'], second['parent']) == ('§ 1', 'cpt_I', 'cpt_1')
        assert [(c['eId'], c['text']) for c in second['children']] == [
            ('par_1', 'Statens ydelse bestemmes ved lov, hvis 1) kongen er myndig, 2) ...'),
            ('par_2', 'Stk. 2. Statsydelsen kan ikke behæftes med gæld.')]
        assert doc['conclusions']['conclusion_text'] == 'Givet på Christiansborg slot, den 5. juni 1953. Frederik R.'


GRUNDLOV = """<div class="bjelke">Oversigt</div><DIV CLASS=PARA ID="OVERSIGT"><UL><LI>Kapitel I.</LI></UL></DIV>
<DIV CLASS=PARA ID="INDHOLD"><center><H1 CLASS=TITLE ALIGN=CENTER>Danmarks Riges Grundlov (Grundloven) </H1></center>
<P CLASS=SUB-TITLE>&nbsp;&nbsp;Vi Frederik den Niende, af Guds Nåde Konge til Danmark</P>
<A NAME=""K1""></A><DIV CLASS=KAPITEL ID="K1"><center><H3 CLASS=KTITLE1 ALIGN=CENTER>Kapitel I. </H3></center>
<DIV CLASS=PARAGRAPH ID="P1"><P CLASS=PARAB>&nbsp;&nbsp; <B>§ 1. </B> Denne grundlov gælder for alle dele
 af Danmarks Rige. </P></DIV></DIV>
<DIV CLASS=KAPITEL ID="K2"><H3 CLASS=KTITLE1 ALIGN=CENTER>Kapitel 1 </H3>
<P CLASS=KTITLE2 ALIGN=CENTER> <I>Lovens almindelige anvendelsesområde </I></P>
<DIV CLASS=PARAGRAPH ID="P10"><P CLASS=PARAB> <B>§ 10. </B> Stk. 1. Statens ydelse bestemmes ved lov, hvis </P>
<UL CLASS=PLAIN-LIST><LI>1) kongen er myndig,</LI><LI>2) ...</LI></UL>
<P CLASS=STK>&nbsp; <I>Stk. 2. </I> Statsydelsen kan ikke behæftes med gæld. </P></DIV></DIV>
<DIV CLASS=GIVET ID="GIVET"><P CLASS=GIVET-LINE><I>Givet på Christiansborg slot, den 5. juni 1953.</I></P>
<P CLASS=UNDERSKREVET-AF><B>Frederik R.</B></P></DIV></DIV>"""


def test_download_html(client, tmp_path):
    response = Mock(json=Mock(return_value=[{'documentHtml': '<div>Grundloven</div>'}]))
    with patch.object(client.session, 'post', return_value=response) as post:
        path = client.download_html('lta/1953/169')
        assert client.download_html('lta/1953/169') == path  # saved once
    post.assert_called_once()
    assert post.call_args.args[0] == 'https://www.retsinformation.dk/api/document/eli/lta/1953/169'
    with open(path, encoding='utf-8') as f:
        assert f.read() == '<div>Grundloven</div>'
    response.json.return_value = [{'documentHtml': ''}]
    with patch.object(client.session, 'post', return_value=response):
        with pytest.raises(FileLoadError):
            client.download_html('lta/1985/571')
