from tulit.quality import ERROR, WARNING, check, counts


def _doc(**changes):
    doc = {
        'preface': 'Data Protection Act',
        'preamble': {'formula': 'The Parliament enacts:', 'citations': [], 'recitals': [],
                     'recitals_intro': None, 'final': None},
        'chapters': [{'eId': 'cpt_1', 'type': 'chapter', 'num': 'Chapter 1', 'heading': 'General', 'parent': None}],
        'articles': [{'eId': 'art_1', 'num': '1.', 'heading': 'Scope', 'parent': 'cpt_1',
                      'children': [{'eId': 'par_1', 'text': '(1) This Act applies to data.', 'amendment': None}]}],
        'annexes': [],
        'meta': {'jurisdiction': 'XX', 'language': 'eng', 'version': 'original', 'source': 'https://example.org',
                 'version_date': '2018-06-21'},
    }
    doc.update(changes)
    return doc


def _errors(doc, **options):
    return [p for p in check(doc, **options) if p.severity == ERROR]


def test_clean_document():
    assert check(_doc()) == []


def test_missing_title_and_articles():
    found = _errors(_doc(preface=None, articles=[]))
    assert {p.where for p in found} == {'preface', 'articles'}
    # A repealed act may have no articles
    assert [p.where for p in _errors(_doc(articles=[]), expect_articles=False)] == []


def test_duplicate_and_dangling_identifiers():
    article = _doc()['articles'][0]
    doc = _doc(articles=[article, dict(article, parent='cpt_9')])
    messages = [str(p) for p in _errors(doc)]
    assert any('2 articles share this eId' in m for m in messages)
    assert any('cpt_9 is not a division' in m for m in messages)


def test_markup_and_broken_characters():
    child = {'eId': 'par_1', 'text': 'Text with <b>markup</b> &nbsp; and �', 'amendment': None}
    article = dict(_doc()['articles'][0], children=[child])
    messages = [str(p) for p in _errors(_doc(articles=[article]))]
    assert any('markup left' in m for m in messages)
    assert any('broken or control characters' in m for m in messages)


def test_amendments():
    child = {'eId': 'unp_1', 'text': 'Article 5 is replaced.',
             'amendment': {'action': 'rewrite', 'instruction': '', 'amended_act': None, 'quoted': []}}
    article = dict(_doc()['articles'][0], children=[child])
    messages = [str(p) for p in _errors(_doc(articles=[article]))]
    assert any("unknown amendment action 'rewrite'" in m for m in messages)
    assert any('no instruction' in m for m in messages)


def test_page_header_in_articles():
    header = 'OFFICIAL GAZETTE OF THE REPUBLIC, No 132, page 4'
    articles = [{'eId': f'art_{n}', 'num': f'{n}.', 'heading': None, 'parent': None,
                 'children': [{'eId': 'unp_1', 'text': f'Provision {n}. {header}', 'amendment': None}]}
                for n in range(1, 9)]
    warnings = [p for p in check(_doc(articles=articles, chapters=[])) if p.severity == WARNING]
    assert any('recurs in 8 articles' in p.message for p in warnings)


def test_recurring_citation_is_not_a_page_header():
    # An amending act citing the same regulation in many articles
    citation = ('rozporządzenia 2016/679 w sprawie ochrony osób fizycznych w związku z przetwarzaniem danych '
                'osobowych (Dz. Urz. UE L 119 z 04.05.2016, str. 1)')
    articles = [{'eId': f'art_{n}', 'num': f'{n}.', 'heading': None, 'parent': None,
                 'children': [{'eId': 'unp_1', 'text': f'W ustawie nr {n} stosuje się przepisy {citation}.',
                               'amendment': None}]}
                for n in range(1, 9)]
    assert check(_doc(articles=articles, chapters=[])) == []


def test_metadata():
    doc = _doc(meta={'jurisdiction': 'XX', 'language': None, 'version': 'original', 'source': 'x',
                     'version_date': '21.06.2018'})
    assert {p.where for p in _errors(doc)} == {'meta.language', 'meta.version_date'}


def test_counts():
    assert counts(_doc()) == {'divisions': 1, 'articles': 1, 'paragraphs': 1, 'annexes': 0, 'amendments': 0,
                              'recitals': 0, 'characters': len('Data Protection ActThe Parliament enacts:Chapter 1'
                                                               'General1.Scope(1) This Act applies to data.')}
