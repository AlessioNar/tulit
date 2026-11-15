"""
Live checks of every act in the corpus (``tests/corpus/acts/<code>.json``).

Each act is fetched from its official source and must pass the generic
checks of ``tulit.quality`` (no errors) and its own expectations: the title,
and the number of articles, divisions, annexes and amendments, checked by
hand against the official text when the act was added.

An entry::

    {"identifier": "300099", "version": "original", "date": null,
     "options": {}, "kind": "law", "title": "Fizisko personu datu apstrādes likums",
     "expect": {"articles": 37, "divisions": 8, "annexes": 1, "amendments": false,
                "version_date": "2018-06-21"},
     "note": "Data protection law, as published in Latvijas Vēstnesis"}

A number in ``expect`` is exact, a pair [min, max] a range; ``amendments``
true means at least one structured amendment, false none.
"""
import json
import time
from pathlib import Path

import pytest

import tulit
from tulit.parser.exceptions import NetworkError
from tulit.quality import ERROR, check, counts

from .conftest import RESULTS

ACTS = Path(__file__).parent / 'acts'


def _entries():
    for path in sorted(ACTS.glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        for act in data['acts']:
            yield pytest.param(data['jurisdiction'], act,
                               id=f"{data['jurisdiction']}:{act.get('version') or 'default'}:{act['identifier'][:60]}")


def _matches(expected, actual) -> bool:
    if isinstance(expected, bool):
        return bool(actual) == expected
    if isinstance(expected, list):
        return expected[0] <= actual <= expected[1]
    return actual == expected


@pytest.mark.corpus
@pytest.mark.parametrize('jurisdiction, act', list(_entries()))
def test_act(jurisdiction, act, corpus_dir, request):
    only = request.config.getoption('--corpus-jurisdiction')
    if only and jurisdiction not in only:
        pytest.skip(f'only {", ".join(only)}')
    result = {'jurisdiction': jurisdiction, 'identifier': act['identifier'], 'version': act.get('version'),
              'kind': act.get('kind'), 'status': 'error'}
    RESULTS.append(result)
    started = time.monotonic()

    def fetch():
        return tulit.fetch(act['identifier'], jurisdiction=jurisdiction, version=act.get('version'),
                           date=act.get('date'), language=act.get('language'),
                           download_dir=str(corpus_dir / jurisdiction), **(act.get('options') or {}))

    try:
        try:
            doc = fetch()
        except NetworkError:
            # Some sources (Normattiva, e-seimas) drop connections in bursts: try once more after a pause
            time.sleep(60)
            doc = fetch()
    except Exception as e:
        result['failure'] = f'{type(e).__name__}: {e}'
        raise
    finally:
        result['seconds'] = round(time.monotonic() - started, 1)

    expect = act.get('expect') or {}
    size = counts(doc)
    problems = check(doc, expect_articles=expect.get('articles') != 0)
    result.update(counts=size, problems=[str(p) for p in problems])

    failures = [str(p) for p in problems if p.severity == ERROR]
    if act.get('title') and act['title'].casefold() not in (doc.get('preface') or '').casefold():
        failures.append(f"title {act['title']!r} not in preface {doc.get('preface')!r}")
    for key in ('divisions', 'articles', 'annexes', 'amendments', 'recitals'):
        if key in expect and not _matches(expect[key], size[key]):
            failures.append(f'{key}: expected {expect[key]}, got {size[key]}')
    if 'version_date' in expect and doc['meta'].get('version_date') != expect['version_date']:
        failures.append(f"version_date: expected {expect['version_date']}, got {doc['meta'].get('version_date')}")
    result['status'] = 'fail' if failures else 'pass'
    result['failures'] = failures
    assert not failures, '\n'.join(failures)
