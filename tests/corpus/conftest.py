"""
The corpus: at least ten real acts per jurisdiction, fetched live from their official sources.

Off by default. Run it with ``pytest tests/corpus --corpus``; downloads are kept in
``TULIT_CORPUS_DIR`` (default ``.corpus``) so a second run reads them again
instead of downloading, and the results are written to ``<dir>/report.json``.
"""
import json
import os
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption('--corpus', action='store_true', default=False,
                     help='run the live corpus of real acts against the official sources')
    parser.addoption('--corpus-jurisdiction', action='append', default=[],
                     help='only run the corpus of these jurisdictions (repeatable), e.g. --corpus-jurisdiction LV')


def pytest_collection_modifyitems(config, items):
    if config.getoption('--corpus'):
        return
    skip = pytest.mark.skip(reason='live corpus: run with --corpus')
    for item in items:
        if 'corpus' in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope='session')
def corpus_dir() -> Path:
    path = Path(os.environ.get('TULIT_CORPUS_DIR', '.corpus'))
    path.mkdir(parents=True, exist_ok=True)
    return path


RESULTS: list[dict] = []


def pytest_sessionfinish(session, exitstatus):
    if not RESULTS:
        return
    path = Path(os.environ.get('TULIT_CORPUS_DIR', '.corpus')) / 'report.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(RESULTS, key=lambda r: (r['jurisdiction'], r['identifier'])),
                               ensure_ascii=False, indent=2), encoding='utf-8')
