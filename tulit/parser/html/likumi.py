"""
Parser for Latvian legislation in the HTML of likumi.lv and vestnesis.lv.

likumi.lv, run by the official publisher Latvijas Vēstnesis, publishes each
act and each of its versions (redakcijas) as HTML with typographic classes:

- ``TV207`` gives the title (preface) and ``TV206`` the enacting formula
  ('Saeima ir pieņēmusi un Valsts prezidents izsludina šādu likumu:');
- ``TV212`` headings ('I nodaļa', then the heading after a line break)
  become divisions: daļa a part, nodaļa a chapter, apakšnodaļa a section;
- each numbered block (``div.TV213[data-num]``) becomes an article: a law's
  'pants', whose first line ('3. pants. Datu valsts inspekcija') gives its
  number and heading, or a regulation's numbered point; paragraphs '(1)'
  become par_N, with sub-points folded into them;
- the transitional provisions (Pārejas noteikumi) and the references to EU
  directives become annexes, the closing lines (adoption, signature) the
  conclusions;
- amendment notes ('(Ar grozījumiem, kas izdarīti ar ...)') are left out.

The official publication in Latvijas Vēstnesis (vestnesis.lv, ``div.docContent``)
is plainer: the enacting formula (``p.lik_c``), the title (``h3``), division
and annex headings (``h4``), and articles opening with a bold line; it is
read the same way.
"""
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, element_text

BLOCK_TAGS = ('p', 'div', 'br', 'li', 'tr', 'td', 'table')
SKIP_CLASSES = ('notify-msg', 'labojumu_pamats', 'panta-doc-npk', 'info-icon-wrapper', 'panta-piezimite', 'court',
                'p_id')
_ARTICLE_LINE = re.compile(r'^(?P<num>\d+\.(?:\s?\d+\.?)?\s*pants)\.?\s*(?P<heading>.*)$')
_PARAGRAPH = re.compile(r'^\((?P<num>\d+(?:\.\d+)?)\)\s')
ORDINALS = ('pirmā', 'otrā', 'trešā', 'ceturtā', 'piektā', 'sestā', 'septītā', 'astotā', 'devītā', 'desmitā',
            'vienpadsmitā', 'divpadsmitā', 'trīspadsmitā', 'četrpadsmitā', 'piecpadsmitā')
_DIVISION = re.compile(r'^(?P<num>[IVXLC]+|\d+|[A-Z]|' + '|'.join(ORDINALS) + r')\.?\s*'
                       r'(?P<kind>daļa|sadaļa|nodaļa|apakšnodaļa|iedaļa)\b', re.IGNORECASE)
ANNEX_HEADINGS = ('Pārejas noteikumi', 'Informatīvā atsauce uz Eiropas Savienības direktīvām',
                  'Informatīvā atsauce uz Eiropas Savienības direktīvu', 'Noslēguma jautājumi')
_POINT = re.compile(r'^(?P<num>\d+(?:\.\d+)?)\.\s+(?P<rest>\S.*)$')
_AMENDED_ACT = re.compile(r'^Izdarīt (?P<act>.+?)\s*(?:\(.*)?šādu[s]? grozījum', re.IGNORECASE)
DIVISIONS = {'daļa': 'part', 'sadaļa': 'title', 'nodaļa': 'chapter', 'apakšnodaļa': 'section',
             'iedaļa': 'subsection'}


# Amending phrases, checked in order
ACTIONS = (
    ('izslēgt', 'delete'), ('svītrot', 'delete'), ('atzīt par spēku zaudējuš', 'delete'),
    ('papildināt', 'add'), ('šādā redakcijā', 'replace'), ('aizstāt', 'replace'),
)


def amendment_action(text: str) -> Optional[str]:
    """
    'Izteikt 5. pantu šādā redakcijā:' -> 'replace'; 'Izslēgt 7. pantu.' -> 'delete'.

    Only an instruction counts, i.e. a sentence opening with its verb ('papildinātā' in
    an ordinary sentence is not one).
    """
    lowered = re.sub(r'^\d+(\.\d+)*\.\s*', '', text.strip()).lower()
    if not re.match(r'^(izteikt|papildināt|aizstāt|izslēgt|svītrot|atzīt|grozīt|aizvietot|'
                    r'(?:[^.:;]{0,120}?)\b(?:izteikt|papildināt|aizstāt|izslēgt|svītrot)\b)', lowered):
        return None
    for phrase, action in ACTIONS:
        if phrase in lowered:
            return action
    return None


def _unquote(text: str) -> str:
    """Quoted text without its quotation marks ('"2) veikt ...;".' -> '2) veikt ...;')."""
    return re.sub(r'"[.;,]?$', '', text[1:] if text.startswith('"') else text)


def _clean(element: etree._Element) -> etree._Element:
    """A copy of an element without amendment notes and page widgets."""
    copy = html.fromstring(html.tostring(element, encoding='unicode'))
    for node in copy.xpath('.//*[@class]'):
        if any(name in (node.get('class') or '').split() for name in SKIP_CLASSES) and node.getparent() is not None:
            parent, previous = node.getparent(), node.getprevious()
            if node.tail:
                if previous is not None:
                    previous.tail = (previous.tail or '') + node.tail
                else:
                    parent.text = (parent.text or '') + node.tail
            parent.remove(node)
    for node in copy.xpath('.//script | .//style'):
        node.getparent().remove(node)
    return copy


def _text(element: Optional[etree._Element]) -> str:
    return element_text(element, BLOCK_TAGS) if element is not None else ''


def _classes(element: etree._Element) -> list[str]:
    return (element.get('class') or '').split()


_GAZETTE_FORMULA = re.compile(r'(ir pieņēmusi un Valsts prezidents izsludina|Ministru kabinets noteic)')
_CLOSING = re.compile(r'^(Likums|Grozījumi|Noteikumi) (Saeimā )?pieņemt[si]')
_REGULATION_CHAPTER = re.compile(r'^(?P<num>[IVXLC]+)\.\s+(?P<heading>\S.*)$')


def _division(number: str, heading: Optional[str]) -> Optional[tuple[str, str, Optional[str], str]]:
    """Kind, number, heading and token of a division heading, or None when it is not one."""
    match = _DIVISION.match(number)
    if match:
        token = match.group('num')
        if token.lower() in ORDINALS:
            token = str(ORDINALS.index(token.lower()) + 1)
        return DIVISIONS.get(match.group('kind').lower(), 'chapter'), number, heading, token
    # A regulation's chapter: 'I. Vispārīgie jautājumi'
    match = _REGULATION_CHAPTER.match(number)
    if match and not heading:
        return 'chapter', f"{match.group('num')}.", match.group('heading'), match.group('num')
    return None


def _centred_bold(block: etree._Element) -> bool:
    """A heading set as a centred bold paragraph (in older issues of Latvijas Vēstnesis)."""
    style = (block.get('style') or '').replace(' ', '').lower()
    return (block.tag == 'p' and 'text-align:center' in style
            and ('font-weight:bold' in style or bool(block.xpath('./b | ./strong'))))


def _right_aligned(block: etree._Element) -> bool:
    """A right-aligned paragraph: after the articles, a signature."""
    style = (block.get('style') or '').replace(' ', '').lower()
    return 'text-align:right' in style or (block.get('align') or '').lower() == 'right'


def _rows(block: etree._Element) -> list[str]:
    """The texts of a block, one per table row; the text around a table (e.g. its notes) is kept."""
    if block.tag != 'table' and not block.xpath('.//table'):
        return [_text(block)]
    if block.tag == 'table':
        rows = [' '.join(' '.join(cell.text_content().split()) for cell in row.xpath('./td | ./th'))
                for row in block.xpath('.//tr')]
        return [row for row in rows if row.strip()]
    texts: list[str] = []
    for child in block:
        if isinstance(child.tag, str):
            texts.extend(_rows(child))
    return [text for text in texts if text]


def _split_heading(block: etree._Element, text: str) -> tuple[str, Optional[str]]:
    """'I nodaļa' and the heading after the line break."""
    before: list[str] = []
    after: list[str] = []
    target = before
    for node in block.iter():
        if node is not block and node.tag == 'br':
            target = after
        if node is block:
            target.append(node.text or '')
            continue
        if node.tag != 'br':
            target.append(node.text or '')
        target.append(node.tail or '')
    number = ' '.join(''.join(before).split())
    heading = ' '.join(''.join(after).split())
    if not number:
        return text, None
    match = _DIVISION.match(number)
    if not heading and match and number[match.end():].lstrip(' .'):
        # 'I nodaļa. Vispārējie noteikumi' on one line
        return number[:match.end()], number[match.end():].lstrip(' .')
    return number, heading or None


class LikumiParser(Parser):
    """Parses an act from likumi.lv (HTML) into legalJSON."""

    def parse(self, file: str, **options) -> 'LikumiParser':
        try:
            root = html.parse(file, html.HTMLParser(encoding='utf-8')).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read likumi.lv document {file}: {e}") from e
        found = root.xpath('//div[contains(concat(" ", @class, " "), " doc-body ")]') if root is not None else []
        if found and found[0].xpath('.//*[@data-num]'):
            self._read(_clean(found[0]))
            return self
        found = root.xpath('//div[@class="docContent"] | //div[contains(concat(" ", @class, " "), " neko-body ")]') \
            if root is not None else []
        if not found:
            raise FileLoadError(f"{file} holds no act text")
        self._read_gazette(_clean(found[0]))
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read(self, content: etree._Element) -> None:
        body = BodyBuilder()
        annex: Optional[ChildrenBuilder] = None
        closing: list[str] = []
        signature: list[str] = []
        seen_article = False

        for block in content:
            if not isinstance(block.tag, str):
                continue
            classes = _classes(block)
            text = _text(block)
            if not text:
                continue
            if 'TV207' in classes and self.preface is None:
                self.preface = text
            elif 'TV206' in classes:
                self.formula = text
            elif 'TV208' in classes and not seen_article:
                # A preamble
                self.recitals.append({'eId': f'rct_{len(self.recitals) + 1}', 'text': text})
            elif 'TV900' in classes and not seen_article:
                # The legal basis of a regulation ('Izdoti saskaņā ar ...')
                self.recitals.append({'eId': f'rct_{len(self.recitals) + 1}', 'text': text})
            elif 'TV218' in classes or (seen_article and text.startswith('Pielikums')):
                # An attachment to a regulation, its heading and content marked P218
                annex = ChildrenBuilder()
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': text, 'heading': None,
                                     'children': annex.children})
            elif annex is not None and 'P218' in classes:
                if 'TV212' in classes and self.annexes[-1]['heading'] is None and not annex.children:
                    self.annexes[-1]['heading'] = text
                else:
                    for row in _rows(block):
                        annex.add(row)
            elif 'TV212' in classes or 'TV214' in classes:
                number, heading = _split_heading(block, text)
                division = _division(number, heading)
                if 'TV214' in classes or any(text.startswith(name) for name in ANNEX_HEADINGS) or division is None:
                    annex = ChildrenBuilder()
                    self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': None, 'heading': text,
                                         'children': annex.children})
                    continue
                annex = None
                kind, number, heading, token = division
                body.division(kind, number, heading=heading, token=token)
            elif block.get('data-num') is not None:
                if annex is not None:
                    annex.add(text)
                    continue
                seen_article = True
                self._read_article(block, body)
            elif seen_article and ('TV216' in classes or 'TV217' in classes):
                signature.append(text)
            elif seen_article:
                closing.append(text)
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        if closing or signature:
            if not signature:
                signature = closing[-1:]
                closing = closing[:-1]
            self.conclusions = {'conclusion_text': ' '.join(closing) or None, 'signature': ' '.join(signature)}

    def _read_gazette(self, content: etree._Element) -> None:
        """The act as published in Latvijas Vēstnesis, or an amending act on likumi.lv."""
        body = BodyBuilder()
        annex: Optional[ChildrenBuilder] = None
        article: Optional[dict[str, Any]] = None
        closing: list[str] = []
        signature: list[str] = []
        recitals: list[str] = []
        amended_act: Optional[str] = None
        quoting = False
        pending: Optional[dict[str, Any]] = None

        def flush() -> None:
            nonlocal article
            if article is not None:
                body.article(article['num'], article['heading'], article['children'].children,
                             token=article['token'])
            article = None

        for block in content:
            if not isinstance(block.tag, str):
                continue
            text = _text(block)
            if not text:
                continue
            classes = _classes(block)
            odd_quotes = text.count('"') % 2 == 1
            if quoting:
                # Text quoted by an amendment, up to the closing quotation mark
                target = annex if annex is not None else article['children']
                current = target.children[-1] if target.children else None
                if current is not None and current.get('amendment') is not None:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': _unquote(text)})
                target.extend(text)
                quoting = not odd_quotes
                continue
            if text.startswith('"') and (article is not None or annex is not None):
                target = annex if annex is not None else article['children']
                current = target.children[-1] if target.children else None
                if current is not None and current.get('amendment') is not None:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': _unquote(text)})
                target.extend(text)
                quoting = odd_quotes
                continue
            if pending is not None and not _ARTICLE_LINE.match(text) and not _DIVISION.match(text) \
                    and len(text) < 200 and article is None:
                # The heading of a division, on the line after its number (older issues)
                pending['heading'] = f"{pending['heading']} {text}" if pending.get('heading') else text
                continue
            pending = None
            if ('lik_c' in classes or 'lik_noteik' in classes or 'lik_dat' in classes
                    or _GAZETTE_FORMULA.search(text)) and not body.articles and article is None:
                # The enacting formula, or a regulation's number, place and date
                self.formula = f'{self.formula} {text}' if self.formula else text
            elif self.preface is None and (block.tag == 'h3' or (
                    self.formula and not body.articles and not body.chapters and article is None
                    and not _DIVISION.match(text) and not _ARTICLE_LINE.match(text))):
                # The title: a heading, or in older issues the line after the enacting formula
                self.preface = text
            elif 'lik_izd' in classes:
                # The legal basis of a regulation ('Izdoti saskaņā ar ...')
                recitals.append(text)
            elif text.startswith('Pielikums') and (article is not None or body.articles or signature):
                # An attachment to a regulation
                flush()
                annex = ChildrenBuilder()
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': text, 'heading': None,
                                     'children': annex.children})
            elif annex is not None and self.annexes[-1]['num'] is not None:
                if block.tag == 'h4' and self.annexes[-1]['heading'] is None and not annex.children:
                    self.annexes[-1]['heading'] = text
                else:
                    for row in _rows(block):
                        annex.add(row)
            elif 'lik_paraksts' in classes or signature or (
                    (article is not None or body.articles) and _right_aligned(block)):
                signature.append(text)
            elif block.tag == 'h4' or _centred_bold(block) or (_DIVISION.match(text) and len(text) < 200):
                flush()
                number, heading = _split_heading(block, text)
                division = _division(number, heading)
                if any(text.startswith(name) for name in ANNEX_HEADINGS) or division is None:
                    annex = ChildrenBuilder()
                    self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': None, 'heading': text,
                                         'children': annex.children})
                    continue
                annex = None
                kind, number, heading, token = division
                chapter = body.division(kind, number, heading=heading, token=token)
                pending = chapter if not heading else None
            elif annex is not None:
                if re.match(r'^\d+(\.\d+)*\.\s', text) or not annex.children:
                    annex.add(text)
                elif re.match(r'^\d+\)\s', text):
                    annex.extend(text)
                else:
                    closing.append(text)
                    annex = None
            elif closing or _CLOSING.match(text):
                closing.append(text)
            elif (match := _ARTICLE_LINE.match(text)) and (block.find('.//b') is not None
                                                           or 'bold' in (block.get('style') or '')
                                                           or len(text) < 250):
                flush()
                number = re.sub(r'[^\d.]', '', match.group('num')).strip('.')
                article = {'num': match.group('num'), 'heading': match.group('heading') or None,
                           'token': number.replace('.', '-'), 'children': ChildrenBuilder()}
            elif (match := _POINT.match(text)) and (article is None or 'pants' not in article['num']) and (
                    '.' not in match.group('num') or article is None):
                # A point of a regulation or of an amending act ('1. Izteikt 5. pantu šādā redakcijā:')
                flush()
                rest = match.group('rest')
                found = _AMENDED_ACT.match(rest)
                if found:
                    amended_act = found.group('act').strip()
                article = {'num': f"{match.group('num')}.", 'heading': None,
                           'token': match.group('num').replace('.', '-'), 'children': ChildrenBuilder()}
                child = article['children'].add(rest)
                action = amendment_action(rest)
                if action and not found:
                    child['amendment'] = {'action': action, 'instruction': rest, 'amended_act': amended_act,
                                          'quoted': []}
            elif (match := _POINT.match(text)) and article is not None and 'pants' not in article['num']:
                # A sub-point ('3.1. ...') of a regulation's point
                child = article['children'].add(text, number=match.group('num'),
                                                token=match.group('num').replace('.', '-'))
                action = amendment_action(text)
                if action:
                    child['amendment'] = {'action': action, 'instruction': text, 'amended_act': amended_act,
                                          'quoted': []}
            elif article is not None:
                match = _PARAGRAPH.match(text)
                children = article['children']
                action = amendment_action(text)
                if match:
                    child = children.add(text, number=match.group('num'), token=match.group('num').replace('.', '-'))
                elif children.children and re.match(r'^\d+(\.\d+)?\)\s', text):
                    children.extend(text)
                    continue
                elif children.children and not text[:1].isupper() and not text[:1].isdigit():
                    children.extend(text)
                    continue
                else:
                    child = children.add(text)
                if action:
                    child['amendment'] = {'action': action, 'instruction': text, 'amended_act': amended_act,
                                          'quoted': []}
            elif body.articles:
                closing.append(text)
            else:
                # Before the first article: an amending act's opening ('Izdarīt ... šādus grozījumus:')
                recitals.append(text)
                match = _AMENDED_ACT.match(text)
                if match:
                    amended_act = match.group('act').strip()
        flush()
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        if recitals:
            self.recitals = [{'eId': f'rct_{n}', 'text': text} for n, text in enumerate(recitals, start=1)]
        if closing or signature:
            self.conclusions = {'conclusion_text': ' '.join(closing) or None,
                                'signature': ' '.join(signature) or None}

    def _read_article(self, block: etree._Element, body: BodyBuilder) -> None:
        children = ChildrenBuilder()
        number = block.get('data-num')
        num, heading = None, None
        for paragraph in block:
            if not isinstance(paragraph.tag, str):
                continue
            text = _text(paragraph)
            if not text:
                continue
            if 'TVP' in _classes(paragraph) and num is None:
                match = _ARTICLE_LINE.match(text)
                if match:
                    num, heading = match.group('num'), match.group('heading') or None
                    continue
            match = _PARAGRAPH.match(text)
            if match:
                children.add(text, number=match.group('num'), token=match.group('num').replace('.', '-'))
            elif children.children and (re.match(r'^\d+(\.\d+)?\)\s', text) or 'limenis2' in _classes(paragraph)):
                children.extend(text)
            else:
                children.add(text)
        if num is None:
            # A regulation's numbered point: its number opens the text
            num = f'{number}.'
            first = children.children[0] if children.children else None
            if first is not None and first['text'].startswith(num):
                first['text'] = first['text'][len(num):].strip()
        body.article(num, heading, children.children, token=re.sub(r'[._]', '-', number))
