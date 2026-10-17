"""
Parser for Lithuanian legislation in the HTML of the Register of Legal Acts.

The Register of Legal Acts (Teisės aktų registras, TAR) publishes each act,
and each consolidated version of it, as HTML exported from Word; the Seimas
portal e-seimas.lrs.lt serves it at /rs/legalact/TAD/<id>/ (the act) and
/rs/actualedition/<id>/<version>/ (a consolidated version). Paragraphs
(``p.MsoNormal``) carry the text line by line:

- the title in capitals ('LIETUVOS RESPUBLIKOS ... ĮSTATYMAS'), its date and
  number ('2018 m. birželio 30 d. Nr. XIII-1426') and place give the preface;
  an introduction ('Vadovaudamasi ..., Lietuvos Respublikos Vyriausybė
  nutaria:') the formula, other opening text the recitals;
- SKYRIUS, SKIRSNIS, DALIS and KNYGA headings become divisions;
- each article ('1 straipsnis. Įstatymo paskirtis') becomes an article; its
  parts ('1. ...') become par_N, with points ('1) ...') folded in. Acts
  without articles (Government resolutions, orders) are read point by point;
- text quoted by an amendment („...“) stays in the amending article, which
  carries a structured ``amendment``;
- the promulgation and signatures ('Skelbiu šį ... įstatymą.') become the
  conclusions, the attachments (priedai, approved rules) the annexes.

The editorial notes of consolidated versions (amendment references in small
italics, the list of amendments at the end) are left out. Superscript
numbers ('7<sup>1</sup> straipsnis') are written as superscript digits ('7¹').
"""
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

_SUPERSCRIPT = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
_FROM_SUPERSCRIPT = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹', '0123456789')
_SUP = '⁰¹²³⁴⁵⁶⁷⁸⁹'
_DATE = re.compile(r'^\d{4} m\. [a-ząčęėįšųūž]+ \d{1,2} d\.(?: Nr\. (?P<number>\S+))?$')
_DIVISION = re.compile(r'^(?P<num>[IVXLC]+|[A-ZĄČĘĖĮŠŲŪŽ]+(?:OJI|ASIS|OSIS|ASIS))\s+'
                       r'(?P<kind>SKYRIUS|SKIRSNIS|DALIS|KNYGA|POSKYRIS|TITULAS)$')
_ARTICLE = re.compile(rf'^(?P<num>\d+[{_SUP}]*)\s+straipsnis\.\s*(?P<heading>.*)$')
_PART = re.compile(rf'^(?P<num>\d+[{_SUP}]*)\.\s')
_POINT = re.compile(rf'^(?P<num>\d+[{_SUP}]*(?:\.\d+[{_SUP}]*)*)\.\s')
_ITEM = re.compile(rf'^\d+[{_SUP}]*\)\s')
_FORMULA = re.compile(r'(nutaria|įsakau|nusprendžia|nutariu|tvirtinu|nutarė|priima šį įstatymą)\s*:$', re.IGNORECASE)
_CLOSING = re.compile(r'^(Skelbiu|Respublikos Prezident|RESPUBLIKOS PREZIDENT|Ministr\w* Pirminink|'
                      r'MINISTR\w* PIRMININK|Seimo Pirminink|SEIMO PIRMININK)')
_ANNEX = re.compile(r'^(PATVIRTINTA\b|(?:\d+ )?priedas$|.{0,80}\b(?:įstatymo|nutarimo|įsakymo|taisyklių|aprašo) '
                    r'(?:\d+ )?priedas$)')
_NOTE_LINE = re.compile(r'^(Suvestinė redakcija nuo|TAR pastaba|Pakeitimai:)')
# Ordinal numbers of divisions ('PIRMASIS SKIRSNIS', 'ANTROJI DALIS'), by their first five letters
ORDINALS = {'PIRMA': 1, 'PIRMO': 1, 'ANTRA': 2, 'ANTRO': 2, 'TREČI': 3, 'KETVI': 4, 'PENKT': 5, 'ŠEŠTA': 6, 'ŠEŠTO': 6,
            'SEPTI': 7, 'AŠTUN': 8, 'DEVIN': 9, 'DEŠIM': 10}
DIVISIONS = {'KNYGA': 'part', 'DALIS': 'part', 'TITULAS': 'title', 'SKYRIUS': 'chapter', 'POSKYRIS': 'chapter',
             'SKIRSNIS': 'section'}

# Amending phrases, checked in order
ACTIONS = (
    (r'[Pp]ripažinti netekusi\w* galios|[Ii]šbraukti', 'delete'),
    (r'[Pp]apildyti', 'add'),
    (r'išdėstyti (?:taip|jį taip|ją taip|juos taip|jas taip)|[Pp]akeisti', 'replace'),
)


def amendment_action(text: str) -> Optional[str]:
    """'Pakeisti 35 straipsnio 2 dalį ir ją išdėstyti taip:' -> 'replace'; 'Papildyti ...' -> 'add'."""
    for pattern, action in ACTIONS:
        if re.search(pattern, text):
            return action
    return None


def _token(number: str) -> str:
    """'7¹' -> '7-1', '1.2' -> '1-2'."""
    head = number.rstrip(_SUP)
    tail = number[len(head):].translate(_FROM_SUPERSCRIPT)
    return head.replace('.', '-') + (f'-{tail}' if tail else '')


def _is_note(paragraph: etree._Element) -> bool:
    """An editorial note of a consolidated version: all its text in small italics."""
    texts = [t for t in paragraph.xpath('.//text()') if t.strip()]
    if not texts:
        return False
    for text in texts:
        parent = text.getparent()
        if not parent.xpath('ancestor-or-self::i'):
            return False
    return 'font-size:10.0pt' in html.tostring(paragraph, encoding='unicode').replace(' ', '')


def _text(paragraph: etree._Element) -> str:
    copy = html.fromstring(html.tostring(paragraph, encoding='unicode'))
    for sup in copy.xpath('.//sup'):
        sup.text = (sup.text or '').translate(_SUPERSCRIPT)
    for br in copy.xpath('.//br'):
        br.tail = ' ' + (br.tail or '')
    text = ' '.join(copy.text_content().split())
    # A superscript set apart from its number ('7 ¹')
    return re.sub(rf'(\d) ([{_SUP}]+)', r'\1\2', text)


def _lines(root: etree._Element) -> list[tuple[str, bool]]:
    """The lines of the act, and whether each is centred, without the editorial notes."""
    lines = []
    for paragraph in root.xpath('//body//p'):
        text = _text(paragraph)
        if not text or set(text) <= set('_ '):
            continue
        if text == 'Pakeitimai:':
            # The list of amending acts closes a consolidated version
            break
        if _is_note(paragraph) or _NOTE_LINE.match(text):
            continue
        centred = 'center' in (paragraph.get('style') or '') or paragraph.get('align') == 'center'
        lines.append((text, centred))
    return lines


class TARParser(Parser):
    """Parses a Lithuanian act (Register of Legal Acts HTML) into legalJSON."""

    def parse(self, file: str, **options) -> 'TARParser':
        try:
            root = html.parse(file, html.HTMLParser(encoding='utf-8')).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read TAR document {file}: {e}") from e
        lines = _lines(root) if root is not None else []
        if not lines:
            raise FileLoadError(f"{file} holds no act text")
        texts = [text for text, _ in lines]
        self.articled = any(_ARTICLE.match(text) for text in texts)
        start = self._read_front(lines)
        self._read_body(texts[start:])
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _starts_body(self, text: str) -> bool:
        if _DIVISION.match(text) or _ARTICLE.match(text):
            return True
        return not self.articled and bool(re.match(r'^1\.\s', text))

    def _read_front(self, lines: list[tuple[str, bool]]) -> int:
        """Title, date, number and place, and the opening; returns where the body starts."""
        first = next((i for i, (text, _) in enumerate(lines) if self._starts_body(text)), len(lines))
        title: list[str] = []
        recitals: list[str] = []
        i = 0
        while i < first and lines[i][1] and not _DATE.match(lines[i][0]):
            title.append(lines[i][0])
            i += 1
        if i < first and _DATE.match(lines[i][0]):
            title.append(lines[i][0])
            i += 1
            # The place of adoption
            if i < first and len(lines[i][0].split()) <= 2:
                title.append(lines[i][0])
                i += 1
        # Letter-spaced words of the title ('Į S T A T Y M A S') are written together
        self.preface = re.sub(r'(?<!\S)((?:[A-ZĄČĘĖĮŠŲŪŽ] ){2,}[A-ZĄČĘĖĮŠŲŪŽ])(?!\S)',
                              lambda m: m.group(1).replace(' ', ''), ' '.join(title)) or None
        for text, _ in lines[i:first]:
            if _FORMULA.search(text):
                self.formula = text
            else:
                recitals.append(text)
        self.recitals = [{'eId': f'rct_{n}', 'text': text} for n, text in enumerate(recitals, start=1)]
        return first

    def _read_body(self, lines: list[str]) -> None:
        body = BodyBuilder()
        article: Optional[dict[str, Any]] = None
        division: Optional[dict[str, Any]] = None
        annex: Optional[dict[str, Any]] = None
        closing: list[str] = []
        quoting = 0
        amended_act: Optional[str] = None
        if self.preface:
            # The act an amending act names in its title ('... ĮSTATYMO NR. I-1374 ... PAKEITIMO ĮSTATYMAS')
            match = re.search(r'(LIETUVOS RESPUBLIKOS .+? NR\. [\w-]+)', self.preface.upper())
            if match and 'PAKEITIMO' in self.preface.upper():
                amended_act = match.group(1)

        def flush() -> None:
            nonlocal article
            if article is not None:
                body.article(article['num'], article['heading'], article['children'].children,
                             token=article['token'])
            article = None

        def add(text: str) -> None:
            children = article['children']
            match = _PART.match(text) if self.articled else _POINT.match(text)
            if match and self.articled:
                child = children.add(text, number=match.group('num'), token=_token(match.group('num')))
            elif match:
                child = children.add(text, number=match.group('num'), token=_token(match.group('num')))
            elif children.children and _ITEM.match(text):
                children.extend(text)
                return
            else:
                child = children.add(text)
            action = amendment_action(text)
            if action and (text.rstrip().endswith(':') or re.search(r'[Pp]ripažinti|[Pp]akeisti|[Pp]apildyti', text)):
                child['amendment'] = {'action': action, 'instruction': text, 'amended_act': amended_act,
                                      'quoted': []}

        for i, text in enumerate(lines):
            if quoting:
                children = article['children']
                current = children.children[-1] if children.children else None
                if current is not None and current.get('amendment') is not None:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': text.strip('„“')})
                children.extend(text)
                quoting = max(quoting + text.count('„') - text.count('“'), 0)
                continue
            if annex is not None:
                if _ANNEX.match(text) and annex['children'].children:
                    annex = self._annex(text)
                    continue
                if annex['heading'] is None and not annex['children'].children:
                    # The reference to the act ('... įstatymo priedas') over several lines, then the heading
                    if text == text.upper() and re.search(r'[A-ZĄČĘĖĮŠŲŪŽ]{3}', text):
                        annex['heading'] = text
                        self.annexes[-1]['heading'] = text
                    else:
                        self.annexes[-1]['num'] = f"{self.annexes[-1]['num']} {text}"
                else:
                    annex['children'].add(text)
                continue
            if _ANNEX.match(text) and (article is not None or body.articles or closing):
                # An attachment: approved rules ('PATVIRTINTA ...') or an annex ('... priedas')
                flush()
                annex = self._annex(text)
                continue
            if closing:
                # Signatures, and who prepared the act; then an annex whose reference to the act runs over
                # several lines ('Lietuvos Respublikos / ... įstatymo / priedas')
                ahead = lines[i:i + 5]
                end = next((n for n, line in enumerate(ahead) if re.search(r'\bpriedas$', line)), None)
                numbered = any(re.search(r'\d', line) for line in ahead[:end or 0])
                if end is not None and not _CLOSING.match(text) and not numbered:
                    annex = self._annex(text)
                else:
                    closing.append(text)
                continue
            if (article is not None or body.articles) and (_CLOSING.match(text) or self._signature(text)):
                flush()
                closing.append(text)
                continue
            if text.startswith('„') and article is not None:
                children = article['children']
                current = children.children[-1] if children.children else None
                if current is not None and current.get('amendment') is not None:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': text.strip('„“')})
                children.extend(text)
                quoting = max(text.count('„') - text.count('“'), 0)
                continue
            match = _DIVISION.match(text)
            if match:
                flush()
                number = match.group('num')
                token = str(ORDINALS[number[:5]]) if number[:5] in ORDINALS else number
                division = body.division(DIVISIONS[match.group('kind')], text, token=token)
                continue
            if division is not None and article is None and text == text.upper():
                division['heading'] = f"{division['heading']} {text}" if division.get('heading') else text
                continue
            division = None
            match = _ARTICLE.match(text)
            if match:
                flush()
                article = {'num': f"{match.group('num')} straipsnis", 'heading': match.group('heading') or None,
                           'token': _token(match.group('num')), 'children': ChildrenBuilder()}
                continue
            match = re.match(r'^(?P<num>\d+)\.\s', text)
            if not self.articled and match and (article is None or '.' not in match.group('num')):
                # A point of an act without articles
                flush()
                article = {'num': f"{match.group('num')}.", 'heading': None, 'token': match.group('num'),
                           'children': ChildrenBuilder()}
                add(text[match.end():])
                quoting = max(text.count('„') - text.count('“'), 0)
                continue
            if article is None:
                continue
            add(text)
            quoting = max(text.count('„') - text.count('“'), 0)
        flush()
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        if closing:
            self.conclusions = {'conclusion_text': closing[0], 'signature': ' '.join(closing[1:]) or None}

    def _signature(self, text: str) -> bool:
        """In an act without articles, a signature: a short line naming a position and a person."""
        if self.articled or re.match(r'^(\d|„|\()', text) or text[-1:] in '.;:,':
            return False
        return len(text) < 100 and bool(re.search(r'[A-ZĄČĘĖĮŠŲŪŽ][a-ząčęėįšųūž]+ [A-ZĄČĘĖĮŠŲŪŽ][a-ząčęėįšųūž]+$',
                                                  text))

    def _annex(self, text: str) -> dict[str, Any]:
        children = ChildrenBuilder()
        annex = {'heading': None, 'children': children}
        self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': text, 'heading': None,
                             'children': children.children})
        return annex
