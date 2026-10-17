import json
from unittest.mock import Mock, patch

import pytest

pytest.importorskip('pdfplumber')

import tulit  # noqa: E402
from tulit.client.state.greece import GovernmentGazetteClient, pdf_url  # noqa: E402
from tulit.parser.exceptions import FileLoadError  # noqa: E402
from tulit.parser.pdf.greece import GovernmentGazetteParser, amendment_action  # noqa: E402
from tulit.sources.gr import reference  # noqa: E402

ROW = {'search_ID': '581161', 'search_DocumentNumber': '137', 'search_IssueGroupID': '1',
       'search_IssueDate': '08/29/2019 00:00:00', 'search_PublicationDate': '08/29/2019 00:00:00',
       'search_Pages': '28', 'search_PrimaryLabel': 'Α 137/2019', 'search_LawID': '1',
       'search_LawProtocolNumber': '4624', 'search_Description': 'ΑΡΧΗ ΠΡΟΣΤΑΣΙΑΣ ΔΕΔΟΜΕΝΩΝ ΠΡΟΣΩΠΙΚΟΥ ΧΑΡΑΚΤΗΡΑ'}


def answer(rows):
    return Mock(status_code=200, json=Mock(return_value={'status': 'ok', 'data': json.dumps(rows)}))


@pytest.fixture
def greece(data_root):
    return data_root / 'sources' / 'member_states' / 'greece'


@pytest.mark.parametrize('identifier, expected', [
    ('ν. 4624/2019', ('law', '4624', '2019')),
    ('Ν. 4624/2019', ('law', '4624', '2019')),
    ('4624/2019', ('law', '4624', '2019')),
    ('π.δ. 70/2015', ('decree', '70', '2015')),
    ('ΠΔ 70/2015', ('decree', '70', '2015')),
    ('ΦΕΚ Α 137/29.08.2019', ('issue', '1/137', '2019')),
    ("Α' 137/2019", ('issue', '1/137', '2019')),
    ('ΦΕΚ A΄ 137/2019', ('issue', '1/137', '2019')),
    ('https://ia37rg02wpsa01.blob.core.windows.net/fek/01/2019/20190100137.pdf', ('issue', '1/137', '2019')),
])
def test_reference(identifier, expected):
    assert reference(identifier) == expected


def test_reference_rejects_other_text():
    with pytest.raises(ValueError):
        reference('data protection law')


def test_pdf_url():
    assert pdf_url('1', '137', '2019') == 'https://ia37rg02wpsa01.blob.core.windows.net/fek/01/2019/20190100137.pdf'


@pytest.mark.parametrize('instruction, action', [
    ('Το άρθρο 31 του ν. 3986/2011 (Α΄ 152) αντικαθίσταται ως εξής:', 'replace'),
    ('Στην παρ. 1 του άρθρου 14 προστίθενται περ. κ) και κα) ως εξής:', 'add'),
    ('Η παρ. 3 του άρθρου 5 καταργείται.', 'delete'),
    ('Σκοπός του παρόντος νόμου είναι:', None),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestGovernmentGazetteParser:
    def test_law(self, greece):
        parser = GovernmentGazetteParser().parse(str(greece / 'a137_2019_p1_p28.pdf'))
        assert parser.preface.startswith('NOMOΣ ΥΠ΄ΑΡΙΘΜ. 4624 Αρχή Προστασίας Δεδομένων Προσωπικού Χαρακτήρα')
        assert parser.formula == ('Ο ΠΡΟΕΔΡΟΣ ΤΗΣ ΕΛΛΗΝΙΚΗΣ ΔΗΜΟΚΡΑΤΙΑΣ Εκδίδομε τον ακόλουθο νόμο που '
                                  'ψήφισε η Βουλή:')
        assert [(c['eId'], c['num'], c['heading']) for c in parser.chapters] == [
            ('cpt_Α', 'ΚΕΦΑΛΑΙΟ Α΄', 'ΓΕΝΙΚΕΣ ΔΙΑΤΑΞΕΙΣ')]
        first = parser.articles[0]
        assert (first['eId'], first['num'], first['heading'], first['parent']) == (
            'art_1', 'Άρθρο 1', 'Σκοπός του νόμου', 'cpt_Α')
        # Points stay in their paragraph; the two columns are read in turn
        assert first['children'][0]['text'].startswith('Σκοπός του παρόντος νόμου είναι: α) η αντικατάσταση')
        assert parser.articles[1]['heading'] == 'Ουσιαστικό πεδίο εφαρμογής'
        last = parser.articles[-1]
        assert (last['num'], last['heading']) == ('Άρθρο 87', 'Έναρξη ισχύος')
        assert parser.conclusions['conclusion_text'].startswith('Παραγγέλλομε τη δημοσίευση του παρόντος')
        assert parser.conclusions['signature'].startswith('Αθήνα, 28 Αυγούστου 2019 Ο Πρόεδρος της Δημοκρατίας')
        # The page headers and the masthead are left out
        texts = ' '.join(c['text'] for a in parser.articles for c in a['children'])
        assert 'ΕΦΗΜΕΡΙΔΑ' not in texts and 'Τεύχος' not in texts

    @pytest.mark.parametrize('number, articles', [('70', 6), ('71', 5)])
    def test_decrees_in_one_issue(self, greece, number, articles):
        parser = GovernmentGazetteParser(number).parse(str(greece / 'a114_2015.pdf'))
        assert parser.preface.startswith(f'ΠΡΟΕΔΡΙΚΟ ΔΙΑΤΑΓΜΑ ΥΠ΄ ΑΡΙΘΜ. {number}')
        assert parser.formula == 'Ο ΠΡΟΕΔΡΟΣ ΤΗΣ ΕΛΛΗΝΙΚΗΣ ΔΗΜΟΚΡΑΤΙΑΣ αποφασίζουμε:'
        assert parser.recitals_init == 'Έχοντας υπόψη:'
        assert parser.recitals[0]['text'].startswith('1. Τις διατάξεις:')
        assert len(parser.articles) == articles
        assert parser.conclusions['conclusion_text'].startswith('Στον Πρωθυπουργό αναθέτουμε τη δημοσίευση')

    def test_decree_not_in_issue(self, greece):
        with pytest.raises(FileLoadError, match='holds no act 72'):
            GovernmentGazetteParser('72').parse(str(greece / 'a114_2015.pdf'))

    def test_amendment(self, greece):
        parser = GovernmentGazetteParser().parse(str(greece / 'a198_2024_p6.pdf'))
        article = parser.articles[0]
        assert article['num'] == 'Άρθρο 4'
        assert article['heading'].startswith('Εξαιρέσεις από τον υπολογισμό του εισοδήματος')
        amendment = article['children'][0]['amendment']
        assert amendment['action'] == 'add'
        assert amendment['amended_act'] == 'ν. 4172/2013'
        assert amendment['quoted'][0]['text'].startswith('κ) παροχές')


class TestGovernmentGazetteClient:
    def test_find_act(self, tmp_path):
        client = GovernmentGazetteClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'post', return_value=answer([ROW])) as post:
            issue = client.find_act('law', '4624', '2019')
        assert post.call_args.args[0] == 'https://searchetv99.azurewebsites.net/api/searchlegislation'
        assert post.call_args.kwargs['json'] == {'legislationCatalogues': '1', 'legislationNumber': '4624',
                                                 'selectYear': ['2019']}
        assert (issue['part'], issue['issue'], issue['label'], issue['date_publication']) == (
            '1', '137', 'Α 137/2019', '2019-08-29')

    def test_act_not_found(self, tmp_path):
        client = GovernmentGazetteClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'post', return_value=answer([])):
            with pytest.raises(FileLoadError, match='no law 9999/2019'):
                client.find_act('law', '9999', '2019')

    def test_find_issue(self, tmp_path):
        client = GovernmentGazetteClient(download_dir=str(tmp_path))
        with patch.object(client.session, 'post', return_value=answer([ROW])) as post:
            issue = client.find_issue('1', '137', '2019')
        assert post.call_args.kwargs['json'] == {'selectYear': ['2019'], 'selectIssue': ['1'],
                                                 'documentNumber': '137'}
        assert issue['issue'] == '137'

    def test_download(self, greece, tmp_path):
        client = GovernmentGazetteClient(download_dir=str(tmp_path))
        pdf = Mock(status_code=200, content=(greece / 'a114_2015.pdf').read_bytes())
        with patch.object(client.session, 'get', return_value=pdf) as get:
            path = client.download({'part': '1', 'issue': '114'}, '2015')
        assert get.call_args.args[0] == 'https://ia37rg02wpsa01.blob.core.windows.net/fek/01/2015/20150100114.pdf'
        assert path.endswith('20150100114.pdf')


class TestGreeceSource:
    def test_law(self, greece, tmp_path):
        with patch.object(GovernmentGazetteClient, 'find_act', return_value={
                'part': '1', 'issue': '137', 'label': 'Α 137/2019', 'date_publication': '2019-08-29'}) as find_act, \
                patch.object(GovernmentGazetteClient, 'download',
                             return_value=str(greece / 'a137_2019_p1_p28.pdf')):
            doc = tulit.fetch('ν. 4624/2019', jurisdiction='GR', download_dir=str(tmp_path))
        find_act.assert_called_once_with('law', '4624', '2019')
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['language'], meta['version_date']) == (
            'GR', 'original', 'ell', '2019-08-29')
        assert meta['gazette_issue'] == 'Α 137/2019'
        assert meta['source'] == 'https://ia37rg02wpsa01.blob.core.windows.net/fek/01/2019/20190100137.pdf'
        assert doc['articles'][0]['heading'] == 'Σκοπός του νόμου'

    def test_decree_picked_from_issue(self, greece, tmp_path):
        with patch.object(GovernmentGazetteClient, 'find_act', return_value={'part': '1', 'issue': '114'}), \
                patch.object(GovernmentGazetteClient, 'download', return_value=str(greece / 'a114_2015.pdf')):
            doc = tulit.fetch('π.δ. 71/2015', jurisdiction='GR', download_dir=str(tmp_path))
        assert doc['preface'].startswith('ΠΡΟΕΔΡΙΚΟ ΔΙΑΤΑΓΜΑ ΥΠ΄ ΑΡΙΘΜ. 71')

    def test_issue_link(self, greece, tmp_path):
        url = 'https://ia37rg02wpsa01.blob.core.windows.net/fek/01/2015/20150100114.pdf'
        with patch.object(GovernmentGazetteClient, 'find_issue', return_value={'part': '1', 'issue': '114'}), \
                patch.object(GovernmentGazetteClient, 'download', return_value=str(greece / 'a114_2015.pdf')):
            doc = tulit.fetch(url, number='70', download_dir=str(tmp_path))
        assert doc['meta']['jurisdiction'] == 'GR'
        assert doc['preface'].startswith('ΠΡΟΕΔΡΙΚΟ ΔΙΑΤΑΓΜΑ ΥΠ΄ ΑΡΙΘΜ. 70')

    def test_no_consolidated_version(self, tmp_path):
        with pytest.raises(ValueError, match='does not publish the consolidated version'):
            tulit.fetch('ν. 4624/2019', jurisdiction='GR', version='consolidated', download_dir=str(tmp_path))
