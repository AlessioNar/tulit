"""
Checks that a legalJSON document is well formed beyond its schema.

The schema says which fields exist and what type they have; these checks
look at what a parser can get wrong while still producing schema-valid
output: duplicate or dangling identifiers, empty articles, markup or page
furniture left in the text, malformed amendments, missing metadata.

>>> from tulit.quality import check
>>> problems = check(tulit.fetch("32024R0903"))
>>> [p for p in problems if p.severity == "error"]
[]
"""
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterator

ERROR = 'error'
WARNING = 'warning'

ACTIONS = {'replace', 'insert', 'add', 'delete', 'amend', 'repeal', 'renumber', 'substitute'}
_MARKUP = re.compile(r'<\s*/?\s*[a-zA-Z][a-zA-Z0-9:_-]*(\s[^<>]*)?/?>|&(?:[a-zA-Z]{2,8}|#\d{2,5}|#x[0-9a-fA-F]{2,4});')
_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_ABBREVIATION = re.compile(r'\b[^\W\d_]{1,3}\.$')
_BAD_CHARACTERS = re.compile(r'[�\x00-\x08\x0b\x0c\x0e-\x1f]')


@dataclass(frozen=True)
class Problem:
    """One thing wrong with a document: its severity, where it is (an eId or field) and what is wrong."""
    severity: str
    where: str
    message: str

    def __str__(self) -> str:
        return f'{self.severity}: {self.where}: {self.message}'


def _texts(doc: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Every text of the document with where it is."""
    if doc.get('preface'):
        yield 'preface', doc['preface']
    preamble = doc.get('preamble') or {}
    for key in ('formula', 'recitals_intro', 'final'):
        if preamble.get(key):
            yield f'preamble.{key}', preamble[key]
    for key in ('citations', 'recitals'):
        for item in preamble.get(key) or []:
            yield item.get('eId') or f'preamble.{key}', item.get('text') or ''
    for chapter in doc.get('chapters') or []:
        for key in ('num', 'heading'):
            if chapter.get(key):
                yield chapter['eId'], chapter[key]
    for article in doc.get('articles') or []:
        for key in ('num', 'heading'):
            if article.get(key):
                yield article['eId'], article[key]
        for child in article.get('children') or []:
            yield f"{article['eId']}/{child.get('eId')}", child.get('text') or ''
    for annex in doc.get('annexes') or []:
        for child in annex.get('children') or []:
            yield f"{annex.get('eId')}/{child.get('eId')}", child.get('text') or ''


def check(doc: dict[str, Any], expect_articles: bool = True) -> list[Problem]:
    """
    The problems found in a legalJSON document, errors first.

    ``expect_articles``: whether the act should have articles (False for an
    act that is repealed, or published without a text).
    """
    problems: list[Problem] = []

    def add(severity: str, where: str, message: str) -> None:
        problems.append(Problem(severity, where, message))

    if not (doc.get('preface') or '').strip():
        add(ERROR, 'preface', 'the act has no title')

    chapters = doc.get('chapters') or []
    articles = doc.get('articles') or []
    if expect_articles and not articles:
        add(ERROR, 'articles', 'the act has no articles')

    # Identifiers: unique, and parents that exist
    chapter_ids = Counter(c.get('eId') for c in chapters)
    for eid, count in chapter_ids.items():
        if count > 1:
            add(ERROR, eid, f'{count} divisions share this eId')
    article_ids = Counter(a.get('eId') for a in articles)
    for eid, count in article_ids.items():
        if count > 1:
            add(ERROR, eid, f'{count} articles share this eId')
    for chapter in chapters:
        if chapter.get('parent') and chapter['parent'] not in chapter_ids:
            add(ERROR, chapter['eId'], f"its parent {chapter['parent']} is not a division")
    for article in articles:
        eid = article.get('eId')
        if article.get('parent') and article['parent'] not in chapter_ids:
            add(ERROR, eid, f"its parent {article['parent']} is not a division")
        if not (article.get('num') or '').strip():
            add(WARNING, eid, 'the article has no number')
        children = article.get('children') or []
        if not children:
            add(WARNING, eid, 'the article has no text (repealed?)')
        child_ids = Counter(c.get('eId') for c in children)
        for child_id, count in child_ids.items():
            if count > 1:
                add(ERROR, f'{eid}/{child_id}', f'{count} paragraphs share this eId')
        for child in children:
            if not (child.get('text') or '').strip():
                add(ERROR, f"{eid}/{child.get('eId')}", 'the paragraph is empty')
            amendment = child.get('amendment')
            if amendment:
                where = f"{eid}/{child.get('eId')}"
                if amendment.get('action') not in ACTIONS:
                    add(ERROR, where, f"unknown amendment action {amendment.get('action')!r}")
                if not (amendment.get('instruction') or '').strip():
                    add(ERROR, where, 'the amendment has no instruction')
                for quoted in amendment.get('quoted') or []:
                    if not (quoted.get('text') or quoted.get('children')):
                        add(WARNING, where, 'an amendment quotes nothing')

    # The text itself: markup, broken characters, padding
    for where, text in _texts(doc):
        if _MARKUP.search(text):
            add(ERROR, where, f'markup left in the text: {_MARKUP.search(text).group(0)!r}')
        if _BAD_CHARACTERS.search(text):
            add(ERROR, where, 'broken or control characters in the text')
        if text != text.strip():
            add(WARNING, where, 'the text has leading or trailing spaces')

    # Page furniture (running headers, footers) repeated across articles; amending
    # provisions repeat their formulas ('... helyébe a következő alcím lép:')
    lines: Counter = Counter()
    for article in articles:
        seen = set()
        for child in article.get('children') or []:
            if child.get('amendment'):
                continue
            cut = False
            for sentence in re.split(r'(?<=[.;:])\s+', child.get('text') or ''):
                # Pieces cut at an abbreviation ('(Dz.', 'str.', 'Z. z.') are parts of a citation, not a header
                cut, after_cut = bool(_ABBREVIATION.search(sentence)), cut
                if len(sentence) >= 25 and sentence not in seen and not cut and not after_cut:
                    seen.add(sentence)
                    lines[sentence] += 1
    threshold = max(5, len(articles) // 4)
    for sentence, count in lines.most_common(3):
        if count >= threshold and not re.search(r'\d', sentence[:3]):
            add(WARNING, 'articles', f'the same text recurs in {count} articles (page header?): {sentence[:60]!r}')

    meta = doc.get('meta')
    if meta is not None:
        for key in ('jurisdiction', 'language', 'version', 'source'):
            if not meta.get(key):
                add(ERROR, f'meta.{key}', 'missing')
        for key in ('version_date', 'date_document', 'date_publication', 'date_in_force'):
            value = meta.get(key)
            if value and not _DATE.match(str(value)):
                add(ERROR, f'meta.{key}', f'not an ISO date: {value!r}')

    order = {ERROR: 0, WARNING: 1}
    return sorted(problems, key=lambda p: order[p.severity])


def counts(doc: dict[str, Any]) -> dict[str, int]:
    """Size of a document: divisions, articles, paragraphs, annexes, amendments, recitals and characters."""
    articles = doc.get('articles') or []
    children = [c for a in articles for c in a.get('children') or []]
    return {
        'divisions': len(doc.get('chapters') or []),
        'articles': len(articles),
        'paragraphs': len(children),
        'annexes': len(doc.get('annexes') or []),
        'amendments': sum(1 for c in children if c.get('amendment')),
        'recitals': len((doc.get('preamble') or {}).get('recitals') or []),
        'characters': sum(len(text) for _, text in _texts(doc)),
    }
