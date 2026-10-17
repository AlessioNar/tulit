import json
from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.slovenia import PisrsClient
from tulit.parser.exceptions import FileLoadError
from tulit.parser.html.pisrs import PisrsParser, amendment_action


@pytest.fixture
def slovenia(data_root):
    return data_root / 'sources' / 'member_states' / 'slovenia'


@pytest.fixture
def record(slovenia):
    return json.loads((slovenia / 'URED8455.json').read_text(encoding='utf-8'))['data']


def search_hit(act_id, title, status='Veljaven predpis'):
    return {'zunanjiId': act_id, 'nazivAkta': title, 'semafor': {'naziv': status}}


@pytest.mark.parametrize('instruction, action', [
    ('V 19. členu se četrti odstavek spremeni tako, da se glasi:', 'replace'),
    ('Za šestim odstavkom se doda nov sedmi odstavek, ki se glasi:', 'add'),
    ('V 25. členu se tretji odstavek črta.', 'delete'),
    ('V 30. členu se besedilo »do 30. junija« nadomesti z besedilom »do 31. julija«.', 'replace'),
    ('Ta zakon začne veljati naslednji dan po objavi v Uradnem listu Republike Slovenije.', None),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestPisrsParser:
    def test_regulation(self, slovenia):
        parser = PisrsParser().parse(str(slovenia / 'URED8455_0.html'))
        assert parser.preface == 'UREDBO o pomožni policiji'
        assert parser.formula.startswith('Na podlagi 106. člena Zakona o organiziranosti in delu v policiji')
        # Chapters typed with a lower-case L read as Roman numerals
        chapter = parser.chapters[1]
        assert (chapter['eId'], chapter['num'], chapter['heading']) == (
            'cpt_II', 'll.', 'POSTOPEK POPOLNJEVANJA POMOŽNE POLICIJE IN NAČIN OPRAVLJANJA NALOG')
        article = parser.articles[0]
        assert (article['eId'], article['num'], article['heading'], article['parent']) == (
            'art_1', '1. člen', 'vsebina', 'cpt_I')
        assert len(parser.articles) == 23
        assert parser.conclusions == {'conclusion_text': 'Št. 00704-184/2022 Ljubljana, dne 18. maja 2022',
                                      'signature': 'EVA 2021-1711-0108 Vlada Republike Slovenije Janez Janša '
                                                   'predsednik'}

    def test_consolidated_version(self, slovenia):
        parser = PisrsParser().parse(str(slovenia / 'URED8455_2.html'))
        # The notice of the consolidated version is left out
        assert parser.preface == 'UREDBA o pomožni policiji'
        texts = ' '.join(c['text'] for a in parser.articles for c in a['children'])
        assert 'Neuradno prečiščeno besedilo' not in texts and 'Opozorilo' not in texts
        assert len(parser.articles) == 23

    def test_amending_law(self, slovenia):
        parser = PisrsParser().parse(str(slovenia / 'ZAKO8638_0.html'))
        assert parser.preface == 'ZAKON O SPREMEMBAH IN DOPOLNITVAH ZAKONA O DAVČNEM POSTOPKU (ZDavP-2N)'
        # Quoted chapters and articles stay in the amending articles
        assert len(parser.articles) == 41
        assert [c['heading'] for c in parser.chapters] == ['PREHODNE IN KONČNE DOLOČBE']
        instruction = parser.articles[1]['children'][0]
        assert instruction['text'].startswith('V 19. členu se četrti odstavek spremeni tako, da se glasi:')
        amendment = instruction['amendment']
        assert (amendment['action'], amendment['amended_act']) == ('replace', 'Zakonu o davčnem postopku')
        assert amendment['quoted'][0]['text'].startswith('(4) Davčni organ sme upravičeni osebi')

    def test_preamble_and_annexes(self, tmp_path):
        page = tmp_path / 'ustava.html'
        page.write_text(
            '<html><body><div class="mainText">'
            '<p class="zamik textJustify odstavek">Izhajajoč iz</p>'
            '<p class="zamik textJustify odstavek">Temeljne ustavne listine sprejema Skupščina</p>'
            '<p class="center bold uppercase naslov">USTAVO REPUBLIKE SLOVENIJE</p>'
            '<p class="center bold clen">1. člen</p><p class="zamik textJustify odstavek">Slovenija je republika.</p>'
            '<p class=" priloga"><a href="https://pisrs.si/api/datoteke/integracije/1">Priloga 1: Obrazec</a></p>'
            '</div></body></html>', encoding='utf-8')
        doc = PisrsParser().parse(str(page)).to_dict()
        assert doc['preamble']['recitals'] == [
            {'eId': 'rct_1', 'text': 'Izhajajoč iz Temeljne ustavne listine sprejema Skupščina'}]
        assert [c['text'] for c in doc['articles'][0]['children']] == ['Slovenija je republika.']
        assert doc['annexes'] == [{'eId': 'anx_1', 'num': 'Priloga 1', 'heading': 'Obrazec', 'children': []}]

    def test_page_without_text(self, tmp_path):
        page = tmp_path / 'page.html'
        page.write_text('<html><body><div>Napaka</div></body></html>')
        with pytest.raises(FileLoadError, match='no act text'):
            PisrsParser().parse(str(page))


class TestPisrsClient:
    def test_versions(self, record):
        versions = PisrsClient.versions(record)
        assert [(v['name'], v['date']) for v in versions] == [
            ('Osnovni', None), ('NPB 1', '2025-02-22'), ('NPB 2', '2026-06-13')]
        assert versions[0]['html'] == 355193883

    def test_record_by_gazette_number(self, record, tmp_path):
        client = PisrsClient(download_dir=str(tmp_path))
        answer = Mock(status_code=200, json=lambda: {'data': record})
        with patch.object(client.session, 'request', return_value=answer) as request:
            assert client.record('2022-01-1632', key='sop')['evidencniPodatki']['zunanjiID'] == 'URED8455'
        assert request.call_args.args[1] == 'https://pisrs.si/api/rezultat/zbirka/sop/2022-01-1632'

    def test_unknown_act(self, tmp_path):
        client = PisrsClient(download_dir=str(tmp_path))
        answer = Mock(status_code=200, json=lambda: {'data': None})
        with patch.object(client.session, 'request', return_value=answer):
            with pytest.raises(FileLoadError, match='no act ZAKO1'):
                client.record('ZAKO1')

    def test_search_body(self, tmp_path):
        client = PisrsClient(download_dir=str(tmp_path))
        answer = Mock(status_code=200, json=lambda: {'data': {'seznam': [search_hit('ZAKO7959', 'Zakon')]}})
        with patch.object(client.session, 'request', return_value=answer) as request:
            client.search(issue=('163', '2022'))
        assert request.call_args.kwargs['json'] == {
            'nazivZbirke': ['Register predpisov'], 'uradniListObjava': {'stevilkaObjave': '163', 'letoObjave': '2022'}}


class TestSloveniaSource:
    def fetch(self, slovenia, record, tmp_path, identifier, **kwargs):
        def download(self, act_id, version):
            # The fixtures hold the original and NPB 2
            return str(slovenia / f"URED8455_{0 if version['number'] == 0 else 2}.html")

        with patch.object(PisrsClient, 'record', return_value=record) as get_record, \
                patch.object(PisrsClient, 'download', autospec=True, side_effect=download) as get_file:
            doc = tulit.fetch(identifier, download_dir=str(tmp_path), **kwargs)
        return doc, get_record, get_file

    def test_original(self, slovenia, record, tmp_path):
        doc, get_record, get_file = self.fetch(slovenia, record, tmp_path, 'URED8455', jurisdiction='SI')
        get_record.assert_called_once_with('URED8455')
        assert get_file.call_args.args[2]['name'] == 'Osnovni'
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['language'], meta['version_date']) == (
            'SI', 'original', 'slv', '2022-05-20')
        assert meta['citation'] == 'Uradni list RS, št. 70/22, 11/25 in 797/26'
        assert meta['source'] == 'https://pisrs.si/pregledPredpisa?id=URED8455'

    @pytest.mark.parametrize('date, name, version_date', [
        (None, 'NPB 2', '2026-06-13'), ('2025-06-01', 'NPB 1', '2025-02-22'), ('2023-01-01', 'Osnovni', '2022-06-04')])
    def test_consolidated(self, slovenia, record, tmp_path, date, name, version_date):
        doc, _, get_file = self.fetch(slovenia, record, tmp_path, 'https://pisrs.si/pregledPredpisa?id=URED8455',
                                      version='consolidated', date=date)
        chosen = get_file.call_args.args[2]
        assert chosen['name'] == name
        assert doc['meta']['version_date'] == version_date

    def test_undated_versions_on_a_date(self, tmp_path):
        # PISRS dates only recent versions; an older one cannot apply before the acts it lists were published
        def notice(until):
            return ('<html><body><div class="mainText"><p>Neuradno prečiščeno besedilo obsega:</p>'
                    f'<p>- Zakon (Uradni list RS, št. 1/01 z dne {until})</p><p class="naslov">ZAKON</p>'
                    '<p class="clen">1. člen</p><p>Besedilo.</p></div></body></html>')
        pages = {1: notice('2. 4. 2004'), 2: notice('14. 10. 2016')}
        versions = [{'name': 'Osnovni', 'number': 0, 'html': 10, 'date': None},
                    {'name': 'NPB 1', 'number': 1, 'html': 11, 'date': None},
                    {'name': 'NPB 2', 'number': 2, 'html': 12, 'date': None}]

        def download(self, act_id, version):
            path = tmp_path / f"{act_id}_{version['number']}.html"
            path.write_text(pages.get(version['number'], notice('25. 10. 2001')), encoding='utf-8')
            return str(path)
        record = {'evidencniPodatki': {'veljaOd': '2002-01-01', 'objavljeno': '2001-10-25'}}
        with patch.object(PisrsClient, 'record', return_value=record), \
                patch.object(PisrsClient, 'versions', return_value=versions), \
                patch.object(PisrsClient, 'download', download):
            doc = tulit.fetch('ZAKO1263', jurisdiction='SI', version='consolidated', date='2010-01-01',
                              download_dir=str(tmp_path))
        assert doc['meta']['consolidation'] == 'NPB 1'

    def test_date_before_entry_into_force(self, slovenia, record, tmp_path):
        with pytest.raises(FileLoadError, match='enters into force on 2022-06-04'):
            self.fetch(slovenia, record, tmp_path, 'URED8455', jurisdiction='SI', version='consolidated',
                       date='2022-01-01')

    def test_gazette_number_and_link(self, slovenia, record, tmp_path):
        _, get_record, _ = self.fetch(slovenia, record, tmp_path,
                                      'https://www.uradni-list.si/glasilo-uradni-list-rs/vsebina/2022-01-1632')
        get_record.assert_called_once_with('2022-01-1632', key='sop')

    def test_abbreviation(self, slovenia, record, tmp_path):
        hits = [search_hit('ZAKO1', 'Zakon o spremembah Zakona o varstvu osebnih podatkov (ZVOP-1A)'),
                search_hit('ZAKO7959', 'Zakon o varstvu osebnih podatkov (ZVOP-2)')]
        with patch.object(PisrsClient, 'search', return_value=hits):
            _, get_record, _ = self.fetch(slovenia, record, tmp_path, 'ZVOP-2', jurisdiction='SI')
        get_record.assert_called_once_with('ZAKO7959')

    def test_ambiguous_citation(self, tmp_path):
        hits = [search_hit('ZAKO7959', 'Zakon o varstvu osebnih podatkov (ZVOP-2)'),
                search_hit('ZAKO8638', 'Zakon o spremembah in dopolnitvah Zakona o davčnem postopku (ZDavP-2N)')]
        with patch.object(PisrsClient, 'search', return_value=hits):
            with pytest.raises(ValueError, match='published 2 acts; give the PISRS id of one: ZAKO7959'):
                tulit.fetch('Uradni list RS, št. 163/22', jurisdiction='SI', download_dir=str(tmp_path))

    def test_bad_identifier(self, tmp_path):
        with pytest.raises(ValueError, match='not a Slovenian act identifier'):
            tulit.fetch('zakon o varstvu osebnih podatkov', jurisdiction='SI', download_dir=str(tmp_path))
