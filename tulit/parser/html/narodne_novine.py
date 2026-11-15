"""
Parser for Croatian legislation in the HTML of Narodne novine (the Official Gazette).

Narodne novine publishes each act as typeset HTML: one ``p`` per line,
with typographic classes (``T-9-8`` body text, ``Clanak`` article numbers,
``T-10-9-kurz-S`` italic headings, ``T-11-9-sred`` centred headings). The
classes vary over the years, so the structure is read mostly from the text:

- the page title gives the preface; the promulgation decision of a law
  (Odluka o proglašenju) gives the formula, the legal basis of other acts
  ('Na temelju članka ...') the citations;
- 'DIO' headings become parts, 'GLAVA' and Roman-numbered headings
  chapters, 'Odjeljak' headings sections;
- each 'Članak N.' becomes an article, the italic line above it its
  heading; numbered paragraphs '(1)' become par_N, with lists folded in;
- amending provisions ('... mijenja se i glasi:', '... briše se') carry a
  structured ``amendment`` with the quoted text (»...«);
- older items label divisions on a line of their own ('Dio prvi',
  'Glava I.', 'Odjeljak 1.', 'Odsjek 1.') with the title on the next line;
  the lines between a division and the next article are read as division
  titles (upper case) or as the article heading;
- the reference, place, date and signature after the last article become
  the conclusions, and each 'PRILOG' after them an annex.
"""
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, element_text

# Digits misread as I or l in scanned items ('Članak I35.')
_ARTICLE = re.compile(r'^Članak\s+(?P<number>(?-i:[\dIl]*\d[\dIl]*)\s?\.?\s?[a-z]?)\.?$', re.IGNORECASE)
_PARAGRAPH = re.compile(r'^\((?P<number>\d+[a-z]?)\)\s')
_ROMAN = re.compile(r'^(?P<number>[IVXLC]+)\.\s+\S')
_GLAVA = re.compile(r'^GLAVA\b.*?\((?P<number>[IVXLC]+)\.?\)|^GLAVA\s+(?P<word>[IVXLC]+)\b', re.IGNORECASE)
_DIO = re.compile(r'^DIO\s+(?P<after>\w+)|^(?:(?P<ordinal>\w+)\s+)?DIO\b|\bDIO$', re.IGNORECASE)
_POGLAVLJE = re.compile(r'^POGLAVLJE\s+(?P<number>[IVXLC]+|\d+)\b', re.IGNORECASE)
_ODJELJAK = re.compile(r'^(?P<number>\d+)\.\s*Odjeljak\b|^Odjeljak\s+(?P<number2>\d+)', re.IGNORECASE)
_LABEL = re.compile(r'^(?:(?P<part>Dio)\s+\w+|(?P<chapter>Glava)\s+[IVXLC]+|(?P<section>Odjeljak)\s+\d+'
                    r'|(?P<subsection>Odsjek)\s+\d+)\.?$', re.IGNORECASE)
_NUMBERED = re.compile(r'^(?P<number>\d+)\.\s+\S')
_LIST = re.compile(r'^(?:[-–•]|\d+\)|[a-z]\))\s')
_ANNEX = re.compile(r'^PRILOG\b', re.IGNORECASE)
# An opening quote, except the one of the gazette's name in citations
_QUOTE = re.compile(r'»(?!Narodne novine«)')
_AMENDED_ACT = re.compile(r'^U\s+(?P<act>(?:Zakonu|Uredbi|Pravilniku|Odluci|Naredbi|Kaznenom zakonu)\b.*?)'
                          r'\s*\(\s*»Narodne novine«')
ORDINALS = {'prvi': '1', 'drugi': '2', 'treći': '3', 'četvrti': '4', 'peti': '5', 'šesti': '6',
            'sedmi': '7', 'osmi': '8', 'deveti': '9', 'deseti': '10',
            'opći': 'opci', 'posebni': 'posebni', 'završni': 'zavrsni'}

# Amending verbs, checked in order
ACTIONS = (
    ('mijenja se i glasi', 'replace'), ('mijenjaju se i glase', 'replace'), ('zamjenjuje se', 'replace'),
    ('zamjenjuju se', 'replace'), ('briše se', 'delete'), ('brišu se', 'delete'),
    ('iza ', 'insert'), ('ispred ', 'insert'), ('dodaje se', 'add'), ('dodaju se', 'add'),
)


def amendment_action(instruction: str) -> Optional[str]:
    """'Članak 5. mijenja se i glasi:' -> 'replace'; 'Iza članka 5. dodaje se članak 5.a' -> 'insert'."""
    lowered = instruction.lower()
    for verb, action in ACTIONS:
        if verb in ('iza ', 'ispred '):
            if lowered.startswith(verb) or f' {verb}' in lowered:
                if 'dodaje' in lowered or 'dodaju' in lowered:
                    return action
            continue
        if verb in lowered:
            return action
    return None


def _classes(element: etree._Element) -> str:
    return ' '.join(c for c in (element.get('class') or '').lower().split() if not c.startswith('box_'))


def _text(element: etree._Element) -> str:
    return element_text(element, ('br',))


class NarodneNovineParser(Parser):
    """Parses an act published in Narodne novine (HTML) into legalJSON."""

    def parse(self, file: str, **options) -> 'NarodneNovineParser':
        try:
            root = html.parse(file, html.HTMLParser(encoding='utf-8')).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read Narodne novine document {file}: {e}") from e
        content = root.xpath('//div[contains(@class, "sl-content")]') if root is not None else []
        if not content:
            raise FileLoadError(f"{file} holds no act text (the act may be published only as PDF)")
        self.preface = ' '.join((root.findtext('.//title') or '').split()) or None
        lines = [(element, _classes(element), _text(element)) for element in content[0].iter('p')]
        lines = [line for line in lines if line[2]]
        self._read(lines)
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read(self, lines: list[tuple[etree._Element, str, str]]) -> None:
        first = next((i for i, line in enumerate(lines) if self._is_structure(line)), len(lines))
        self._read_front(lines[:first])
        lines = lines[first:]
        titles = self._titles([text for _, _, text in lines])
        labelled = any(_LABEL.match(text) for _, _, text in lines)

        body = BodyBuilder()
        children: Optional[ChildrenBuilder] = None
        article: Optional[tuple[str, str, Optional[str]]] = None
        heading: Optional[str] = None
        amended_act: Optional[str] = None
        labelled_division: Optional[dict[str, Any]] = None
        closing: list[str] = []
        annex: Optional[ChildrenBuilder] = None

        def flush() -> None:
            nonlocal article, children
            if article is not None:
                body.article(article[0], article[2], children.children, token=article[1])
            article, children = None, None

        for (element, classes, text), title in zip(lines, titles):
            if closing and (_ANNEX.match(text) or 'prilog' in classes):
                annex = ChildrenBuilder()
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': text, 'heading': None,
                                     'children': annex.children})
                continue
            if annex is not None:
                if self.annexes[-1]['heading'] is None and not annex.children \
                        and (text.isupper() or 'sred' in classes or 'pcenter' in classes):
                    self.annexes[-1]['heading'] = text
                else:
                    annex.add(text)
                continue
            if closing or ('klasa' in classes and article is not None):
                closing.append(text)
                continue
            current = children.children[-1] if children is not None and children.children else None
            if current is not None and current.get('amendment') is not None \
                    and (text.startswith('»') or current['text'].count('»') > current['text'].count('«')):
                # Quoted text of the amendment, up to the closing quote: articles in it are not the act's
                current['amendment']['quoted'].append({'kind': 'text', 'text': re.sub(r'^»|«[.;,]?$', '', text)})
                children.extend(text)
                continue
            previous, labelled_division = labelled_division, None
            if previous is not None and previous['heading'] is None and text.isupper():
                # The title under a 'Glava I.' line
                previous['heading'] = text
                continue
            match = _ARTICLE.match(text)
            if match:
                flush()
                number = re.sub(r'[\s.]', '', match.group('number'))
                digits = re.match(r'[\dIl]+', number).group(0)
                token = digits.replace('I', '1').replace('l', '1') + number[len(digits):]
                article, children = (text, token, heading), ChildrenBuilder()
                heading = None
                continue
            division = self._division(classes, text)
            if division and (article is None or not children.children or 'sred' in classes or title):
                flush()
                body.division(division[0], text, token=division[1])
                continue
            if title and classes in ('', 'msonormal') and not (text.isupper() or _NUMBERED.match(text)):
                # Scanned items have no article headings: a line without a full stop is text
                title = False
            if title:
                flush()
                label = _LABEL.match(text)
                numbered = _NUMBERED.match(text)
                roman = _ROMAN.match(text)
                if label:
                    labelled_division = body.division(label.lastgroup, text)
                elif labelled and ((roman and text.isupper()) or numbered):
                    # Under 'Glava' labels, numbered titles are the lowest level
                    body.division('division', text, token=(roman or numbered).group('number'), rank=5)
                elif roman and text.isupper():
                    body.division('chapter', text, token=roman.group('number'))
                elif numbered:
                    body.division('section', text, token=numbered.group('number'))
                elif text.isupper():
                    body.division('subsection', None, heading=text)
                else:
                    heading = f'{heading} {text}' if heading else text
                continue
            if 'kurz' in classes or ('fett' in classes and article is None):
                # An italic heading belongs to the next article
                flush()
                heading = f'{heading} {text}' if heading else text
                continue
            if children is None and not body.articles and any(titles):
                # Text before the first article: the preamble ('Izvorišne osnove' of the Ustav)
                self.recitals.append({'eId': f'rct_{len(self.recitals) + 1}', 'text': text})
                continue
            if children is None:
                article, children = (None, None, heading), ChildrenBuilder()
                heading = None
            act = _AMENDED_ACT.match(text)
            if act and not children.children:
                amended_act = act.group('act')
            self._add(children, text, amended_act)
        flush()
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        if closing:
            self.conclusions = {'conclusion_text': ' '.join(closing[:-1]) or None, 'signature': closing[-1]}

    @staticmethod
    def _titles(texts: list[str]) -> list[bool]:
        """
        Whether each line is one of the short lines (titles, headings) right above an article.

        A title does not end in punctuation, nor start in lower case (the
        end of a sentence broken over two lines).
        """
        titles = [False] * len(texts)
        run = False
        for i in range(len(texts) - 1, -1, -1):
            text = texts[i]
            if _ARTICLE.match(text):
                run = True
                continue
            title = (len(text) <= 200 and not _PARAGRAPH.match(text) and not _LIST.match(text)
                     and not text[0].islower()
                     and (not text.endswith(('.', ',', ';', ':')) or bool(_LABEL.match(text))))
            run = run and title
            titles[i] = run
        return titles

    def _read_front(self, lines: list[tuple[etree._Element, str, str]]) -> None:
        """Promulgation decision (laws) or legal basis (other acts), before the title."""
        texts = [text for _, classes, text in lines
                 if not any(key in classes for key in ('tb-na18', 'broj-d', 'tb-na16', 'fett'))
                 and not text.isdigit()]
        if any('proglaš' in text.lower() for text in texts):
            self.formula = ' '.join(texts) or None
        else:
            self.citations = [{'eId': f'cit_{n}', 'text': text} for n, text in enumerate(texts, start=1)]

    def _is_structure(self, line: tuple[etree._Element, str, str]) -> bool:
        _, classes, text = line
        return (bool(_ARTICLE.match(text)) or bool(self._division(classes, text)) or 'kurz' in classes
                or bool(_LABEL.match(text)))

    @staticmethod
    def _division(classes: str, text: str) -> Optional[tuple[str, Optional[str]]]:
        if 'sred' not in classes and 'sredina' not in classes and not text.isupper():
            return None
        if 'sredina' in classes:
            return None
        glava = _GLAVA.match(text)
        if glava:
            return 'chapter', glava.group('number') or glava.group('word')
        dio = _DIO.search(text)
        if dio and dio.group('after') and dio.group('after').lower() in ORDINALS:
            # 'DIO DRUGI PRAVO NA ...'
            return 'part', ORDINALS[dio.group('after').lower()]
        if dio and len(text.split()) <= 4:
            ordinal = (dio.group('ordinal') or '').lower()
            return 'part', ORDINALS.get(ordinal, ordinal or None)
        poglavlje = _POGLAVLJE.match(text)
        if poglavlje:
            return 'chapter', poglavlje.group('number')
        odjeljak = _ODJELJAK.match(text)
        if odjeljak:
            return 'section', odjeljak.group('number') or odjeljak.group('number2')
        roman = _ROMAN.match(text)
        if roman and ('sred' in classes or 'msonormal' in classes or not classes):
            return 'chapter', roman.group('number')
        return None

    @staticmethod
    def _add(children: ChildrenBuilder, text: str, amended_act: Optional[str]) -> None:
        current = children.children[-1] if children.children else None
        paragraph = _PARAGRAPH.match(text)
        if paragraph:
            child = children.add(text, number=paragraph.group('number'))
        elif current is not None and (re.match(r'^(\d+\.|[a-z]\)|–|-|•)\s', text) or text.startswith('»')
                                      or text[0].islower()):
            # A list item, a quote, or the end of a sentence after a list ('..., kaznit će se ...')
            children.extend(text)
            return
        else:
            child = children.add(text)
        action = amendment_action(text)
        if action and (text.rstrip().endswith(':') or '»' in text or action == 'delete'):
            child['amendment'] = {'action': action, 'instruction': _QUOTE.split(text, 1)[0].strip(),
                                  'amended_act': amended_act, 'quoted': []}
