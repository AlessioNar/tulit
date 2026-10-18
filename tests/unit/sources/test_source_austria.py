from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.austria import AustriaRISClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.xml.bgbl_at import BGBlParser, amendment_action
from tulit.sources.at import gazette_reference


@pytest.fixture
def bgbl(data_root):
    return data_root / 'sources' / 'member_states' / 'austria' / 'bgbl'


@pytest.mark.parametrize('identifier', [
    'BGBl. I Nr. 5/2024', 'BGBl I Nr 5/2024', 'I 5/2024', 'BGBLA_2024_I_5',
    'https://www.ris.bka.gv.at/eli/bgbl/i/2024/5/20240226',
])
def test_gazette_reference(identifier):
    assert gazette_reference(identifier) == ('I', '2024', '5')


def test_gazette_reference_rejects_law_numbers():
    assert gazette_reference('10001597') is None


@pytest.mark.parametrize('instruction, action', [
    ('1. Art. 15 Abs. 7 lautet:', 'replace'),
    ('2. Art. 20 Abs. 3 bis 5 entfällt.', 'delete'),
    ('3. Nach Art. 22 wird folgender Art. 22a eingefügt:', 'insert'),
    ('4. Art. 30 wird folgender Abs. 7 angefügt:', 'add'),
    ('8. In Art. 131 wird der Ausdruck „14a“ durch den Ausdruck „14b“ ersetzt.', 'replace'),
    ('30. In § 70 erhalten die Abs. 1 und 2 die Absatzbezeichnungen „(7)“ und „(8)“.', 'renumber'),
    ('31. Die Abs. 2 bis 7 des § 60 werden nach § 70 eingereiht.', 'renumber'),
    ('32. § 5 wird wie folgt geändert:', 'amend'),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestBGBlParser:
    def test_omnibus_law(self, bgbl):
        """Artikel 1 amends the constitution, Artikel 2 enacts the Informationsfreiheitsgesetz."""
        parser = BGBlParser().parse(str(bgbl / 'BGBLA_2024_I_5.xml'))
        assert parser.preface.startswith('Bundesgesetz, mit dem das Bundes-Verfassungsgesetz geändert')
        assert parser.formula == 'Der Nationalrat hat beschlossen:'
        assert parser.conclusions['signature'] == 'Van der Bellen, Nehammer'

        amending = parser.articles[0]
        assert (amending['eId'], amending['num']) == ('art_1', 'Artikel 1')
        assert amending['heading'] == '(Verfassungsbestimmung) Änderung des Bundes-Verfassungsgesetzes'
        intro, first, second = amending['children'][:3]
        assert intro['text'].startswith('Das Bundes-Verfassungsgesetz – B-VG, BGBl. Nr. 1/1930')
        assert first['eId'] == 'par_1'
        assert first['amendment']['action'] == 'replace'
        assert first['amendment']['amended_act'] == 'BGBl. Nr. 1/1930'
        assert first['amendment']['quoted'][0]['text'].startswith('(7) Im Rahmen des Rechtsinformationssystems')
        assert second['amendment']['action'] == 'delete'

        part = parser.chapters[0]
        assert (part['eId'], part['type'], part['num']) == ('prt_2', 'part', 'Artikel 2')
        assert part['heading'] == 'Bundesgesetz über den Zugang zu Informationen (Informationsfreiheitsgesetz – IFG)'
        sections = [c for c in parser.chapters if c['type'] == 'section']
        assert len(sections) == 6 and {c['parent'] for c in sections} == {'prt_2'}

        paragraph = next(a for a in parser.articles if a['num'] == '§ 2')
        assert (paragraph['heading'], paragraph['parent']) == ('Begriffsbestimmungen', 'sct_1')
        assert [c['eId'] for c in paragraph['children']] == ['par_1', 'par_2']
        assert paragraph['children'][0]['text'].startswith('(1) Information im Sinne')
        assert sum(1 for a in parser.articles if a['num'] and a['num'].startswith('§')) == 20

    def test_amending_law_without_artikel(self, bgbl):
        parser = BGBlParser().parse(str(bgbl / 'BGBLA_2018_I_24.xml'))
        assert len(parser.articles) == 1
        children = parser.articles[0]['children']
        assert children[0]['amendment'] is None
        assert all(c['amendment']['amended_act'] == 'BGBl. I Nr. 165/1999' for c in children[1:])

    def test_agreement_with_art_headings(self, tmp_path):
        """A 15a agreement (BGBl. I Nr. 1/2025): table of contents, preamble, 'art' headings, line breaks."""
        issue = tmp_path / 'BGBLA_2025_I_1.xml'
        issue.write_text(
            '<risdok xmlns="http://www.bka.gv.at"><nutzdaten><abschnitt>'
            '<ueberschrift typ="titel">1. Vereinbarung gemäß Art. 15a B-VG</ueberschrift>'
            '<absatz typ="promkleinlsatz">Der Nationalrat hat beschlossen:</absatz>'
            '<absatz typ="promkleinlsatz">Der Abschluss der Vereinbarung wird genehmigt.</absatz>'
            '<table title="Inhaltsverzeichnis"><tr><td><inhaltsvz typ="spalte">Art. 1</inhaltsvz></td></tr></table>'
            '<ueberschrift typ="g1">PRÄAMBEL</ueberschrift>'
            '<absatz typ="erltext">Im Interesse der Menschen.</absatz>'
            '<ueberschrift typ="g1min">1. Abschnitt<br />Allgemeine Bestimmungen</ueberschrift>'
            '<ueberschrift typ="art">Art. 1<br />Gegenstand</ueberschrift>'
            '<absatz typ="abs">(1) Erster Absatz.</absatz><absatz typ="abs">(2) Zweiter Absatz.</absatz>'
            '<ueberschrift typ="art">Art. 2<br />Geltungsbereich</ueberschrift>'
            '<absatz typ="abs">Text.</absatz>'
            '<ueberschrift typ="anlage">Anlage</ueberschrift>'
            '<ueberschrift typ="erll">DSFA-A01 Kundenverwaltung</ueberschrift><absatz typ="abs">Zweck.</absatz>'
            '</abschnitt></nutzdaten></risdok>', encoding='utf-8')
        parser = BGBlParser().parse(str(issue))
        assert parser.formula == 'Der Nationalrat hat beschlossen: Der Abschluss der Vereinbarung wird genehmigt.'
        assert parser.recitals == [{'eId': 'rct_1', 'text': 'Im Interesse der Menschen.'}]
        assert [(c['eId'], c['num'], c['heading']) for c in parser.chapters] == [
            ('sct_1', '1. Abschnitt', 'Allgemeine Bestimmungen')]
        assert [(a['eId'], a['num'], a['heading'], a['parent']) for a in parser.articles] == [
            ('art_1', 'Art. 1', 'Gegenstand', 'sct_1'), ('art_2', 'Art. 2', 'Geltungsbereich', 'sct_1')]
        assert [c['eId'] for c in parser.articles[0]['children']] == ['par_1', 'par_2']
        annex = parser.annexes[0]
        assert (annex['num'], annex['heading']) == ('Anlage', None)
        assert [c['text'] for c in annex['children']] == ['DSFA-A01 Kundenverwaltung', 'Zweck.']

    def test_amending_agreement_quotes_headings(self, tmp_path):
        """BGBl. I Nr. 1/2026: quoted 'art' and 'anlage' headings belong to the amendments."""
        issue = tmp_path / 'BGBLA_2026_I_1.xml'
        issue.write_text(
            '<risdok xmlns="http://www.bka.gv.at"><nutzdaten><abschnitt>'
            '<ueberschrift typ="titel">Vereinbarung gemäß Art. 15a B-VG</ueberschrift>'
            '<absatz typ="promkleinlsatz">Der Nationalrat hat beschlossen:</absatz>'
            '<absatz typ="promkleinlsatz">Die Vereinbarung wird wie folgt geändert:</absatz>'
            '<absatz typ="novao1">1. Die Überschrift des Art. II lautet:</absatz>'
            '<ueberschrift typ="art">„Nationalparkflächen“</ueberschrift>'
            '<absatz typ="novao1">2. Die Anlage 1 lautet:</absatz>'
            '<ueberschrift typ="anlage">„Anlage 1</ueberschrift><absatz typ="abs">Karte.“</absatz>'
            '</abschnitt></nutzdaten></risdok>', encoding='utf-8')
        parser = BGBlParser().parse(str(issue))
        assert len(parser.articles) == 1 and parser.annexes == []
        children = parser.articles[0]['children']
        assert [c['amendment']['action'] for c in children[1:]] == ['replace', 'replace']
        assert children[1]['amendment']['quoted'] == [{'kind': 'text', 'text': 'Nationalparkflächen'}]

    def test_unreadable_file(self, tmp_path):
        broken = tmp_path / 'broken.xml'
        broken.write_text('<risdok')
        with pytest.raises(FileLoadError):
            BGBlParser().parse(str(broken))


class TestAustriaOriginals:
    def test_fetch_by_gazette_reference(self, bgbl, tmp_path):
        with patch.object(AustriaRISClient, 'download_gazette',
                          return_value=str(bgbl / 'BGBLA_2024_I_5.xml')) as download:
            doc = tulit.fetch('BGBl. I Nr. 5/2024', jurisdiction='AT', download_dir=str(tmp_path))
        download.assert_called_once_with('I', '2024', '5')
        meta = doc['meta']
        assert (meta['version'], meta['version_date'], meta['date_document']) == (
            'original', '2024-02-26', '2024-02-26')
        assert meta['eli'] == 'https://www.ris.bka.gv.at/eli/bgbl/i/2024/5'

    def test_eli_selects_austria(self, bgbl, tmp_path):
        with patch.object(AustriaRISClient, 'download_gazette',
                          return_value=str(bgbl / 'BGBLA_2018_I_24.xml')) as download:
            doc = tulit.fetch('https://www.ris.bka.gv.at/eli/bgbl/i/2018/24/20180515', download_dir=str(tmp_path))
        download.assert_called_once_with('I', '2018', '24')
        assert doc['meta']['jurisdiction'] == 'AT'

    def test_original_of_a_law_number(self, bgbl, tmp_path):
        with patch.object(AustriaRISClient, 'gazette_reference', return_value=('I', '2024', '5')), \
                patch.object(AustriaRISClient, 'download_gazette',
                             return_value=str(bgbl / 'BGBLA_2024_I_5.xml')) as download:
            tulit.fetch('20012345', jurisdiction='AT', version='original', download_dir=str(tmp_path))
        download.assert_called_once_with('I', '2024', '5')

    def test_invalid_requests(self, tmp_path):
        with pytest.raises(ValueError, match='Gesetzesnummer'):
            tulit.fetch('BGBl. I Nr. 5/2024', jurisdiction='AT', version='consolidated', download_dir=str(tmp_path))
        with pytest.raises(ValueError, match='original version has none'):
            tulit.fetch('BGBl. I Nr. 5/2024', jurisdiction='AT', date='2024-03-01', download_dir=str(tmp_path))
        with pytest.raises(ValueError, match='not a RIS Gesetzesnummer'):
            tulit.fetch('DSG', jurisdiction='AT', download_dir=str(tmp_path))


class TestGazetteClient:
    def test_before_2004(self, tmp_path):
        with pytest.raises(FileLoadError, match='predates'):
            AustriaRISClient(download_dir=str(tmp_path)).download_gazette('I', '1999', '165')

    def test_download(self, tmp_path):
        client = AustriaRISClient(download_dir=str(tmp_path))
        response = Mock(status_code=200, content=b'<?xml version="1.0"?><risdok/>')
        with patch.object(client.session, 'get', return_value=response) as get:
            path = client.download_gazette('I', '2024', '5')
        assert get.call_args.args[0].endswith('/BGBLA_2024_I_5/BGBLA_2024_I_5.xml')
        assert path.endswith('BGBLA_2024_I_5.xml')

    def test_missing_issue(self, tmp_path):
        client = AustriaRISClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'get', return_value=Mock(status_code=404, content=b'')):
            with pytest.raises(FileLoadError):
                client.download_gazette('I', '2024', '999')

    def test_gazette_reference(self, tmp_path):
        client = AustriaRISClient(download_dir=str(tmp_path))
        reference = {'Data': {'Metadaten': {'Bundesrecht': {'BrKons': {
            'StammnormPublikationsorgan': 'BGBl. I Nr.', 'StammnormBgblnummer': '165/1999'}}}}}
        with patch.object(client, 'search', return_value=[reference]):
            assert client.gazette_reference('10001597') == ('I', '1999', '165')
        with patch.object(client, 'search', return_value=[]):
            assert client.gazette_reference('10001597') is None
