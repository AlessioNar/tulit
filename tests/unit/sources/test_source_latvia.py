from unittest.mock import Mock, patch

import pytest

import tulit
from tulit.client.state.latvia import LikumiClient, iso_date
from tulit.parser.exceptions import FileLoadError
from tulit.parser.html.likumi import LikumiParser, amendment_action
from tulit.sources.lv import act_id


@pytest.fixture
def latvia(data_root):
    return data_root / 'sources' / 'member_states' / 'latvia'


@pytest.mark.parametrize('identifier', [
    '300099', 'https://likumi.lv/ta/id/300099-fizisko-personu-datu-apstrades-likums',
    'https://likumi.lv/ta/id/300099', 'https://www.vestnesis.lv/ta/id/300099',
    'https://likumi.lv/ta/en/en/id/300099-personal-data-processing-law',
])
def test_act_id(identifier):
    assert act_id(identifier) == '300099'


def test_act_id_rejects_other_text():
    with pytest.raises(ValueError):
        act_id('Fizisko personu datu apstrādes likums')


@pytest.mark.parametrize('instruction, action', [
    ('Izteikt 5. panta pirmās daļas 2. punktu šādā redakcijā:', 'replace'),
    ('Aizstāt 23. pantā vārdus "a" ar vārdiem "b".', 'replace'),
    ('Papildināt likumu ar 23.1 pantu šādā redakcijā:', 'add'),
    ('Izslēgt 7. pantu.', 'delete'),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestLikumiParser:
    def test_consolidated_law(self, latvia):
        parser = LikumiParser().parse(str(latvia / '300099.html'))
        assert parser.preface == 'Fizisko personu datu apstrādes likums'
        assert parser.formula == 'Saeima ir pieņēmusi un Valsts prezidents izsludina šādu likumu:'
        chapter = parser.chapters[0]
        assert (chapter['eId'], chapter['num'], chapter['heading']) == ('cpt_I', 'I nodaļa', 'Vispārīgie noteikumi')
        article = parser.articles[2]
        assert (article['eId'], article['num'], article['heading'], article['parent']) == (
            'art_3', '3. pants', 'Datu valsts inspekcija', 'cpt_II')
        assert [c['eId'] for c in article['children']] == [f'par_{n}' for n in range(1, 8)]
        # An article inserted by an amendment, and no amendment notes in the text
        inserted = next(a for a in parser.articles if a['num'] == '23.1 pants')
        assert inserted['eId'] == 'art_23-1'
        assert not any('redakcijā, kas stājas spēkā' in c['text'] for a in parser.articles for c in a['children'])
        assert parser.annexes[0]['heading'] == 'Pārejas noteikumi'
        assert len(parser.annexes[0]['children']) == 5
        assert parser.conclusions['signature'] == 'Valsts prezidents R. Vējonis Rīgā 2018. gada 4. jūlijā'

    def test_official_publication(self, latvia):
        parser = LikumiParser().parse(str(latvia / '300099_op.html'))
        assert parser.preface == 'Fizisko personu datu apstrādes likums'
        assert len(parser.chapters) == 8
        assert len(parser.articles) == 37
        point = parser.articles[3]['children'][0]
        assert point['text'].startswith('(1) Inspekcija pilda') and ' 1) uzrauga' in point['text']
        assert parser.conclusions['conclusion_text'].startswith('Likums stājas spēkā')

    def test_amending_law(self, latvia):
        parser = LikumiParser().parse(str(latvia / '323369.html'))
        assert parser.recitals[0]['text'].startswith('Izdarīt Fizisko personu datu apstrādes likumā')
        assert [a['num'] for a in parser.articles] == ['1.', '2.', '3.', '4.', '5.']
        amendment = parser.articles[0]['children'][0]['amendment']
        assert amendment['action'] == 'replace'
        assert amendment['amended_act'] == 'Fizisko personu datu apstrādes likumā'
        assert amendment['quoted'] == [{'kind': 'text', 'text': '2) veikt administratīvā pārkāpuma procesu;'}]
        # The quoted chapter and articles stay inside the amending point
        added = parser.articles[3]['children'][0]
        assert added['amendment']['action'] == 'add'
        assert '38. pants' in added['text'] and len(added['amendment']['quoted']) == 6
        assert parser.chapters == []
        assert parser.conclusions['conclusion_text'] == 'Likums Saeimā pieņemts 2021. gada 6. maijā.'

    @pytest.mark.parametrize('name', ['355850.html', '355850_op.html'])
    def test_regulation(self, latvia, name):
        parser = LikumiParser().parse(str(latvia / name))
        assert parser.formula.startswith('Ministru kabineta noteikumi Nr. 656')
        assert parser.recitals[0]['text'].startswith('Izdoti saskaņā ar')
        assert [a['num'] for a in parser.articles] == [f'{n}.' for n in range(1, 9)]
        # Sub-points stay in their point
        assert '3.9.' in ' '.join(c['text'] for c in parser.articles[2]['children'])
        annex = parser.annexes[0]
        assert annex['num'].startswith('Pielikums')
        assert annex['heading'] == 'Latvijas Nacionālā botāniskā dārza publisko maksas pakalpojumu cenrādis'
        assert annex['children'][0]['text'].startswith('Nr. p. k. Pakalpojuma veids')
        assert parser.conclusions['signature'].startswith('Ministru prezidente E. Siliņa')

    def test_early_publication(self, latvia):
        parser = LikumiParser().parse(str(latvia / '57980_op.html'))
        assert [c['num'] for c in parser.chapters][-1] == 'VII nodaļa'
        assert parser.chapters[-1]['heading'] == 'Valsts kontrole'
        assert len(parser.articles) == 88
        assert parser.conclusions['signature'].startswith('J. Čakste')

    def test_page_without_act(self, tmp_path):
        page = tmp_path / 'page.html'
        page.write_text('<html><body><div class="news">Jaunumi</div></body></html>')
        with pytest.raises(FileLoadError, match='no act text'):
            LikumiParser().parse(str(page))


class TestLikumiClient:
    def test_metadata(self, latvia):
        meta = LikumiClient.metadata(str(latvia / '300099.html'))
        assert meta['title'] == 'Fizisko personu datu apstrādes likums'
        assert (meta['type'], meta['issuer']) == ('likums', 'Saeima')
        assert (meta['date_document'], meta['date_in_force'], meta['date_publication']) == (
            '2018-06-21', '2018-07-05', '2018-07-04')
        assert meta['op_number'] == '2018/132.1'

    def test_versions(self, latvia, tmp_path):
        assert LikumiClient(str(tmp_path)).versions(str(latvia / '300099.html')) == ['2019-05-31', '2021-06-04']

    def test_iso_date(self):
        assert iso_date('05.07.2018.') == '2018-07-05'
        assert iso_date(None) is None

    def test_dated_version_url(self, latvia, tmp_path):
        client = LikumiClient(download_dir=str(tmp_path))
        page = Mock(status_code=200, content=(latvia / '300099.html').read_bytes())
        with patch.object(client.session, 'get', return_value=page) as get:
            path = client.download('300099', '2020-01-01')
        assert get.call_args[0][0] == 'https://likumi.lv/ta/id/300099/redakcijas-datums/2020/01/01'
        assert path.endswith('300099_2020-01-01.html')

    def test_unknown_act_in_gazette(self, tmp_path):
        client = LikumiClient(download_dir=str(tmp_path))
        home = Mock(status_code=200, content=b'<html><body><div class="news">Jaunumi</div></body></html>')
        with patch.object(client.session, 'get', return_value=home):
            with pytest.raises(FileLoadError, match='no text'):
                client.download_publication('999999999')


class TestLatviaSource:
    def test_original(self, latvia, tmp_path):
        with patch.object(LikumiClient, 'download', return_value=str(latvia / '300099.html')), \
                patch.object(LikumiClient, 'download_publication',
                             return_value=str(latvia / '300099_op.html')) as publication:
            doc = tulit.fetch('https://likumi.lv/ta/id/300099-fizisko-personu-datu-apstrades-likums',
                              jurisdiction='LV', download_dir=str(tmp_path))
        publication.assert_called_once_with('300099')
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['version_date']) == ('LV', 'original', '2018-06-21')
        assert meta['source'] == 'https://www.vestnesis.lv/ta/id/300099'
        assert len(doc['articles']) == 37

    def test_original_without_gazette_text(self, latvia, tmp_path):
        with patch.object(LikumiClient, 'download', return_value=str(latvia / '300099.html')) as download, \
                patch.object(LikumiClient, 'download_publication', side_effect=FileLoadError('no text')):
            doc = tulit.fetch('300099', jurisdiction='LV', download_dir=str(tmp_path))
        # The first version on likumi.lv, as it entered into force
        assert download.call_args_list[-1].args == ('300099', '2018-07-05')
        assert doc['meta']['source'] == 'https://likumi.lv/ta/id/300099'

    def test_consolidated(self, latvia, tmp_path):
        with patch.object(LikumiClient, 'download', return_value=str(latvia / '300099.html')):
            doc = tulit.fetch('300099', jurisdiction='LV', version='consolidated', download_dir=str(tmp_path))
        meta = doc['meta']
        assert (meta['version'], meta['version_date']) == ('consolidated', '2021-06-04')
        assert len(doc['articles']) == 40

    def test_date_before_entry_into_force(self, latvia, tmp_path):
        with patch.object(LikumiClient, 'download', return_value=str(latvia / '300099.html')):
            with pytest.raises(FileLoadError, match='enters into force on 2018-07-05'):
                tulit.fetch('300099', jurisdiction='LV', version='consolidated', date='2018-01-01',
                            download_dir=str(tmp_path))

    def test_jurisdiction_from_link(self, latvia, tmp_path):
        with patch.object(LikumiClient, 'download', return_value=str(latvia / '300099.html')), \
                patch.object(LikumiClient, 'download_publication', return_value=str(latvia / '300099_op.html')):
            doc = tulit.fetch('https://www.vestnesis.lv/ta/id/300099', download_dir=str(tmp_path))
        assert doc['meta']['jurisdiction'] == 'LV'
