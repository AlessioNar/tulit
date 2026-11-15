import glob
import io
import os
import tarfile
from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.france_dila import DilaClient, id_path
from tulit.parser.exceptions import FileLoadError
from tulit.parser.xml.dila import DilaParser, amendment_action
from tulit.sources.fr import _matcher, reference

DECREE = 'JORFTEXT000054988304'


@pytest.fixture
def france(data_root):
    return data_root / 'sources' / 'member_states' / 'france' / 'dila'


def _jorf_archive(folder) -> bytes:
    """A daily JORF archive holding the files of one text, laid out as the DILA lays them out."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for path in glob.glob(os.path.join(folder, '*', '*.xml')):
            kind, name = path.split(os.sep)[-2:]
            ident = name[:-4]
            prefix = {'version': 'texte/version', 'struct': 'texte/struct', 'article': 'article',
                      'section_ta': 'section_ta'}[kind]
            info = tarfile.TarInfo(f'20261016-213852/jorf/global/{prefix}/{id_path(ident)}.xml')
            content = open(path, 'rb').read()
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


@pytest.mark.parametrize('identifier, expected', [
    ('JORFTEXT000054988304', {'id': 'JORFTEXT000054988304'}),
    ('ECOE2626788D', {'nor': 'ECOE2626788D'}),
    ('Décret n° 2026-959 du 15 octobre 2026', {'num': '2026-959', 'date': '2026-10-15', 'nature': 'DECRET'}),
    ('LOI n° 2025-1249 du 22 décembre 2025', {'num': '2025-1249', 'date': '2025-12-22', 'nature': 'LOI'}),
    ('Loi n° 2018-493 du 1er juin 2018', {'num': '2018-493', 'date': '2018-06-01'}),
    ('https://www.legifrance.gouv.fr/eli/decret/2026/10/15/ECOE2626788D/jo/texte',
     {'nor': 'ECOE2626788D', 'date': '2026-10-15', 'nature': 'DECRET'}),
])
def test_reference(identifier, expected):
    found = reference(identifier)
    assert {key: found[key] for key in expected} == expected


def test_reference_rejects_other_text():
    with pytest.raises(ValueError):
        reference('the data protection law')


def test_matcher_accepts_an_open_date():
    # loi 2025-1251: the DILA gives it no date (2999-01-01)
    match = _matcher(reference('LOI n° 2025-1251 du 22 décembre 2025'))
    assert match({'num': '2025-1251', 'date_texte': '2999-01-01'})
    assert not match({'num': '2025-1251', 'date_texte': '2024-01-01'})


def test_id_path():
    assert id_path('JORFTEXT000054988304') == 'JORF/TEXT/00/00/54/98/83/JORFTEXT000054988304'


@pytest.mark.parametrize('instruction, action', [
    ("L'article L. 2123-23 est ainsi rédigé :", 'replace'),
    ('Le code général des collectivités territoriales est ainsi modifié :', 'amend'),
    ('Après le mot : « municipal, », sont insérés les mots : « d\'une part, » ;', 'insert'),
    ('Le 3° est abrogé.', 'delete'),
    ('Il est institué une indemnité carburant.', None),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestDilaParser:
    def test_decree(self, france):
        parser = DilaParser().parse(str(france / DECREE))
        assert parser.preface.startswith('Décret n° 2026-959 du 15 octobre 2026 relatif à la création')
        assert parser.formula.startswith('Le Premier ministre, Sur le rapport du ministre de l\'économie')
        assert parser.citations[0]['text'].startswith('Vu le code des assurances')
        assert parser.preamble_final == 'Décrète :'
        assert [a['num'] for a in parser.articles] == [f'Article {n}' for n in range(1, 11)]
        # Numbered paragraphs ('1.') are children of their own
        assert [c['eId'] for c in parser.articles[1]['children']][:2] == ['par_1', 'par_2']
        assert parser.conclusions['conclusion_text'] == 'Fait le 15 octobre 2026.'

    def test_amending_law(self, france):
        parser = DilaParser().parse(str(france / 'JORFTEXT000053142169'))
        assert parser.formula == "L'Assemblée nationale et le Sénat ont adopté,"
        assert parser.preamble_final == 'Le Président de la République promulgue la loi dont la teneur suit :'
        assert [(c['eId'], c['num']) for c in parser.chapters] == [('tit_Ier', 'Titre Ier')]
        assert all(a['parent'] == 'tit_Ier' for a in parser.articles)
        amendment = parser.articles[0]['children'][0]['amendment']
        assert amendment['action'] == 'amend'
        assert amendment['amended_act'] == 'code général des collectivités territoriales'
        # the table's cells, without the lone guillemet opening it
        assert len(amendment['quoted']) == 19 and all(q['text'] for q in amendment['quoted'])

    def test_consolidated_on_a_date(self, france):
        assert len(DilaParser(date='2026-10-17').parse(str(france / f'{DECREE}_LEGI')).articles) == 10
        # Not yet in force the day before
        assert DilaParser(date='2026-10-16').parse(str(france / f'{DECREE}_LEGI')).articles == []

    def test_folder_without_text(self, tmp_path):
        with pytest.raises(FileLoadError, match='no DILA text'):
            DilaParser().parse(str(tmp_path))

    def test_parts_annex_and_closing_formula(self, tmp_path):
        # loi 2025-1403 (LFSS 2026): 'PREMIÈRE PARTIE', an annex printed as unnumbered articles, and the
        # closing formula printed in the last article
        files = {
            'version': '<TEXTE_VERSION><META><META_COMMUN><ID>JORFTEXT1</ID></META_COMMUN></META><TITREFULL>LOI n° '
                       '2025-1403</TITREFULL><SIGNATAIRES><CONTENU><p>Fait le 30 décembre 2025.</p></CONTENU>'
                       '</SIGNATAIRES></TEXTE_VERSION>',
            'struct': '<TEXTELR><META><META_COMMUN><ID>JORFTEXT1</ID></META_COMMUN></META><STRUCT>'
                      '<LIEN_SECTION_TA id="S1">PREMIÈRE PARTIE : DISPOSITIONS RELATIVES AUX RECETTES</LIEN_SECTION_TA>'
                      '<LIEN_ART id="A3" num=""/><LIEN_ART id="A4" num=""/></STRUCT></TEXTELR>',
            'section': '<SECTION_TA><ID>S1</ID><STRUCTURE_TA><LIEN_ART id="A1" num="1"/><LIEN_ART id="A2" num="2"/>'
                       '</STRUCTURE_TA></SECTION_TA>',
        }
        articles = {'A1': 'I. - Le code est ainsi modifié :', 'A2': "L'objectif est fixé à 43,6 milliards d'euros."
                    "</p><p>La présente loi entrera en vigueur immédiatement et sera exécutée comme loi de l'Etat.",
                    'A3': 'ANNEXE</p><p>RAPPORT DÉCRIVANT LES PRÉVISIONS</p><p>I. - Situation',
                    'A4': 'II. - Prévisions'}
        for name, content in files.items():
            (tmp_path / f'{name}.xml').write_text(content, encoding='utf-8')
        for ident, text in articles.items():
            (tmp_path / f'{ident}.xml').write_text(
                f'<ARTICLE><META><META_COMMUN><ID>{ident}</ID></META_COMMUN></META><BLOC_TEXTUEL><CONTENU><p>{text}'
                '</p></CONTENU></BLOC_TEXTUEL></ARTICLE>', encoding='utf-8')
        parser = DilaParser().parse(str(tmp_path))
        assert [(c['eId'], c['type'], c['num']) for c in parser.chapters] == [('prt_1', 'part', 'PREMIÈRE PARTIE')]
        assert [a['num'] for a in parser.articles] == ['Article 1', 'Article 2']
        assert [c['text'] for c in parser.articles[1]['children']] == ["L'objectif est fixé à 43,6 milliards d'euros."]
        assert parser.conclusions['conclusion_text'].startswith('La présente loi entrera en vigueur')
        assert [(a['num'], a['heading']) for a in parser.annexes] == [('ANNEXE', 'RAPPORT DÉCRIVANT LES PRÉVISIONS')]
        assert [c['text'] for c in parser.annexes[0]['children']] == ['I. - Situation', 'II. - Prévisions']


class TestDilaClient:
    def test_archives(self, tmp_path):
        client = DilaClient(download_dir=str(tmp_path))
        listing = Mock(status_code=200, content=b'<a href="Freemium_jorf_global_20250713-140000.tar.gz">x</a>'
                       b'<a href="JORF_20261016-213852.tar.gz">x</a><a href="JORF_20250713-002503.tar.gz">x</a>')
        with patch.object(client.session, 'get', return_value=listing):
            assert client.archives('JORF') == [('JORF_20250713-002503.tar.gz', '2025-07-13'),
                                               ('JORF_20261016-213852.tar.gz', '2026-10-16')]

    def test_find_published_and_text_files(self, france, tmp_path):
        client = DilaClient(download_dir=str(tmp_path))
        archive = Mock(status_code=200, content=_jorf_archive(france / DECREE))
        with patch.object(DilaClient, 'archives', return_value=[('JORF_20261016-213852.tar.gz', '2026-10-16')]), \
                patch.object(client.session, 'get', return_value=archive):
            identifier, files = client.find_published(lambda meta: meta['num'] == '2026-959', '2026-10-15')
        assert identifier == DECREE
        folder = client.save(identifier, client.text_files(identifier, files))
        assert sorted(os.listdir(folder)) == ['article', 'struct', 'version']
        assert len(os.listdir(os.path.join(folder, 'article'))) == 10

    def test_find_by_id_bisects(self, france, tmp_path):
        client = DilaClient(download_dir=str(tmp_path))
        archive = _jorf_archive(france / DECREE)
        empty = io.BytesIO()
        with tarfile.open(fileobj=empty, mode='w:gz'):
            pass
        names = [(f'JORF_2026100{n}-000000.tar.gz', f'2026-10-0{n}') for n in range(1, 4)]
        contents = {names[0][0]: empty.getvalue(), names[1][0]: archive, names[2][0]: empty.getvalue()}

        def get(url, timeout):
            return Mock(status_code=200, content=contents[url.rsplit('/', 1)[1]])

        with patch.object(DilaClient, 'archives', return_value=names), \
                patch.object(client.session, 'get', side_effect=get):
            identifier, files = client.find_by_id(DECREE)
        assert identifier == DECREE and any(path.endswith(f'{DECREE}.xml') for path in files)

    def test_dump(self, france, tmp_path):
        # An extracted dump: jorf/global with the files at their DILA paths
        dump = tmp_path / 'dump'
        with tarfile.open(fileobj=io.BytesIO(_jorf_archive(france / DECREE)), mode='r:gz') as archive:
            archive.extractall(dump, filter='data')
        client = DilaClient(download_dir=str(tmp_path / 'downloads'))
        root = client.dump_root(str(dump), 'JORF')
        index = client.dump_index(root)
        assert [meta['id'] for meta in index] == [DECREE]
        files = client.dump_files(root, index[0]['path'])
        assert len([path for path in files if '/article/' in f'/{path}']) == 10


class TestFranceSource:
    def _published(self, france):
        folder = str(france / DECREE)
        eli = 'https://www.legifrance.gouv.fr/eli/decret/2026/10/15/ECOE2626788D/jo/texte'
        meta = {'id': DECREE, 'nor': 'ECOE2626788D', 'num': '2026-959', 'date_texte': '2026-10-15',
                'date_publi': '2026-10-16', 'eli': eli, 'source': 'x'}
        return folder, meta

    def test_original(self, france, tmp_path):
        with patch('tulit.sources.fr.FranceSource._published', return_value=self._published(france)) as published:
            doc = tulit.fetch('https://www.legifrance.gouv.fr/eli/decret/2026/10/15/ECOE2626788D/jo/texte',
                              download_dir=str(tmp_path))
        assert published.call_args.args[1]['nor'] == 'ECOE2626788D'
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['version_date'], meta['nor']) == (
            'FR', 'original', '2026-10-16', 'ECOE2626788D')
        assert len(doc['articles']) == 10

    def test_consolidated(self, france, tmp_path):
        folder = str(france / f'{DECREE}_LEGI')
        with patch('tulit.sources.fr.FranceSource._consolidated',
                   return_value=(folder, self._published(france)[1])):
            doc = tulit.fetch('Décret n° 2026-959 du 15 octobre 2026', jurisdiction='FR', version='consolidated',
                              date='2026-10-20', download_dir=str(tmp_path))
        assert (doc['meta']['version'], doc['meta']['version_date']) == ('consolidated', '2026-10-17')
        assert len(doc['articles']) == 10

    def test_old_text_needs_dump(self, tmp_path):
        with patch.object(DilaClient, 'archives', return_value=[('JORF_20250713-002503.tar.gz', '2025-07-13')]):
            with pytest.raises(FileLoadError, match='dump_dir'):
                tulit.fetch('Loi n° 2018-493 du 20 juin 2018', jurisdiction='FR', download_dir=str(tmp_path))

    def test_nor_alone_needs_date(self, tmp_path):
        with patch.object(DilaClient, 'archives', return_value=[('JORF_20250713-002503.tar.gz', '2025-07-13')]):
            with pytest.raises(ValueError, match='its date'):
                tulit.fetch('ECOE2626788D', jurisdiction='FR', download_dir=str(tmp_path))

    def test_long_consolidation_needs_dump(self, france, tmp_path):
        legi = [(f'LEGI_{n}.tar.gz', '2026-11-01') for n in range(61)]
        with patch('tulit.sources.fr.FranceSource._published', return_value=self._published(france)), \
                patch.object(DilaClient, 'archives', return_value=legi):
            with pytest.raises(FileLoadError, match='global LEGI dump'):
                tulit.fetch('Décret n° 2026-959 du 15 octobre 2026', jurisdiction='FR', version='consolidated',
                            date='2026-12-31', download_dir=str(tmp_path))
