import json
from unittest.mock import Mock, patch

import pytest

pytest.importorskip('pdfplumber')

import tulit  # noqa: E402
from tulit.client.state.greece import GovernmentGazetteClient, pdf_url  # noqa: E402
from tulit.parser.exceptions import FileLoadError  # noqa: E402
from tulit.parser.pdf.greece import (  # noqa: E402
    _DIVISION, GovernmentGazetteParser, _Line, _text, amendment_action, read_lines)
from tulit.sources.gr import reference  # noqa: E402

ROW = {'search_ID': '581161', 'search_DocumentNumber': '137', 'search_IssueGroupID': '1',
       'search_IssueDate': '08/29/2019 00:00:00', 'search_PublicationDate': '08/29/2019 00:00:00',
       'search_Pages': '28', 'search_PrimaryLabel': 'Α 137/2019', 'search_LawID': '1',
       'search_LawProtocolNumber': '4624', 'search_Description': 'ΑΡΧΗ ΠΡΟΣΤΑΣΙΑΣ ΔΕΔΟΜΕΝΩΝ ΠΡΟΣΩΠΙΚΟΥ ΧΑΡΑΚΤΗΡΑ'}


def body_lines(specs):
    """Lines of a column from (indent, text[, bold]); a full line runs to the column's right edge."""
    lines = []
    for n, (indent, text, *bold) in enumerate(specs):
        full = indent < 10 and len(text) > 30 and not text.endswith(('.', ':', '”'))
        x1 = 300.0 if full else 100.0 + indent + 4 * len(text)
        lines.append(_Line(0, 0, 10.0 * n, 50.0 + indent, x1, text, 9.0, bool(bold and bold[0]), 50.0, 300.0))
    return lines


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
        # 'NOMOΣ' is set with Latin capitals in the PDF
        assert parser.preface.startswith('ΝΟΜΟΣ ΥΠ΄ ΑΡΙΘΜ. 4624 Αρχή Προστασίας Δεδομένων Προσωπικού Χαρακτήρα')
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

    def test_latin_capitals_in_greek_words(self):
        chars = [{'text': c, 'x0': float(i), 'x1': float(i) + 1} for i, c in enumerate('NOMOΣ')]
        assert _text(chars) == 'ΝΟΜΟΣ'
        # Words without Greek letters keep their Latin capitals
        chars = [{'text': c, 'x0': float(i), 'x1': float(i) + 1} for i, c in enumerate('(EE)')]
        assert _text(chars) == '(EE)'

    def test_words_of_a_tightly_set_line(self):
        # A title of ν. 5220/2025: letters overlap by 0.1pt, words stand 1.3pt apart
        chars, x = [], 0.0
        for word in ('αξιολόγηση', 'προσωπικού'):
            for letter in word:
                chars.append({'text': letter, 'x0': x, 'x1': x + 5.0})
                x += 4.9
            x += 1.4
        assert _text(chars) == 'αξιολόγηση προσωπικού'
        # In ordinary lines, letters 1.3pt apart belong to one word
        chars = [{'text': c, 'x0': i * 6.3, 'x1': i * 6.3 + 5.0} for i, c in enumerate('ΤΗΣ')]
        chars += [{'text': c, 'x0': 30.0 + i * 5.0, 'x1': 35.0 + i * 5.0} for i, c in enumerate('ΙΙ')]
        assert _text(chars) == 'ΤΗΣ ΙΙ'

    def test_division_title_run_on(self):
        match = _DIVISION.match('ΚΕΦΑΛΑΙΟ Α΄ΕΝΣΩΜΑΤΩΣΗ ΟΔΗΓΙΑΣ (ΕΕ) 2019/1158')
        assert (match.group('head'), match.group('title')) == ('ΚΕΦΑΛΑΙΟ Α΄', 'ΕΝΣΩΜΑΤΩΣΗ ΟΔΗΓΙΑΣ (ΕΕ) 2019/1158')
        assert _DIVISION.match('ΜΕΡΟΣ ΙV').group('num') == 'ΙV'
        assert not _DIVISION.match('ΚΕΦΑΛΑΙΟ Α΄ του ν. 4624/2019')

    def test_treaty_keeps_its_articles(self):
        # The ratifying article quotes the treaty, whose quotation closes with ” instead of »; the treaty numbers
        # its articles from 1, and the law resumes with a division and the next article (ν. 4808/2021)
        parser = GovernmentGazetteParser()
        parser._read_body(body_lines([
            (23, 'ΜΕΡΟΣ I'), (23, 'ΚΥΡΩΣΗ ΤΗΣ ΣΥΜΒΑΣΗΣ 190'), (23, 'Άρθρο 1'), (23, 'Κύρωση διεθνούς σύμβασης'),
            (9, 'Κυρώνεται η Σύμβαση 190, το κείμενο της οποίας έχει ως εξής:'), (9, '«Σύμβαση 190'),
            (23, 'Άρθρο 1'), (9, '1. Για τους σκοπούς αυτής της Σύμβασης.'), (23, 'Άρθρο 2'),
            (9, 'Η παρούσα Σύμβαση εφαρμόζεται.'), (23, 'Άρθρο 3'), (9, 'Κάθε Μέλος σέβεται.'),
            (94, 'Article 1'), (9, 'This Convention is authoritative.”'),
            (22, 'ΜΕΡΟΣ ΙΙ'), (22, 'ΥΙΟΘΕΤΗΣΗ ΜΕΤΡΩΝ'), (22, 'Άρθρο 2'), (22, 'Σκοπός'),
            (8, 'Σκοπός του παρόντος Μέρους είναι η πρόληψη.')]))
        assert [(a['num'], a['parent']) for a in parser.articles] == [('Άρθρο 1', 'prt_I'), ('Άρθρο 2', 'prt_ΙΙ')]
        assert [(c['num'], c['heading']) for c in parser.chapters] == [
            ('ΜΕΡΟΣ I', 'ΚΥΡΩΣΗ ΤΗΣ ΣΥΜΒΑΣΗΣ 190'), ('ΜΕΡΟΣ ΙΙ', 'ΥΙΟΘΕΤΗΣΗ ΜΕΤΡΩΝ')]
        treaty = ' '.join(c['text'] for c in parser.articles[0]['children'])
        assert 'Άρθρο 3 Κάθε Μέλος σέβεται.' in treaty and treaty.endswith('authoritative.”')
        assert parser.articles[1]['heading'] == 'Σκοπός'

    def test_code_held_by_an_article_in_words(self):
        # ν. 3463/2006 ratifies a code in its first article; the code's divisions and articles are its text
        parser = GovernmentGazetteParser()
        parser._read_body(body_lines([
            (86, 'Άρθρο πρώτο'), (8, 'Κυρώνεται ο Κώδικας Δήμων και Κοινοτήτων.'), (88, 'ΚΕΦΑΛΑΙΟ Α΄'),
            (80, 'ΓΕΝΙΚΗ ΔΙΑΤΑΞΗ'), (99, 'Άρθρο 1'), (8, '1. Η Τοπική Αυτοδιοίκηση καταργείται.'),
            (86, 'Άρθρο δεύτερο'), (8, 'Από την έναρξη ισχύος του παρόντος.'),
            (86, 'Άρθρο εικοστό πρώτο'), (8, 'Η ισχύς του παρόντος αρχίζει.'),
            (8, 'Παραγγέλομε τη δημοσίευση του παρόντος.')]))
        assert [(a['eId'], a['num']) for a in parser.articles] == [
            ('art_1', 'Άρθρο πρώτο'), ('art_2', 'Άρθρο δεύτερο'), ('art_21', 'Άρθρο εικοστό πρώτο')]
        assert parser.chapters == []
        code = parser.articles[0]['children']
        assert [c['text'] for c in code][1:] == ['ΚΕΦΑΛΑΙΟ Α΄ ΓΕΝΙΚΗ ΔΙΑΤΑΞΗ Άρθρο 1',
                                                 '1. Η Τοπική Αυτοδιοίκηση καταργείται.']
        # The code's text amends nothing
        assert all(c['amendment'] is None for c in code)
        # 'Παραγγέλομε' as misspelt in 2026 issues
        assert parser.conclusions['conclusion_text'] == 'Παραγγέλομε τη δημοσίευση του παρόντος.'

    def test_only_amendments_of_other_acts(self):
        # ν. 4624/2019: entries deleted, a budget amended, are provisions of the law itself
        parser = GovernmentGazetteParser()
        parser._read_body(body_lines([
            (23, 'Άρθρο 74'), (23, 'Τήρηση αρχείων'), (9, '4. Οι καταχωρίσεις διαγράφονται στο τέλος του έτους.'),
            (9, '5. Ο προϋπολογισμός της Αρχής μπορεί να τροποποιείται με απόφαση του Υπουργού.'),
            (9, '6. Η παρ. 3 του άρθρου 3 του Ν. 4151/2013 καταργείται.'),
            (9, '7. Στο άρθρο 67 του Κ.Φ.Ε. προστίθεται παρ. 8 ως εξής: «8. Αν η ημερομηνία παρέλθει.»'),
            (9, '8. Από την έναρξη ισχύος του παρόντος καταργούνται:')]))
        assert [(c['eId'], (c['amendment'] or {}).get('action')) for c in parser.articles[0]['children']] == [
            ('par_4', None), ('par_5', None), ('par_6', 'delete'), ('par_7', 'add'), ('par_8', 'delete')]

    def test_contents_headed_in_lower_case(self):
        # ν. 5270/2026: 'Πίνακας Περιεχομένων'; the contents end at the divisions above the first article
        lines = body_lines([(14, 'Πίνακας Περιεχομένων'), (14, 'ΜΕΡΟΣ Α΄'), (14, 'ΡΥΘΜΙΣΕΙΣ'), (14, 'Άρθρο 1 Σκοπός'),
                            (28, 'ΜΕΡΟΣ Α΄'), (28, 'ΡΥΘΜΙΣΕΙΣ'), (28, 'Άρθρο 1'), (28, 'Σκοπός')])
        assert [line.text for line in GovernmentGazetteParser._without_contents(lines)] == [
            'ΜΕΡΟΣ Α΄', 'ΡΥΘΜΙΣΕΙΣ', 'Άρθρο 1', 'Σκοπός']

    def test_next_article_on_a_page_set_across(self):
        # The last page of the act of legislative content of 25.2.2020: its last article is set flush with the
        # signatures, which give the page's margin
        parser = GovernmentGazetteParser()
        parser._read_body(body_lines([(23, 'Άρθρο πέμπτο'), (23, 'Έκτακτη ενίσχυση'), (8, 'Με κοινή απόφαση.'),
                                      (0, 'Άρθρο έκτο'), (0, 'Έναρξη ισχύος'), (-14, 'Η ισχύς της παρούσας αρχίζει.')]))
        assert [(a['num'], a['heading']) for a in parser.articles] == [
            ('Άρθρο πέμπτο', 'Έκτακτη ενίσχυση'), ('Άρθρο έκτο', 'Έναρξη ισχύος')]

    def test_first_line_set_in_as_far_as_the_heading(self):
        # Issues of 2026 are set across the page; the first line of a paragraph runs to the right edge
        parser = GovernmentGazetteParser()
        parser._read_body(body_lines([(28, 'Άρθρο πρώτο'), (28, 'Κύρωση Συμφωνίας'),
                                      (14, 'Κυρώνεται και έχει την ισχύ, που ορίζει η παρ. 1 του άρθρου 28 του'),
                                      (0, 'Συντάγματος, η Συμφωνία.')]))
        article = parser.articles[0]
        assert article['heading'] == 'Κύρωση Συμφωνίας'
        assert article['children'][0]['text'].startswith('Κυρώνεται και έχει την ισχύ')

    def test_article_set_in_the_middle_of_a_page(self):
        # The last article of ν. 4387/2016, set in a narrow block on a page of its own: its text is set in as far
        # as its heading, but in roman where the number and heading are bold
        parser = GovernmentGazetteParser()
        parser._read_body(body_lines([(217, 'Άρθρο 122', True), (207, 'Έναρξη ισχύος', True),
                                      (131, 'Η ισχύς του παρόντος νόμου αρχίζει από τη δημοσί-'),
                                      (124, 'ευσή του στην Εφημερίδα της Κυβερνήσεως.')]))
        article = parser.articles[0]
        assert article['heading'] == 'Έναρξη ισχύος'
        assert article['children'][0]['text'] == ('Η ισχύς του παρόντος νόμου αρχίζει από τη δημοσίευσή του στην '
                                                  'Εφημερίδα της Κυβερνήσεως.')

    def test_paragraph_across_a_page_signed_in_columns(self, greece):
        # The last page of ν. 5190/2025: the article and the order to publish run across the page, the signatures
        # below them are set in columns
        parser = GovernmentGazetteParser().parse(str(greece / 'a51_2025_p8.pdf'))
        assert parser.articles[0]['children'][0]['text'] == (
            'Η ισχύς του παρόντος νόμου αρχίζει από τη δημοσίευσή του στην Εφημερίδα της Κυβερνήσεως και της '
            'Συμφωνίας που κυρώνεται από την πλήρωση των προϋποθέσεων του άρθρου 10 αυτής.')
        assert parser.conclusions['conclusion_text'] == ('Παραγγέλλομε τη δημοσίευση του παρόντος στην Εφημερίδα '
                                                         'της Κυβερνήσεως και την εκτέλεσή του ως νόμου του Κράτους.')

    def test_garbled_facsimile_left_out(self):
        # A treaty as signed, in fonts without their characters' codes (ν. 5190/2025)
        def char(text, x):
            return {'text': text, 'x0': x, 'x1': x + 5.0, 'size': 10.0, 'fontname': 'F', 'top': 100.0,
                    'bottom': 110.0}
        garbled = [char('(cid:24)', 50.0 + 6 * i) for i in range(60)]
        page = Mock(width=595.0, chars=garbled, extract_text_lines=Mock(return_value=[
            {'top': 400.0, 'bottom': 410.0, 'chars': garbled}]))
        pdf = Mock(pages=[page])
        pdf.__enter__ = Mock(return_value=pdf)
        pdf.__exit__ = Mock(return_value=False)
        with patch('tulit.parser.pdf.greece._pdfplumber', return_value=Mock(open=Mock(return_value=pdf))):
            assert read_lines('issue.pdf') == []

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

    def test_scanned_issue(self, greece, tmp_path):
        # ν. 2472/1997 is published in a scanned issue, without text but for its barcode
        with patch.object(GovernmentGazetteClient, 'find_act', return_value={'part': '1', 'issue': '50'}), \
                patch.object(GovernmentGazetteClient, 'download', return_value=str(greece / 'a50_1997_p2.pdf')):
            found = tulit.download('ν. 2472/1997', jurisdiction='GR', download_dir=str(tmp_path))
            with pytest.raises(FileLoadError, match='only as a scanned document'):
                tulit.fetch('ν. 2472/1997', jurisdiction='GR', download_dir=str(tmp_path))
        assert found['parser'] is None
        assert found['meta']['scanned'] is True

    def test_no_consolidated_version(self, tmp_path):
        with pytest.raises(ValueError, match='does not publish the consolidated version'):
            tulit.fetch('ν. 4624/2019', jurisdiction='GR', version='consolidated', download_dir=str(tmp_path))
