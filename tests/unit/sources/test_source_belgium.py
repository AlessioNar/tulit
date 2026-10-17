from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.belgium import EJusticeClient, iso_date
from tulit.parser.exceptions import FileLoadError
from tulit.parser.html.ejustice import EJusticeParser, amendment_action
from tulit.sources.be import act_reference


@pytest.fixture
def belgium(data_root):
    return data_root / 'sources' / 'member_states' / 'belgium'


@pytest.mark.parametrize('identifier, expected', [
    ('loi/2018/07/30/2018040581', ('loi', '2018-07-30', '2018040581', None)),
    ('https://www.ejustice.just.fgov.be/eli/loi/2018/07/30/2018040581/justel',
     ('loi', '2018-07-30', '2018040581', 'fra')),
    ('https://www.ejustice.just.fgov.be/eli/wet/2018/07/30/2018040581/staatsblad',
     ('loi', '2018-07-30', '2018040581', 'nld')),
    ('https://www.ejustice.just.fgov.be/eli/decreet/2018/12/07/2018015301',
     ('decret', '2018-12-07', '2018015301', 'nld')),
    ('arrete/2024/04/28/2024A03378', ('arrete', '2024-04-28', '2024A03378', None)),
])
def test_act_reference(identifier, expected):
    assert act_reference(identifier) == expected


@pytest.mark.parametrize('identifier', ['2018040581', 'loi/2018/07/30', 'reglement/2018/07/30/2018040581'])
def test_act_reference_rejects(identifier):
    with pytest.raises(ValueError):
        act_reference(identifier)


@pytest.mark.parametrize('instruction, action', [
    ("L'article 3 est remplacé par ce qui suit :", 'replace'),
    ('Dans le même arrêté, il est inséré un article 7/1 rédigé comme suit :', 'insert'),
    ('Aan titel 2 wordt een hoofdstuk 12 toegevoegd, dat luidt als volgt:', 'add'),
    ('Artikel 5 wordt opgeheven.', 'delete'),
    ('In artikel 2 worden de volgende wijzigingen aangebracht:', 'amend'),
    ("La présente loi règle une matière visée à l'article 74 de la Constitution.", None),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestEJusticeParser:
    def test_publication(self, belgium):
        parser = EJusticeParser().parse(str(belgium / '2020044419_fra_publication.html'))
        assert parser.preface.startswith('20 DECEMBRE 2020. - Arrêté royal relatif aux cadres linguistiques')
        assert parser.formula == ('PHILIPPE, Roi des Belges, A tous, présents et à venir, Salut. '
                                  'Nous avons arrêté et arrêtons :')
        # The report to the King, then the citations
        assert parser.recitals[0]['text'].startswith('RAPPORT AU ROI')
        assert parser.recitals[1]['text'].startswith('Vu les lois sur l\'emploi des langues')
        assert [c['num'] for c in parser.chapters] == ['CHAPITRE 1er', 'CHAPITRE 2', 'CHAPITRE 3', 'CHAPITRE 4']
        assert parser.chapters[3]['heading'] == 'Dispositions finales'
        assert [a['eId'] for a in parser.articles] == [f'art_{n}' for n in range(1, 8)]
        assert parser.articles[0]['num'] == 'Article 1er.'
        assert parser.conclusions == {'conclusion_text': 'Bruxelles, le 20 décembre 2020.',
                                      'signature': "PHILIPPE Par le Roi : La Ministre de l'Intérieur, A. VERLINDEN "
                                                   "Le Ministre de la Justice, V. VAN QUICKENBORNE"}

    def test_justel(self, belgium):
        parser = EJusticeParser().parse(str(belgium / '2020044419_fra_justel.html'))
        assert parser.preface.startswith('20 DECEMBRE 2020. - Arrêté royal')
        assert parser.formula.endswith('Nous avons arrêté et arrêtons :')
        assert parser.recitals[0]['text'].startswith('Vu les lois')
        assert len(parser.articles) == 7
        # A table is one line per row, joined to the paragraph introducing it
        first = parser.articles[0]['children']
        assert len(first) == 1 and ' | ' in first[0]['text']
        assert parser.conclusions['conclusion_text'] == 'Bruxelles, le 20 décembre 2020.'

    def test_justel_markers_and_notes_left_out(self, belgium):
        parser = EJusticeParser().parse(str(belgium / '2018015301_nld_justel.html'))
        texts = ' '.join(c['text'] for a in parser.articles for c in a['children'])
        assert '[1' not in texts and ']1' not in texts
        assert 'Ingevoegd bij' not in texts and '----------' not in texts

    def test_amending_order(self, belgium):
        parser = EJusticeParser().parse(str(belgium / '2020031023_fra_publication.html'))
        # A citation running over several lines stays in the recitals
        assert parser.formula == ('PHILIPPE, Roi des Belges, A tous, présents et à venir, Salut. '
                                  'Nous avons arrêté et arrêtons :')
        assert parser.recitals[-1]['text'] == "Sur la proposition du Ministre de l'Emploi,"
        first = parser.articles[0]['children'][0]['amendment']
        assert first['action'] == 'insert'
        assert first['amended_act'].startswith('arrêté royal du 5 juillet 2004')
        assert first['quoted']
        # 'du même arrêté' names the act amended before
        assert parser.articles[1]['children'][0]['amendment']['amended_act'] == first['amended_act']
        assert parser.conclusions['conclusion_text'] == 'Donné à Bruxelles, le 26 juin 2020.'

    def test_dutch_decree(self, belgium):
        parser = EJusticeParser().parse(str(belgium / '2018015301_nld_publication.html'))
        assert parser.formula == ('Het VLAAMS PARLEMENT heeft aangenomen en Wij, REGERING, '
                                  'bekrachtigen hetgeen volgt:')
        assert parser.articles[0]['num'] == 'Artikel 1.'
        amendment = parser.articles[1]['children'][0]['amendment']
        assert amendment['action'] == 'amend'
        assert amendment['amended_act'].startswith('Codex Fiscaliteit van 13 december 2013')
        assert len(amendment['quoted']) == 4
        assert parser.articles[2]['children'][0]['amendment']['action'] == 'add'
        assert parser.conclusions['conclusion_text'].startswith('Kondigen dit decreet af')
        assert parser.conclusions['signature'].startswith('Brussel, 7 december 2018.')

    def test_annex(self, belgium):
        parser = EJusticeParser().parse(str(belgium / '2024009737_fra_publication.html'))
        assert parser.formula == 'LE GOUVERNEMENT FLAMAND ARRETE :'
        annex = parser.annexes[0]
        assert (annex['num'], annex['heading']) == ('Annexe', "Taux d'inoccupation, tels que visés à l'article 10")
        assert annex['children'][1]['text'] == "Toutes les catégories d'animaux de l'espèce Porcins | 10 %"
        assert 'Annexe' not in (parser.conclusions['signature'] or '')

    def test_repealed_act(self, belgium):
        parser = EJusticeParser().parse(str(belgium / '2020030839_fra_justel.html'))
        assert parser.articles == []

    def test_page_without_text(self, tmp_path):
        page = tmp_path / 'page.html'
        page.write_text('<html><body><p>Attention</p></body></html>')
        with pytest.raises(FileLoadError, match='no act text'):
            EJusticeParser().parse(str(page))


class TestEJusticeClient:
    def test_eli(self):
        assert EJusticeClient.eli('loi', '2018-07-30', '2018040581', 'nld', 'publication') == \
            'https://www.ejustice.just.fgov.be/eli/wet/2018/07/30/2018040581/staatsblad'
        assert EJusticeClient.eli('arrete', '2020-12-20', '2020044419', 'fra', 'justel') == \
            'https://www.ejustice.just.fgov.be/eli/arrete/2020/12/20/2020044419/justel'

    def test_iso_date(self):
        assert iso_date('05-09-2018') == '2018-09-05'
        assert iso_date('5 septembre 2018') == '2018-09-05'
        assert iso_date('20 december 2018') == '2018-12-20'

    def test_metadata(self, belgium):
        meta = EJusticeClient.metadata(str(belgium / '2018015301_nld_justel.html'))
        assert meta['title'].startswith('7 DECEMBER 2018. - Decreet tot wijziging')
        assert (meta['issuer'], meta['date_publication'], meta['date_in_force']) == (
            'Vlaamse Overheid', '2018-12-20', '2019-01-01')
        assert meta['amends'] == ['2013036154']

    def test_archives(self, belgium):
        number, link = EJusticeClient.archive_link(str(belgium / '2020030839_fra_justel.html'))
        assert number == 2 and 'arch=002' in link
        # The table of archives shares its box id with the report to the King
        assert EJusticeClient.archives(str(belgium / '2020030839_fra_justel_002.html')) == [
            (1, '2020-06-05'), (2, '2020-05-04')]

    def test_publication_answered_with_404(self, belgium, tmp_path):
        client = EJusticeClient(download_dir=str(tmp_path))
        page = Mock(status_code=404, content=(belgium / '2020044419_fra_publication.html').read_bytes())
        with patch.object(client.session, 'get', return_value=page):
            path = client.download('arrete', '2020-12-20', '2020044419', 'fra')
        assert path.endswith('2020044419_fra_publication.html')

    def test_pdf_only_publication(self, tmp_path):
        client = EJusticeClient(download_dir=str(tmp_path))
        page = Mock(status_code=404, content='<main class="article-text"><p>Attention</p><p>Les textes publiés '
                    'avant le 1 juin 1997 sont consultables uniquement au format PDF</p></main>'.encode('latin-1'))
        with patch.object(client.session, 'get', return_value=page):
            with pytest.raises(FileLoadError, match='only as PDF'):
                client.download('constitution', '1994-02-17', '1994021048', 'fra')


class TestBelgiumSource:
    def test_original(self, belgium, tmp_path):
        def download(doc_type, date, numac, language='fra', consolidated=False):
            return str(belgium / f"{numac}_{language}_{'justel' if consolidated else 'publication'}.html")

        with patch.object(EJusticeClient, 'download', side_effect=download):
            doc = tulit.fetch('https://www.ejustice.just.fgov.be/eli/decreet/2018/12/07/2018015301',
                              download_dir=str(tmp_path))
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['language'], meta['version_date']) == (
            'BE', 'original', 'nld', '2018-12-07')
        assert meta['source'] == 'https://www.ejustice.just.fgov.be/eli/decreet/2018/12/07/2018015301/staatsblad'
        assert meta['date_publication'] == '2018-12-20'
        assert len(doc['articles']) == 65

    def test_consolidated_without_archives(self, belgium, tmp_path):
        with patch.object(EJusticeClient, 'download', return_value=str(belgium / '2020044419_fra_justel.html')), \
                patch.object(EJusticeClient, 'archive_link', return_value=None):
            doc = tulit.fetch('arrete/2020/12/20/2020044419', jurisdiction='BE', version='consolidated',
                              download_dir=str(tmp_path))
        assert doc['meta']['version'] == 'consolidated'
        assert doc['meta']['source'].endswith('/2020044419/justel')

    @pytest.mark.parametrize('date, archive, start', [
        ('2020-06-01', 1, '2020-05-04'), ('2021-01-01', 2, '2020-06-05')])
    def test_consolidated_on_a_date(self, belgium, tmp_path, date, archive, start):
        current = str(belgium / '2020030839_fra_justel.html')
        latest = str(belgium / '2020030839_fra_justel_002.html')
        with patch.object(EJusticeClient, 'download', return_value=current), \
                patch.object(EJusticeClient, 'download_archive', return_value=latest) as download_archive, \
                patch.object(EJusticeClient, 'archives', return_value=[(1, '2020-06-05'), (2, '2026-01-01')]), \
                patch.object(EJusticeClient, 'metadata', return_value={'date_in_force': '2020-05-04'}), \
                patch.object(EJusticeClient, 'article_count', return_value=7):
            doc = tulit.fetch('arrete/2020/05/04/2020030839', jurisdiction='BE', version='consolidated',
                              date=date, download_dir=str(tmp_path))
        assert download_archive.call_args_list[-1].args[-1] == archive
        assert doc['meta']['version_date'] == start
        assert len(doc['articles']) == 7

    def test_date_before_entry_into_force(self, belgium, tmp_path):
        with patch.object(EJusticeClient, 'download', return_value=str(belgium / '2020030839_fra_justel.html')), \
                patch.object(EJusticeClient, 'metadata', return_value={'date_in_force': '2020-05-04'}):
            with pytest.raises(FileLoadError, match='enters into force on 2020-05-04'):
                tulit.fetch('arrete/2020/05/04/2020030839', jurisdiction='BE', version='consolidated',
                            date='2020-05-03', download_dir=str(tmp_path))

    def test_repealed_act_today(self, belgium, tmp_path):
        with patch.object(EJusticeClient, 'download', return_value=str(belgium / '2020030839_fra_justel.html')), \
                patch.object(EJusticeClient, 'download_archive',
                             return_value=str(belgium / '2020030839_fra_justel_002.html')):
            doc = tulit.fetch('arrete/2020/05/04/2020030839', jurisdiction='BE', version='consolidated',
                              download_dir=str(tmp_path))
        assert doc['articles'] == []
        assert doc['meta']['version_date'] == '2020-05-04'

    def test_partial_archive(self, belgium, tmp_path):
        with patch.object(EJusticeClient, 'download', return_value=str(belgium / '2020030839_fra_justel.html')), \
                patch.object(EJusticeClient, 'download_archive',
                             return_value=str(belgium / '2020030839_fra_justel_002.html')), \
                patch.object(EJusticeClient, 'archives', return_value=[(1, '2020-06-05'), (2, '2026-01-01')]), \
                patch.object(EJusticeClient, 'metadata', return_value={}), \
                patch.object(EJusticeClient, 'article_count', side_effect=lambda path: 1 if '_002' in path else 100):
            with pytest.raises(FileLoadError, match='only the articles changed'):
                tulit.fetch('arrete/2020/05/04/2020030839', jurisdiction='BE', version='consolidated',
                            date='2020-05-20', download_dir=str(tmp_path))
