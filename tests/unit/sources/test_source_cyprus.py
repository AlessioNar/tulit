import urllib.parse
from unittest.mock import Mock, patch

import pytest

pytest.importorskip('pdfplumber')

import tulit  # noqa: E402
from tulit.client.state.cyprus import CyprusGazetteClient  # noqa: E402
from tulit.parser.exceptions import FileLoadError  # noqa: E402
from tulit.parser.pdf.cyprus import CyprusGazetteParser, amendment_action, normalise_number  # noqa: E402

ISSUE_PAGE = '''<html><body><a href="../5601BC24BB819A11C2258E750053FF80/$file/5096 17 9 2026 PARARTΗMA 1o MEROS I.pdf">
5096</a><p>Αριθμός Εφημερίδας: 5096 Σελίδες: 1069-1070 Ημερομηνία: 17/09/2026</p></body></html>'''
SEARCH_PAGE = '''<html><body>
<a href="../All/AAAA?OpenDocument&highlight=x">4385 - ΠΑΡΑΡΤΗΜΑ ΕΚΤΟ</a>
<a href="../All/5601BC24BB819A11C2258E750053FF80?OpenDocument&highlight=x">5096 - ΠΑΡΑΡΤΗΜΑ ΠΡΩΤΟ - ΜΕΡΟΣ (Ι)</a>
</body></html>'''


@pytest.fixture
def cyprus(data_root):
    return data_root / 'sources' / 'member_states' / 'cyprus'


@pytest.mark.parametrize('identifier', ['125(I)/2018', '125(Ι)/2018', 'Ν. 125(Ι)/2018', '125(Ι) του 2018',
                                        'N. 125 (I)/2018'])
def test_normalise_number(identifier):
    assert normalise_number(identifier) == '125(I)/2018'


def test_normalise_number_rejects_other_text():
    with pytest.raises(ValueError):
        normalise_number('Νόμος 125')


@pytest.mark.parametrize('instruction, action', [
    ('Το άρθρο 5 του βασικού νόμου αντικαθίσταται από το ακόλουθο νέο άρθρο:', 'replace'),
    ('Το Πρώτο Παράρτημα του βασικού νόμου τροποποιείται ως ακολούθως:', 'amend'),
    ('Στο άρθρο 2 προστίθεται ο ακόλουθος νέος ορισμός:', 'add'),
    ('οι περί Επεξεργασίας Δεδομένων Νόμοι του 2001 έως 2012 καταργούνται.', 'delete'),
    ('Ο παρών Νόμος θα αναφέρεται ως ο περί Φόρων Κατανάλωσης Νόμος.', None),
])
def test_amendment_action(instruction, action):
    assert amendment_action(instruction) == action


class TestCyprusGazetteParser:
    def test_law(self, cyprus):
        parser = CyprusGazetteParser('125(Ι)/2026').parse(str(cyprus / '5096_p1.pdf'))
        assert parser.recitals_init.startswith('Ο περί Φόρων Κατανάλωσης (Τροποποιητικός) (Αρ. 3) Νόμος του 2026 '
                                               'εκδίδεται με δημοσίευση')
        assert parser.preface == ('ΝΟΜΟΣ ΠΟΥ ΤΡΟΠΟΠΟΙΕΙ ΤΟΥΣ ΠΕΡΙ ΦΟΡΩΝ ΚΑΤΑΝΑΛΩΣΗΣ ΝΟΜΟΥΣ ΤΟΥ 2004 ΕΩΣ (ΑΡ. 2) '
                                  'ΤΟΥ 2026')
        assert parser.formula == 'Η Βουλή των Αντιπροσώπων ψηφίζει ως ακολούθως:'
        section = parser.articles[0]
        # The heading comes from the margin; the laws cited there are left out
        assert (section['eId'], section['num'], section['heading']) == ('art_1', '1.', 'Συνοπτικός τίτλος.')
        text = section['children'][0]['text']
        assert text.startswith('Ο παρών Νόμος θα αναφέρεται ως ο περί Φόρων Κατανάλωσης')
        assert '91(I) του 2004' not in text and 'Συνοπτικός' not in text

    def test_other_law_number(self, cyprus):
        with pytest.raises(FileLoadError, match='holds no law 126'):
            CyprusGazetteParser('126(I)/2026').parse(str(cyprus / '5096_p1.pdf'))

    def test_parts_and_subsections(self, cyprus):
        parser = CyprusGazetteParser().parse(str(cyprus / '4670_p14.pdf'))
        assert [(c['eId'], c['num'], c['heading']) for c in parser.chapters] == [
            ('prt_XII', 'ΜΕΡΟΣ ΧΙΙ', 'ΜΕΤΑΒΑΤΙΚΕΣ ΔΙΑΤΑΞΕΙΣ')]
        section = parser.articles[-1]
        assert (section['num'], section['heading'], section['parent']) == ('37.', 'Μεταβατικές διατάξεις.', 'prt_XII')
        assert [c['eId'] for c in section['children']] == ['par_1', 'par_2', 'par_3']


class TestCyprusGazetteClient:
    def test_find_and_describe_issue(self, tmp_path):
        client = CyprusGazetteClient(download_dir=str(tmp_path))
        responses = [Mock(status_code=200, content=SEARCH_PAGE.encode('utf-8')),
                     Mock(status_code=200, content=ISSUE_PAGE.encode('utf-8'))]
        with patch.object(client.session, 'get', side_effect=responses) as get:
            details = client.issue(client.find_law('125', 'I', '2026'))
        assert 'Αριθμός 125(Ι) του 2026' in urllib.parse.unquote(get.call_args_list[0].args[0])
        assert get.call_args_list[1].args[0].endswith('/All/5601BC24BB819A11C2258E750053FF80?OpenDocument')
        assert details == {
            'pdf': 'https://www.mof.gov.cy/mof/gpo/gazette.nsf/All/5601BC24BB819A11C2258E750053FF80/$file/'
                   '5096%2017%209%202026%20PARART%CE%97MA%201o%20MEROS%20I.pdf',
            'issue': '5096', 'pages': '1069-1070', 'date_publication': '2026-09-17'}

    def test_law_not_found(self, tmp_path):
        client = CyprusGazetteClient(download_dir=str(tmp_path))
        empty = Mock(status_code=200, content=b'<html><body>No results</body></html>')
        with patch.object(client.session, 'get', return_value=empty):
            with pytest.raises(FileLoadError, match='no law 64'):
                client.find_law('64', 'I', '2010')


class TestCyprusSource:
    def test_fetch(self, cyprus, tmp_path):
        details = {'pdf': 'https://www.mof.gov.cy/x.pdf', 'issue': '5096', 'pages': '1069-1070',
                   'date_publication': '2026-09-17'}
        with patch.object(CyprusGazetteClient, 'download',
                          return_value=(str(cyprus / '5096_p1.pdf'), details)) as download:
            doc = tulit.fetch('Ν. 125(Ι)/2026', jurisdiction='CY', download_dir=str(tmp_path))
        download.assert_called_once_with('125', 'I', '2026')
        meta = doc['meta']
        assert (meta['jurisdiction'], meta['version'], meta['language'], meta['version_date']) == (
            'CY', 'original', 'ell', '2026-09-17')
        assert (meta['number'], meta['gazette_issue']) == ('125(I)/2026', '5096')
        assert doc['articles'][0]['heading'] == 'Συνοπτικός τίτλος.'

    def test_no_consolidated_version(self, tmp_path):
        with pytest.raises(ValueError, match='does not publish the consolidated version'):
            tulit.fetch('125(I)/2018', jurisdiction='CY', version='consolidated', download_dir=str(tmp_path))

    def test_bad_identifier(self, tmp_path):
        with pytest.raises(ValueError, match='neither a Cypriot law number'):
            tulit.fetch('data protection law', jurisdiction='CY', download_dir=str(tmp_path))


VIEW = '/mof/gpo/gazette.nsf/dmlgazette_archive_gr/dmlgazette_archive_gr?OpenForm&Start=1&Count=9999'
ARCHIVE_YEARS = f'''<html><body><table>
<tr><td><a href="{VIEW}&Expand=16&Seq=1">2011</a></td></tr>
<tr><td><a href="{VIEW}&Expand=17&Seq=1">2010</a></td></tr>
</table></body></html>'''
ARCHIVE_MONTH = '''<html><body><table>
<tr><td></td><td><a href="/mof/gpo/gazette.nsf/All/2A853FB2F2C03848C225872C003C952E?OpenDocument">
Παρασκευή - 23/07/2010 - ΠΑΡΑΡΤΗΜΑ ΤΡΙΤΟ - ΜΕΡΟΣ (Ι) - Αρ. 4252</a></td></tr>
<tr><td></td><td><a href="/mof/gpo/gazette.nsf/All/05685C5CBA23148BC225872C003C952D?OpenDocument">
Παρασκευή - 23/07/2010 - - Αρ. 4252</a></td></tr>
</table></body></html>'''


class TestOlderIssues:
    def test_find_issue_in_archive(self, tmp_path):
        client = CyprusGazetteClient(download_dir=str(tmp_path))
        pages = [Mock(status_code=200, content=ARCHIVE_YEARS.encode('utf-8')),
                 Mock(status_code=200, content=ARCHIVE_MONTH.encode('utf-8'))]
        with patch.object(client.session, 'get', side_effect=pages) as get:
            link = client.find_issue('4252', 2010, 7)
        assert 'Expand=17.7.2' in get.call_args_list[1].args[0]
        # The Annex One issue, not another annex's issue with the same number
        assert link == 'https://www.mof.gov.cy/mof/gpo/gazette.nsf/All/05685C5CBA23148BC225872C003C952D?OpenDocument'

    @pytest.mark.parametrize('identifier, month', [('4252/2010', None), ('4252, 23.7.2010', 7),
                                                   ('Αρ. 4252/2010', None)])
    def test_issue_reference(self, cyprus, tmp_path, identifier, month):
        details = {'pdf': 'https://www.mof.gov.cy/x.pdf', 'issue': '4252', 'date_publication': '2010-07-23'}
        with patch.object(CyprusGazetteClient, 'find_issue', return_value='https://link') as find_issue, \
                patch.object(CyprusGazetteClient, 'download_issue',
                             return_value=(str(cyprus / '5096_p1.pdf'), details)), \
                patch('tulit.sources.cy._has_text', return_value=False):
            found = tulit.download(identifier, 'CY', download_dir=str(tmp_path))
            with pytest.raises(FileLoadError, match='only as a scanned document'):
                tulit.fetch(identifier, 'CY', download_dir=str(tmp_path))
        find_issue.assert_called_with('4252', 2010, month)
        assert found['parser'] is None
        assert found['path'].endswith('5096_p1.pdf')
        assert (found['version_date'], found['meta']['gazette_issue'], found['meta']['scanned']) == (
            '2010-07-23', '4252', True)

    def test_issue_link_with_law_number(self, cyprus, tmp_path):
        details = {'pdf': 'https://www.mof.gov.cy/x.pdf', 'issue': '5096', 'date_publication': '2026-09-17'}
        link = 'https://www.mof.gov.cy/mof/gpo/gazette.nsf/All/5601BC24BB819A11C2258E750053FF80?OpenDocument'
        with patch.object(CyprusGazetteClient, 'download_issue',
                          return_value=(str(cyprus / '5096_p1.pdf'), details)) as download_issue:
            doc = tulit.fetch(link, number='125(Ι)/2026', download_dir=str(tmp_path))
        download_issue.assert_called_once_with(link)
        assert doc['meta']['jurisdiction'] == 'CY'
        assert doc['meta']['number'] == '125(I)/2026'

    def test_old_law_number_points_to_issues(self, tmp_path):
        with patch.object(CyprusGazetteClient, 'search', return_value=[]):
            with pytest.raises(FileLoadError, match="give the Annex One issue"):
                tulit.fetch('64(I)/2010', 'CY', download_dir=str(tmp_path))
