"""
Germany, original version: the Federal Law Gazette (Bundesgesetzblatt) as promulgated,
from recht.bund.de (2023-) and the bgbl.de archive (1949-2022), parsed from PDF.
"""
import json
import shutil
from unittest.mock import MagicMock, patch

import pytest

import tulit
from tulit.client.state.germany import GermanyClient
from tulit.client.state.germany_bgbl import BundesgesetzblattClient, archive_name, german_date
from tulit.parser.exceptions import FileLoadError, UnsupportedError
from tulit.parser.pdf.germany import amendment_action, join_lines, quotations
from tulit.sources.de import citation, gazette_reference, reference_eli, work_eli


@pytest.fixture
def bgbl(data_root):
    return data_root / 'sources' / 'member_states' / 'germany' / 'bgbl'


@pytest.mark.parametrize('identifier, reference', [
    ('BGBl. 2024 I Nr. 149', {'part': '1', 'year': '2024', 'number': '149'}),
    ('BGBl. I 2024 Nr. 149', {'part': '1', 'year': '2024', 'number': '149'}),
    ('BGBl 2024 I Nr 149', {'part': '1', 'year': '2024', 'number': '149'}),
    ('BGBl. 2025 II Nr. 12a', {'part': '2', 'year': '2025', 'number': '12a'}),
    ('BGBl. 2017 I S. 2097', {'part': '1', 'year': '2017', 'page': '2097'}),
    ('BGBl. I 2017, S. 2097', {'part': '1', 'year': '2017', 'page': '2097'}),
    ('BGBl. I S. 2097 (2017)', {'part': '1', 'year': '2017', 'page': '2097'}),
    ('BGBl. 1951 II S. 151b', {'part': '2', 'year': '1951', 'page': '151b'}),
    ('eli/bund/bgbl-1/2017/s2097', {'part': '1', 'year': '2017', 'page': '2097'}),
    ('https://www.recht.bund.de/eli/bund/BGBl_1/2023/1', {'part': '1', 'year': '2023', 'number': '1'}),
    ('https://www.recht.bund.de/bgbl/1/2024/149/VO.html', {'part': '1', 'year': '2024', 'number': '149'}),
    ('https://www.bgbl.de/xaver/bgbl/start.xav?startbk=Bundesanzeiger_BGBl&jumpTo=bgbl117s2097.pdf',
     {'part': '1', 'year': '2017', 'page': '2097'}),
])
def test_gazette_reference(identifier, reference):
    assert gazette_reference(identifier) == reference


def test_gazette_reference_needs_the_year():
    with pytest.raises(UnsupportedError, match='gives no year'):
        gazette_reference('BGBl. I S. 2097')
    assert gazette_reference('10001597') is None


def test_citation_and_eli():
    new, old = {'part': '1', 'year': '2024', 'number': '149'}, {'part': '2', 'year': '1951', 'page': '103'}
    assert (citation(new), citation(old)) == ('BGBl. 2024 I Nr. 149', 'BGBl. 1951 II S. 103')
    assert (reference_eli(new), reference_eli(old)) == ('eli/bund/bgbl-1/2024/149', 'eli/bund/bgbl-2/1951/s103')
    # A citation, or the old spelling of an ELI, names the work in the portal too
    assert work_eli('BGBl. 2017 I S. 2097') == 'eli/bund/bgbl-1/2017/s2097'
    assert work_eli('https://www.recht.bund.de/eli/bund/BGBl_1/2023/1') == 'eli/bund/bgbl-1/2023/1'


def test_archive_name_and_dates():
    assert archive_name('1', '2017', '2097') == 'bgbl117s2097.pdf'
    assert german_date('Nr. 44 vom 05.07.2017') == '2017-07-05'
    assert german_date('31.02.2017') is None


@pytest.mark.parametrize('instruction, action', [
    ('1. In § 2 wird das Wort „Telemedien“ durch das Wort „digitale Dienste“ ersetzt.', 'replace'),
    ('2. § 35 wird wie folgt geändert: a) In Satz 3 wird das Wort „x“ gestrichen.', 'amend'),
    ('2. § 74 Absatz 1 Nummer 13 wird gestrichen.', 'delete'),
    ('Artikel 2 des Dritten Gesetzes zur Änderung des Telemediengesetzes wird aufgehoben.', 'delete'),
    ('3. Nach § 5 wird folgender § 5a eingefügt: „§ 5a Prüfung ersetzt“', 'insert'),
    ('4. Dem § 3 wird folgender Absatz 4 angefügt: „(4) ...“', 'add'),
    ('5. § 7 wird wie folgt gefasst: „§ 7 ...“', 'replace'),
    ('Anlage 2 der Verordnung erhält die aus dem Anhang ersichtliche Fassung.', 'replace'),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


def test_quotations_and_join_lines():
    assert quotations('das Wort „a „b“ c“ durch das Wort „d“ ersetzt') == ['a „b“ c', 'd']
    assert join_lines(['des Bundesra-', 'tes']) == 'des Bundesrates'
    assert join_lines(['„Telekommunikation-Telemedien-', 'Datenschutz-Gesetzes“']) == \
        '„Telekommunikation-Telemedien-Datenschutz-Gesetzes“'
    assert join_lines(['Datenschutz-Anpassungs-', 'und -Umsetzungsgesetz']) == \
        'Datenschutz-Anpassungs- und -Umsetzungsgesetz'


class TestParser:
    @pytest.fixture(autouse=True)
    def _pdf(self):
        pytest.importorskip('pdfplumber')

    def parse(self, path, **options):
        from tulit.parser.pdf.germany import BundesgesetzblattParser
        return BundesgesetzblattParser(**options).parse(str(path)).to_dict()

    def test_electronic_omnibus_act(self, bgbl):
        # BGBl. 2024 I Nr. 149, pages 1 and 34-35: Artikel 1 enacts the DDG, Artikel 32-36 amend, 37 enters into force
        doc = self.parse(bgbl / 'bgbl1_2024_149_p1_p34-35.pdf')
        assert doc['preface'].startswith('Gesetz zur Durchführung der Verordnung (EU) 2022/2065')
        assert doc['preface'].endswith('und zur Änderung weiterer Gesetze')
        assert doc['preamble']['formula'] == 'Der Bundestag hat das folgende Gesetz beschlossen:'
        assert [(c['eId'], c['num'], c['heading'], c['parent']) for c in doc['chapters']] == [
            ('prt_1', 'Artikel 1', 'Digitale-Dienste-Gesetz (DDG)', None),
            ('prt_1_2', 'Teil 1', 'Allgemeine Vorschriften', 'prt_1')]
        articles = {a['num']: a for a in doc['articles']}
        assert list(articles) == ['§ 1'] + [f'Artikel {n}' for n in range(32, 38)]
        first = articles['§ 1']
        assert (first['heading'], first['parent']) == ('Anwendungsbereich, Begriffsbestimmungen', 'prt_1_2')
        # The footnote of 'Artikel 1*' is left out
        assert not any('dienen der Umsetzung' in c['text'] for a in doc['articles'] for c in a['children'])

        amending = articles['Artikel 35']
        assert (amending['heading'], amending['parent']) == ('Änderung des Telekommunikationsgesetzes', None)
        intro, *instructions = amending['children']
        assert intro['amendment'] is None and intro['text'].endswith('wird wie folgt geändert:')
        assert [c['eId'] for c in instructions] == ['par_1', 'par_2', 'par_3', 'par_4']
        amendment = instructions[0]['amendment']
        assert amendment['action'] == 'replace'
        assert amendment['amended_act'] == 'BGBl. I S. 1858'
        assert [q['text'] for q in amendment['quoted']] == [
            'Telemedien', 'digitaler Dienste nach § 1 Absatz 4 Nummer 1 des Digitale-Dienste-Gesetzes']
        assert instructions[2]['amendment']['action'] == 'amend'
        repeal = articles['Artikel 36']['children'][0]['amendment']
        assert (repeal['action'], repeal['amended_act']) == ('delete', 'BGBl. I S. 3530')
        assert [c['eId'] for c in articles['Artikel 37']['children']] == ['par_1', 'par_2']
        assert all(c['amendment'] is None for c in articles['Artikel 37']['children'])

        conclusions = doc['conclusions']
        assert conclusions['conclusion_text'].endswith('Berlin, den 6. Mai 2024')
        assert conclusions['signature'].startswith('Der Bundespräsident, Steinmeier, Der Bundeskanzler, Olaf Scholz')

    def test_electronic_amending_regulation(self, bgbl):
        # BGBl. 2026 I Nr. 300, pages 1-4: a Verordnung of two Artikel
        doc = self.parse(bgbl / 'bgbl1_2026_300_p1-4.pdf')
        assert doc['preface'] == 'Dreiundzwanzigste Verordnung zur Änderung der Außenwirtschaftsverordnung'
        assert doc['preamble']['formula'].startswith('Die Bundesregierung verordnet aufgrund')
        assert doc['chapters'] == []
        first, second = doc['articles']
        assert [c['amendment']['action'] for c in first['children'][1:]] == [
            'replace', 'delete', 'replace', 'amend', 'replace']
        # Headings quoted by an instruction ('„§ 76a') stay in it
        assert '§ 76a Ausnahmen von § 74 Absatz 1' in first['children'][3]['text']
        assert (second['num'], second['heading']) == ('Artikel 2', 'Inkrafttreten')
        assert doc['conclusions']['signature'] == ('Der Bundeskanzler, Merz, '
                                                   'Die Bundesministerin für Wirtschaft und Energie, Katherina Reiche')

    def test_printed_issue_in_two_columns(self, bgbl):
        # BGBl. 2017 I S. 2097, pages 1-4: two columns, a table of contents before the BDSG in Artikel 1
        title = ('Gesetz zur Anpassung des Datenschutzrechts an die Verordnung (EU) 2016/679 und zur Umsetzung '
                 'der Richtlinie (EU) 2016/680 (Datenschutz-Anpassungs- und -Umsetzungsgesetz EU – DSAnpUG-EU)')
        doc = self.parse(bgbl / 'bgbl117s2097_p1-4.pdf', title=title)
        assert doc['preface'] == title
        assert doc['preamble']['formula'] == ('Der Bundestag hat mit Zustimmung des Bundesrates das folgende '
                                              'Gesetz beschlossen:')
        assert [(c['num'], c['heading']) for c in doc['chapters']][:4] == [
            ('Artikel 1', 'Bundesdatenschutzgesetz (BDSG)'), ('Teil 1', 'Gemeinsame Bestimmungen'),
            ('Kapitel 1', 'Anwendungsbereich und Begriffsbestimmungen'),
            ('Kapitel 2', 'Rechtsgrundlagen der Verarbeitung personenbezogener Daten')]
        assert [a['num'] for a in doc['articles']] == ['§ 1', '§ 2', '§ 3', '§ 4', '§ 5', '§ 6']
        third = doc['articles'][2]
        assert third['heading'] == 'Verarbeitung personenbezogener Daten durch öffentliche Stellen'
        assert third['children'][0]['text'].startswith('Die Verarbeitung personenbezogener Daten durch eine '
                                                       'öffentliche Stelle ist zulässig')
        # Neither the table of contents nor the running headers are read as text
        texts = ' '.join(c['text'] for a in doc['articles'] for c in a['children'])
        assert 'Inhaltsübersicht' not in texts and 'Jahrgang 2017' not in texts

    def test_printed_issue_title_across_columns(self, bgbl):
        # BGBl. 2009 I S. 2702, pages 1-2 and 10-11: the title runs across both columns
        doc = self.parse(bgbl / 'bgbl109s2702_p1-2_p10-11.pdf', title='Begleitgesetz zur zweiten Föderalismusreform')
        assert doc['preface'] == 'Begleitgesetz zur zweiten Föderalismusreform'
        assert doc['chapters'][0]['heading'] == ('Gesetz zur Errichtung eines Stabilitätsrates und zur Vermeidung '
                                                 'von Haushaltsnotlagen (Stabilitätsratsgesetz – StabiRatG)')
        nums = [a['num'] for a in doc['articles']]
        assert nums[:2] == ['§ 1', '§ 2'] and nums[-2:] == ['Artikel 12', 'Artikel 13']
        assert doc['articles'][0]['children'][0]['text'].startswith('(1) Bund und Länder bilden einen Stabilitätsrat')
        assert all(c['amendment'] for c in doc['articles'][-2]['children'][1:])
        assert doc['conclusions']['conclusion_text'].endswith('Berlin, den 10. August 2009')


class TestClient:
    def test_promulgation(self, bgbl, tmp_path):
        client = BundesgesetzblattClient(download_dir=str(tmp_path))
        page = (bgbl / 'recht_bund_bgbl-1_2024_149.html').read_text(encoding='utf-8')
        with patch.object(client.session, 'get', return_value=MagicMock(status_code=200, text=page)) as get:
            found = client.promulgation('1', '2024', '149')
        assert get.call_args.args[0] == 'https://www.recht.bund.de/eli/bund/bgbl-1/2024/149'
        assert found['title'].startswith('Gesetz zur Durchführung der Verordnung (EU) 2022/2065')
        assert (found['citation'], found['type']) == ('BGBl. 2024 I Nr. 149', 'Gesetz')
        assert (found['date_document'], found['date_publication']) == ('2024-05-06', '2024-05-13')
        assert found['pdf_urls'] == [
            'https://www.recht.bund.de/bgbl/1/2024/149/regelungstext.pdf?__blob=publicationFile']

    def test_promulgation_annexes_follow_the_text(self, tmp_path):
        client = BundesgesetzblattClient(download_dir=str(tmp_path))
        page = ''.join(f'<a href="https://www.recht.bund.de/bgbl/2/2025/7/{name}.pdf?__blob=publicationFile&v=1">'
                       for name in ('anlage2', 'regelungstext', 'anlage1'))
        with patch.object(client.session, 'get', return_value=MagicMock(status_code=200, text=page)):
            found = client.promulgation('2', '2025', '7')
        assert [url.split('?')[0].rsplit('/', 1)[1] for url in found['pdf_urls']] == [
            'regelungstext.pdf', 'anlage1.pdf', 'anlage2.pdf']
        pdf = MagicMock(status_code=200, content=b'%PDF-1.7 test')
        with patch.object(client.session, 'get', return_value=pdf) as get:
            paths = client.download_promulgation(found, '2', '2025', '7')
            assert client.download_promulgation(found, '2', '2025', '7') == paths  # saved once
        assert get.call_count == 3
        assert paths[0].endswith('bgbl2_2025_7_regelungstext.pdf')

    def test_promulgation_not_found(self, tmp_path):
        client = BundesgesetzblattClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'get', return_value=MagicMock(status_code=404, text='')):
            with pytest.raises(FileLoadError, match='no promulgation BGBl. 2024 I Nr. 99999'):
                client.promulgation('1', '2024', '99999')

    def test_archive_document(self, bgbl, tmp_path):
        client = BundesgesetzblattClient(download_dir=str(tmp_path))
        session = MagicMock(**{'json.return_value': {'sid': 'S1', 'csrftoken': 'C1'}})
        text = MagicMock(**{'json.return_value': json.loads(
            (bgbl / 'bgbl_de_text_bgbl117s2097.json').read_text(encoding='utf-8'))})
        pdf = MagicMock(status_code=200, content=b'%PDF-1.6 test')
        with patch.object(client.session, 'get', side_effect=[MagicMock(), session, text, pdf]) as get:
            document = client.archive_document('bgbl117s2097.pdf')
            path = client.download_archive(document)
        assert document['path'] == 'bgbl/Bundesgesetzblatt Teil I/2017/Nr. 44 vom 05.07.2017/bgbl117s2097.pdf'
        assert document['title'].startswith('Gesetz zur Anpassung des Datenschutzrechts')
        assert (document['issue'], document['date_publication']) == ('Nr. 44 vom 05.07.2017', '2017-07-05')
        assert get.call_args_list[2].kwargs['params']['start'] == "//*[@attr_id='bgbl117s2097.pdf']"
        media = get.call_args_list[3].args[0]
        assert media.startswith('https://www.bgbl.de/xaver/bgbl/media.xav/bgbl_Bundesgesetzblatt%20Teil%20I_')
        assert 'SID=S1' in media and '_csrf=C1' in media
        assert path.endswith('bgbl117s2097.pdf')

    def test_archive_document_missing(self, tmp_path):
        client = BundesgesetzblattClient(download_dir=str(tmp_path))
        client._archive = {'sid': 'S1', 'csrf': 'C1'}
        empty = MagicMock(**{'json.return_value': {'innerhtml': '<div id="txtcontent"></div>', 'topub': []}})
        with patch.object(client.session, 'get', return_value=empty):
            assert client.archive_document('bgbl109s2704.pdf') is None


PROMULGATION = {
    'url': 'https://www.recht.bund.de/eli/bund/bgbl-1/2024/149', 'title': 'Gesetz zur Durchführung ...',
    'citation': 'BGBl. 2024 I Nr. 149', 'type': 'Gesetz', 'date_publication': '2024-05-13',
    'date_document': '2024-05-06',
    'pdf_urls': ['https://www.recht.bund.de/bgbl/1/2024/149/regelungstext.pdf?__blob=publicationFile'],
}
DOCUMENT = {'path': 'bgbl/Bundesgesetzblatt Teil I/2009/Nr. 53 vom 17.08.2009/bgbl109s2702.pdf',
            'title': 'Begleitgesetz zur zweiten Föderalismusreform', 'issue': 'Nr. 53 vom 17.08.2009',
            'date_publication': '2009-08-17'}


class TestSource:
    @pytest.fixture(autouse=True)
    def _pdf(self):
        pytest.importorskip('pdfplumber')

    def copy(self, bgbl, tmp_path, name):
        target = tmp_path / name
        shutil.copy(bgbl / name, target)
        return str(target)

    def test_fetch_promulgation(self, bgbl, tmp_path):
        path = self.copy(bgbl, tmp_path, 'bgbl1_2024_149_p1_p34-35.pdf')
        with patch.object(BundesgesetzblattClient, 'promulgation', return_value=PROMULGATION) as found, \
                patch.object(BundesgesetzblattClient, 'download_promulgation', return_value=[path]):
            doc = tulit.fetch('BGBl. 2024 I Nr. 149', jurisdiction='DE', download_dir=str(tmp_path))
        found.assert_called_once_with('1', '2024', '149')
        meta = doc['meta']
        assert (meta['version'], meta['version_date'], meta['date_document']) == (
            'original', '2024-05-13', '2024-05-06')
        assert meta['eli'] == 'https://www.recht.bund.de/eli/bund/bgbl-1/2024/149'
        assert meta['source'].endswith('/bgbl/1/2024/149/regelungstext.pdf?__blob=publicationFile')
        assert meta['gazette'] == 'BGBl. 2024 I Nr. 149'
        assert doc['articles'][-1]['num'] == 'Artikel 37'

    def test_fetch_archive(self, bgbl, tmp_path):
        path = self.copy(bgbl, tmp_path, 'bgbl109s2702_p1-2_p10-11.pdf')
        with patch.object(BundesgesetzblattClient, 'archive_document',
                          side_effect=lambda name: DOCUMENT if name == 'bgbl109s2702.pdf' else None) as found, \
                patch.object(BundesgesetzblattClient, 'download_archive', return_value=path):
            doc = tulit.fetch('eli/bund/bgbl-1/2009/s2702', jurisdiction='DE', version='original',
                              download_dir=str(tmp_path))
        assert found.call_args.args[0] == 'bgbl109s2702.pdf'
        meta = doc['meta']
        assert (meta['version'], meta['version_date'], meta['gazette_issue']) == (
            'original', '2009-08-17', 'Nr. 53 vom 17.08.2009')
        assert meta['source'].endswith('jumpTo=bgbl109s2702.pdf')
        assert doc['preface'] == 'Begleitgesetz zur zweiten Föderalismusreform'

    def test_scanned_issue(self, tmp_path):
        with patch.object(BundesgesetzblattClient, 'archive_document', return_value=DOCUMENT), \
                patch.object(BundesgesetzblattClient, 'download_archive', return_value=str(tmp_path / 'scan.pdf')), \
                patch('tulit.sources.de.has_text', return_value=False):
            with pytest.raises(FileLoadError, match='scanned'):
                tulit.fetch('BGBl. 1976 I S. 1253', jurisdiction='DE', download_dir=str(tmp_path))
            found = tulit.download('BGBl. 1976 I S. 1253', jurisdiction='DE', download_dir=str(tmp_path))
        assert (found['parser'], found['version'], found['meta']['scanned']) == (None, 'original', True)

    def test_archive_lookups(self, tmp_path):
        names = []

        def lookup(name):
            names.append(name)
            return DOCUMENT if name == 'bgbl251s0151a.pdf' else None

        with patch.object(BundesgesetzblattClient, 'archive_document', side_effect=lookup):
            with pytest.raises(UnsupportedError, match='Several acts begin on BGBl. 1951 II S. 151'):
                tulit.fetch('BGBl. 1951 II S. 151', jurisdiction='DE', download_dir=str(tmp_path))
            # Pages are also written with four digits
            assert names[:2] == ['bgbl251s151.pdf', 'bgbl251s0151.pdf']
            with pytest.raises(FileLoadError, match='cite the first page of the act'):
                tulit.fetch('BGBl. 2009 I S. 2704', jurisdiction='DE', download_dir=str(tmp_path))

    @pytest.mark.parametrize('identifier, version, date, message', [
        ('BGBl. 2017 I Nr. 44', None, None, 'cited by page'),
        ('BGBl. 2024 I S. 12', None, None, 'numbers its promulgations'),
        ('BGBl. 2024 I Nr. 149', None, '2024-06-01', 'original version has none'),
        ('eli/bund/banz-at/2022/1117v1', 'original', None, 'Bundesgesetzblatt acts only'),
        ('Datenschutzgesetz', 'original', None, 'not a Federal Law Gazette citation'),
    ])
    def test_unsupported(self, tmp_path, identifier, version, date, message):
        with pytest.raises(UnsupportedError, match=message):
            tulit.fetch(identifier, jurisdiction='DE', version=version, date=date, download_dir=str(tmp_path))

    def test_citation_of_the_consolidated_version(self, tmp_path):
        with patch.object(GermanyClient, 'current_expression', return_value=None) as current:
            with pytest.raises(FileLoadError):
                tulit.fetch('BGBl. 2017 I S. 2097', jurisdiction='DE', version='consolidated',
                            download_dir=str(tmp_path))
        current.assert_called_once_with('eli/bund/bgbl-1/2017/s2097')
