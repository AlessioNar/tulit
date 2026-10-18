"""
Parser for Bulgarian acts in the HTML of the State Gazette (Държавен вестник).

The National Assembly publishes each act of the official section of the
State Gazette as a web page (dv.parliament.bg, showMaterialDV.jsp), its
text as paragraphs exported from Word, with centred headings:

- the decree of promulgation of a law (УКАЗ), or the issuing ministry of an
  order, gives the recitals' introduction; the title ('ЗАКОН' and 'за ...',
  'НАРЕДБА № 33 от ... за ...') the preface; a reference to the amended act
  ('(обн., ДВ, бр. 38 от 2016 г.; ...)') the recitals; 'МИНИСТЕРСКИЯТ СЪВЕТ
  ПОСТАНОВИ:' and the like the formula;
- Част, Глава, Раздел and Подраздел headings become divisions;
- each article ('Чл. 4. (1) ...') becomes an article, the centred line
  above it its heading; paragraphs (алинеи, '(1)') become par_N, with points
  ('1.', 'а)') folded into them;
- the supplementary provisions (Допълнителни, Преходни и заключителни
  разпоредби) become top-level divisions of type 'provisions', and each of
  their paragraphs ('§ 1.') an article art_pN; an amending act consists of
  such paragraphs only;
- text quoted by an amendment („...“) stays inside the amending article or
  paragraph, which carries a structured ``amendment``;
- the adoption note and the signatures become the conclusions; an appendix
  (Приложение) or a text adopted by the act (e.g. a rulebook adopted by a
  decree of the Council of Ministers) an annex.
"""
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

# Codes are titled by an adjective ('АДМИНИСТРАТИВНОПРОЦЕСУАЛЕН КОДЕКС', 'ИЗБОРЕН КОДЕКС')
_TITLE = re.compile(r'^(ЗАКОН|(?:[\w-]+\s+)?КОДЕКС|КОНСТИТУЦИЯ|НАРЕДБА|ПОСТАНОВЛЕНИЕ|ПРАВИЛНИК|'
                    r'УСТРОЙСТВЕН ПРАВИЛНИК|ТАРИФА|ИНСТРУКЦИЯ|РЕШЕНИЕ|УКАЗ|ПРАВИЛА|'
                    r'МЕТОДИКА|ЗАПОВЕД|РЕГЛАМЕНТ)\b', re.IGNORECASE)
_DECREE = re.compile(r'^УКАЗ\s+№')
_FORMULA = re.compile(r'(ПОСТАНОВИ|РЕШИ|ПОСТАНОВЯВАМ|УКАЗВАМ|НАРЕЖДАМ)\s*:?$')
_DIVISION = re.compile(r'^(?P<kind>Част|Глава|Раздел|Подраздел)\s+(?P<num>[IVXLC]+|\d+[а-я]?|[а-я]+)\.?'
                       r'(?:\s+(?P<heading>.+))?$', re.IGNORECASE)
_PROVISIONS = re.compile(r'^(Допълнителн[аи]|Преходн[аи]|Заключителн[аи]|Преходни и заключителни|'
                         r'Допълнителни, преходни и заключителни)\s+разпоредб[аи]$', re.IGNORECASE)
_ARTICLE = re.compile(r'^Чл\.\s*(?P<num>\d+[а-я]?)\.\s*(?P<rest>.*)$')
_PARAGRAPH = re.compile(r'^(?:§\s*(?P<num>\d+[а-я]?)\.|(?P<single>Параграф единствен)\.)\s*(?P<rest>.*)$')
_ALINEA = re.compile(r'^\((?P<num>\d+[а-я]?)\)\s')
_POINT = re.compile(r'^(\d+[а-я]?\.|[а-я]\)|•|-|–)\s')
_CLOSING = re.compile(r'^(Законът|Кодексът|Решението|Указът|Постановлението) е приет\w* от|^Законът е приет')
_APPENDIX = re.compile(r'^Приложени[ея]\b')
_ORDINALS = {
    'първа': 1, 'първи': 1, 'втора': 2, 'втори': 2, 'трета': 3, 'трети': 3, 'четвърта': 4, 'четвърти': 4,
    'пета': 5, 'пети': 5, 'шеста': 6, 'шести': 6, 'седма': 7, 'седми': 7, 'осма': 8, 'осми': 8,
    'девета': 9, 'девети': 9, 'десета': 10, 'десети': 10, 'единадесета': 11, 'дванадесета': 12,
    'тринадесета': 13, 'четиринадесета': 14, 'петнадесета': 15, 'шестнадесета': 16, 'седемнадесета': 17,
    'осемнадесета': 18, 'деветнадесета': 19, 'двадесета': 20,
}
_LATIN = str.maketrans({'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',
                        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's',
                        'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sht',
                        'ъ': 'a', 'ь': 'y', 'ю': 'yu', 'я': 'ya'})
DIVISIONS = {'част': 'part', 'глава': 'chapter', 'раздел': 'section', 'подраздел': 'subsection'}

# Amending phrases, checked in order
ACTIONS = (
    (r'се отменя|се отменят|отменят се|отменя се|се заличава|се заличават|заличават се', 'delete'),
    (r'се създава|се създават|създава се|създават се|се добавя|се добавят|се допълва|се допълват', 'add'),
    (r'се изменя|се изменят|се заменя|се заменят|заменят се|се преномерира|става ', 'replace'),
    (r'се правят следните изменения|следните изменения', 'amend'),
)


def amendment_action(text: str) -> Optional[str]:
    """'Член 33 се изменя така:' -> 'replace'; 'В чл. 9 ал. 4 се отменя.' -> 'delete'."""
    for pattern, action in ACTIONS:
        if re.search(pattern, text, re.IGNORECASE):
            return action
    return None


def _token(number: str) -> str:
    """'19а' -> '19a': article numbers with a Cyrillic letter, made safe for an eId."""
    return number.lower().translate(_LATIN)


def _division_token(number: str) -> str:
    return str(_ORDINALS.get(number.lower(), number.upper() if re.fullmatch(r'[ivxlc]+', number, re.I)
                             else _token(number)))


def _next_provision(num: str, text: str) -> bool:
    """Whether a line starts the provision after the current one ('§ 4. ...' after '§ 3.')."""
    current = re.match(r'^(Чл\.|§)\s*(\d+)\.$', num)
    following = re.match(r'^(Чл\.|§)\s*(\d+)\.\s', text)
    return bool(current and following and current.group(1) == following.group(1)
                and int(following.group(2)) == int(current.group(2)) + 1)


def _quote_depth(depth: int, text: str) -> int:
    """
    How many quotations („...“) are open after a line.

    Nested quotations often share one closing mark ('„деня на ... в „Държавен вестник“.'), so a line ending
    with a closing mark closes them all.
    """
    if re.search(r'[“”][.;,:]?\s*$', text):
        return 0
    return max(depth + text.count('„') - text.count('“'), 0)


class _Block:
    __slots__ = ('text', 'align', 'rows')

    def __init__(self, text: str, align: Optional[str], rows: Optional[list[str]] = None):
        self.text, self.align, self.rows = text, align, rows


def _text(element: etree._Element) -> str:
    return ' '.join(element.text_content().replace('­', '').split())


def _blocks(content: etree._Element) -> list[_Block]:
    """The paragraphs and tables of a material, in order."""
    blocks: list[_Block] = []

    def elements(node: etree._Element):
        for child in node:
            if not isinstance(child.tag, str):
                continue
            if child.tag in ('p', 'table'):
                yield child
            else:
                yield from elements(child)

    for element in elements(content):
        if element.tag == 'table':
            rows = [' | '.join(cell for cell in (_text(td) for td in tr.xpath('./td | ./th')) if cell)
                    for tr in element.xpath('.//tr')]
            rows = [row for row in rows if row]
            if rows:
                blocks.append(_Block('', None, rows))
            continue
        text = _text(element)
        if not text:
            continue
        style = (element.get('style') or '').replace(' ', '').lower()
        align = (element.get('align') or '').lower() or ('center' if 'text-align:center' in style else
                                                         'right' if 'text-align:right' in style else None)
        blocks.append(_Block(text, align))
    # The page number printed at the end of the material
    while blocks and not blocks[-1].rows and re.fullmatch(r'\d{1,5}', blocks[-1].text):
        blocks.pop()
    return blocks


class DarzhavenVestnikParser(Parser):
    """Parses a Bulgarian act (State Gazette HTML) into legalJSON."""

    def parse(self, file: str, **options) -> 'DarzhavenVestnikParser':
        try:
            root = html.parse(file, html.HTMLParser(encoding='utf-8')).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read State Gazette material {file}: {e}") from e
        title = root.xpath('//span[@class="tdHead1"]') if root is not None else []
        content = title[0].xpath('ancestor::tr[1]/following-sibling::tr//div') if title else []
        if not content:
            raise FileLoadError(f"{file} holds no State Gazette material")
        self.material_title = _text(title[0])
        blocks = _blocks(content[0])
        start = self._read_front(blocks)
        self._read_body(blocks[start:])
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read_front(self, blocks: list[_Block]) -> int:
        """Decree of promulgation, title, reference to the amended act and formula; returns where the body starts."""
        title = next((i for i, block in enumerate(blocks) if block.align == 'center' and _TITLE.match(block.text)
                      and not _DECREE.match(block.text) and not _FORMULA.search(block.text)), None)
        if title is None:
            self.preface = self.material_title or None
            return 0
        if title:
            self.recitals_init = ' '.join(block.text for block in blocks[:title])
        parts = [blocks[title].text]
        index = title + 1
        # The title may run over the following centred lines ('ЗАКОН' / 'за електронната идентификация')
        while index < len(blocks) and blocks[index].align == 'center' and blocks[index].text[:1].islower():
            parts.append(blocks[index].text)
            index += 1
        title_text = ' '.join(parts)
        recitals: list[str] = []
        # The reference to the amended act, when printed with the title
        reference = re.search(r'\s*(\((?:обн|Обн)\..*\))$', title_text)
        if reference:
            recitals.append(reference.group(1))
            title_text = title_text[:reference.start()]
        self.preface = title_text
        while index < len(blocks):
            block = blocks[index]
            if _FORMULA.search(block.text) and block.align == 'center':
                self.formula = block.text
                index += 1
                break
            if block.text.startswith('(обн.') or block.text.startswith('(Обн.'):
                recitals.append(block.text)
                index += 1
                continue
            break
        self.recitals = [{'eId': f'rct_{n}', 'text': text} for n, text in enumerate(recitals, start=1)]
        return index

    def _read_body(self, blocks: list[_Block]) -> None:
        body = BodyBuilder()
        article: Optional[dict[str, Any]] = None
        annex: Optional[ChildrenBuilder] = None
        closing: list[str] = []
        signatures: list[str] = []
        heading: Optional[str] = None
        division: Optional[dict[str, Any]] = None
        quoting = 0
        amended_act = self._amended_act_from_title()

        def flush() -> None:
            nonlocal article
            if article is not None:
                body.article(article['num'], article['heading'], article['children'].children,
                             token=article['token'])
            article = None

        def add(text: str) -> None:
            nonlocal amended_act
            children = article['children']
            match = _ALINEA.match(text)
            if match:
                child = children.add(text, number=match.group('num'), token=_token(match.group('num')))
            elif children.children and _POINT.match(text):
                children.extend(text)
                current = children.children[-1]
                action = amendment_action(text)
                if current.get('amendment') is None and action:
                    current['amendment'] = {'action': action, 'instruction': text, 'amended_act': amended_act,
                                            'quoted': []}
                return
            else:
                child = children.add(text)
            found = re.match(r'^В\s+((?:Закона|Кодекса|Наредба|Правилника|Устройствения правилник|Постановление|'
                             r'Тарифата|Инструкция|Конституцията)[^(:]*?)\s*(?:\(|,|:|се\s)', text)
            if found:
                amended_act = found.group(1).strip()
            action = amendment_action(text)
            if action:
                child['amendment'] = {'action': action, 'instruction': text, 'amended_act': amended_act,
                                      'quoted': []}

        for i, block in enumerate(blocks):
            text = block.text
            if block.rows is not None:
                # A table: its rows join the annex or the text above
                if annex is not None:
                    for row in block.rows:
                        annex.add(row)
                elif article is not None:
                    article['children'].extend(' '.join(block.rows))
                continue
            if quoting and article is not None and (_next_provision(article['num'], text)
                                                    or (block.align == 'center' and _PROVISIONS.match(text))):
                # A quotation left open (its end is in a table or a separate annex) ends at the next provision
                quoting = 0
            if article is not None and (quoting or text.startswith('„')):
                # Text quoted by an amendment ('„Задължения при идентификация', then 'Чл. 5. ...')
                children = article['children']
                children.extend(text)
                current = children.children[-1]
                if current.get('amendment') is not None:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': text.strip('„“ ')})
                quoting = _quote_depth(quoting, text)
                continue
            if annex is not None:
                if self.annexes[-1]['heading'] is None and not annex.children and block.align == 'center' \
                        and _APPENDIX.match(self.annexes[-1]['num']):
                    self.annexes[-1]['heading'] = text
                else:
                    annex.add(text)
                continue
            if signatures and (block.align == 'center' and _TITLE.match(text) or _APPENDIX.match(text)) \
                    or (_APPENDIX.match(text) and block.align == 'right'):
                # An appendix, or a text adopted by the act, after the signatures
                flush()
                annex = ChildrenBuilder()
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': text, 'heading': None,
                                     'children': annex.children})
                continue
            if _CLOSING.match(text) and (article is not None or body.articles):
                flush()
                closing.append(text)
                continue
            # A quoted annex heading ('„Приложение № 1 ...') is text of the amendment above, not a signature
            if block.align == 'right' and (article is not None or body.articles or closing) \
                    and not (article is not None and text.startswith(('„', '"', '“'))):
                flush()
                signatures.append(text)
                continue
            if signatures:
                signatures.append(text)
                continue
            if block.align == 'center' and _PROVISIONS.match(text):
                flush()
                body.close_divisions()
                division = body.division('provisions', None, heading=text, rank=0)
                heading = None
                continue
            match = _DIVISION.match(text) if block.align == 'center' else None
            if match:
                flush()
                kind = match.group('kind').lower()
                number = f"{match.group('kind')} {match.group('num')}"
                division = body.division(DIVISIONS[kind], number, heading=match.group('heading'),
                                         token=_division_token(match.group('num')))
                heading = None
                continue
            if block.align == 'center':
                following = blocks[i + 1].text if i + 1 < len(blocks) else ''
                if division is not None and division.get('heading') is None and article is None:
                    division['heading'] = text
                elif _ARTICLE.match(following) or _PARAGRAPH.match(following):
                    heading = text
                elif article is not None:
                    add(text)
                continue
            match = _ARTICLE.match(text)
            if match:
                flush()
                article = {'num': f"Чл. {match.group('num')}.", 'heading': heading, 'token': _token(match.group('num')),
                           'children': ChildrenBuilder()}
                heading, division = None, None
                if match.group('rest'):
                    add(match.group('rest'))
                quoting = _quote_depth(0, text)
                continue
            match = _PARAGRAPH.match(text)
            if match:
                flush()
                number = match.group('num')
                article = {'num': f'§ {number}.' if number else f"{match.group('single')}.", 'heading': heading,
                           'token': f'p{_token(number)}' if number else 'p1', 'children': ChildrenBuilder()}
                heading, division = None, None
                if match.group('rest'):
                    add(match.group('rest'))
                quoting = _quote_depth(0, text)
                continue
            if article is not None:
                add(text)
                quoting = _quote_depth(0, text)
        flush()
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        if closing or signatures:
            self.conclusions = {'conclusion_text': ' '.join(closing) or None,
                                'signature': ' '.join(signatures) or None}

    def _amended_act_from_title(self) -> Optional[str]:
        """'Закон за изменение и допълнение на Закона за ...' -> 'Закона за ...'."""
        match = re.search(r'за изменение(?: и допълнение)? на (.+)$|за допълнение на (.+)$', self.preface or '',
                          re.IGNORECASE)
        if not match:
            return None
        return re.sub(r'\s*\((?:обн|Обн)\..*$', '', (match.group(1) or match.group(2))).strip()
