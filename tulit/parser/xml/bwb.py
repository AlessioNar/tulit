"""
Parser for consolidated Dutch legislation in the BWB toestand XML format.

- ``intitule`` gives the preface; the royal formula (``wij``), the
  considerations (``considerans.al``) and the enacting clause
  (``afkondiging``) give the preamble;
- divisions (boek, deel, titeldeel, hoofdstuk, afdeling, paragraaf) become
  typed divisions;
- each ``artikel`` becomes an article; its numbered paragraphs (``lid``)
  become par_N, with lists folded into their paragraph;
- the closing formula, date and signatures (``wetsluiting``) give the
  conclusions, and ``bijlage`` elements the annexes;
- ``meta-data`` blocks are left out.
"""
import re
from typing import Any, Optional

from lxml import etree

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, element_text, eid_token

BLOCK_TAGS = ('al', 'lid', 'lidnr', 'lijst', 'li', 'li.nr', 'kop', 'label', 'nr', 'titel',
              'tabel', 'row', 'entry', 'considerans.al', 'ondertekening', 'functie', 'naam')
SKIP_TAGS = ('meta-data', 'jcis', 'jci')

DIVISIONS = {
    'boek': 'part',
    'deel': 'part',
    'titeldeel': 'title',
    'hoofdstuk': 'chapter',
    'afdeling': 'section',
    'paragraaf': 'subsection',
    'sub-paragraaf': 'subparagraph',
}


def _text(element: Optional[etree._Element], skip: tuple = ()) -> str:
    if element is None:
        return ''
    return element_text(element, BLOCK_TAGS, SKIP_TAGS + skip)


class BWBParser(Parser):
    """Parses a BWB toestand XML document into legalJSON."""

    def parse(self, file: str, **options) -> 'BWBParser':
        try:
            self.root = etree.parse(file).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read BWB document {file}: {e}") from e

        self.get_preface()
        self._read_preamble()
        body = BodyBuilder()
        text = self.root.find('.//wettekst')
        if text is not None:
            self._walk(text, body)
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        self._read_conclusions()
        self._read_annexes()
        return self

    def get_preface(self) -> Optional[str]:
        self.preface = _text(self.root.find('.//intitule')) or _text(self.root.find('.//citeertitel')) or None
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read_preamble(self) -> None:
        opening = self.root.find('.//wet-besluit/aanhef')
        if opening is None:
            return
        self.formula = _text(opening.find('wij')) or None
        self.recitals = [
            {'eId': f'rct_{position}', 'text': _text(paragraph)}
            for position, paragraph in enumerate(opening.iter('considerans.al'), start=1)
            if _text(paragraph)
        ]
        self.preamble_final = _text(opening.find('afkondiging')) or None

    def _walk(self, element: etree._Element, body: BodyBuilder) -> None:
        for child in element:
            if not isinstance(child.tag, str):
                continue
            if child.tag in DIVISIONS:
                heading = child.find('kop')
                body.division(
                    DIVISIONS[child.tag],
                    child.get('label') or _text(heading, skip=('titel',)) or None,
                    heading=(_text(heading.find('titel')) or None) if heading is not None else None,
                    token=_number(child),
                )
                self._walk(child, body)
            elif child.tag == 'artikel':
                self._read_article(child, body)

    def _read_article(self, article: etree._Element, body: BodyBuilder) -> None:
        children = ChildrenBuilder()
        for block in article:
            if not isinstance(block.tag, str) or block.tag in ('kop',) + SKIP_TAGS:
                continue
            text = _text(block)
            if not text:
                continue
            if block.tag == 'lid':
                children.add(text, number=block.findtext('lidnr'))
            elif block.tag == 'lijst' and children.children:
                children.extend(text)
            else:
                children.add(text)
        heading = article.find('kop')
        body.article(
            article.get('label') or _text(heading, skip=('titel',)) or None,
            (_text(heading.find('titel')) or None) if heading is not None else None,
            children.children,
            token=_number(article),
        )

    def _read_conclusions(self) -> None:
        closing = self.root.find('.//wet-besluit/wetsluiting')
        if closing is None:
            self.conclusions = None
            return
        given = closing.find('gegeven')
        signatories = [_text(given.find('koning'))] if given is not None and given.find('koning') is not None else []
        signatories += [_text(s) for s in closing.findall('ondertekening') if _text(s)]
        date = closing.find('gegeven/dagtekening/datum')
        text = ' '.join(filter(None, [_text(closing.find('slotformulering')),
                                      _text(closing.find('uitgifte'))]))
        self.conclusions = {
            'conclusion_text': text,
            'signature': {
                'place': closing.findtext('gegeven/dagtekening/plaats'),
                'date': (date.get('isodatum') or _text(date)) if date is not None else None,
                'signatory': signatories[0] if signatories else None,
                'title': None,
                'signatories': signatories,
            },
        }

    def _read_annexes(self) -> None:
        self.annexes = []
        for position, annex in enumerate(self.root.iter('bijlage'), start=1):
            heading = annex.find('kop')
            children = ChildrenBuilder()
            for block in annex:
                if isinstance(block.tag, str) and block.tag not in ('kop',) + SKIP_TAGS:
                    text = _text(block)
                    if text:
                        children.add(text)
            self.annexes.append({
                'eId': f'anx_{_number(annex) or position}',
                'num': annex.get('label') or _text(heading, skip=('titel',)) or None,
                'heading': (_text(heading.find('titel')) or None) if heading is not None else None,
                'children': children.children,
            })


def _number(element: etree._Element) -> Optional[str]:
    """
    The published number of a division or article, for its eId.

    Dotted numbers keep all their parts ('2.1' -> '2-1', '420bis.1' -> '420bis-1').
    """
    heading = element.find('kop')
    number = (heading.findtext('nr') or '').strip() if heading is not None else ''
    if not number:
        label = element.get('label') or ''
        number = label.split()[-1] if label.split() else ''
    if re.fullmatch(r'[0-9A-Za-z]+(\.[0-9A-Za-z]+)+\.?', number):
        return number.rstrip('.').replace('.', '-')
    return eid_token(number)
