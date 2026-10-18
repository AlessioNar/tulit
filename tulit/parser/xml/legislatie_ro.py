"""
Parser for Romanian acts from the Portal Legislativ (legislatie.just.ro) web service.

The Ministry of Justice's legislation database answers searches through a
SOAP web service, which returns each act with its metadata and its text as
published in Monitorul Oficial (the basic form). The text keeps the
portal's layout as plain text: blocks (a heading, an article, an annex) are
separated by '+' markers, items of a list or of an amending article by
'...' markers, and paragraphs by runs of spaces:

- the title ('LEGE nr. 190 din 18 iulie 2018 privind ...') gives the
  preface; the issuer and the publication in Monitorul Oficial the
  recitals' introduction; the considerations of an ordinance or decision
  ('Având în vedere ...', 'în temeiul ...') the recitals and the enacting
  clause ('Parlamentul României adoptă prezenta lege.') the formula;
- Titlul, Capitolul and Secțiunea headings become divisions;
- each 'Articolul N' becomes an article, its heading the title printed
  above it; paragraphs '(1)' become par_N, with letters 'a)' folded in;
- the points of an amending article ('1. La articolul 1, alineatul (3) se
  modifică ...') become its children, with the text they introduce as the
  structured amendment's quoted text;
- the signatures become the conclusions and the annexes (Anexa) the annexes.
"""
import re
from typing import Any, Optional

from lxml import etree

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

NS = 'http://schemas.datacontract.org/2004/07/FreeWebService'
_BLOCK = re.compile(r'\s*\n[\t ]*\xa0\+\xa0\s*\n')
_ITEM = re.compile(r'\xa0\.\.\.\xa0')
_GAP = re.compile(r'[ \t\n\xa0]{3,}')
# Older texts set paragraphs apart by two spaces only: split there before a numbered paragraph or point
_SOFT_GAP = re.compile(r'\s{2}(?=["„]?(?:\d+(?:\^\d+)?\.|\(\d+(?:\^\d+)?\)|[a-z]\))\s+["„]?[A-ZĂÂÎȘȚŞŢ])')
_INLINE_HEADING = re.compile(r'^(?P<heading>[A-ZĂÂÎȘȚŞŢ][^.;:!?]{0,150}?[^\s.;:,])  (?=[A-ZĂÂÎȘȚŞŢ(„"])')
_LABEL = re.compile(r'^(\(\d+(\^\d+)?\)|[a-z](\^\d+)?\)|\d+(\^\d+)?\.|[IVXLC]+\.)$')
_ARTICLE = re.compile(r'^(?:Articolul|Art\.)\s+(?P<num>\d+(?:\^\d+)?|[IVXLC]+(?:\^\d+)?|UNIC|unic)\b\.?$|'
                      r'^(?P<sole>ARTICOL UNIC|Articol unic|Articolul UNIC)$')
_DIVISION = re.compile(r'^(?P<kind>Partea|Cartea|Titlul|Capitolul|Secțiunea|Secţiunea|Subsecțiunea|Subsecţiunea)'
                       r'\s+(?:a\s+)?(?P<num>[^\s-]+)(?:-a)?$', re.IGNORECASE)
_EDITOR_NOTE = re.compile(r'-{5,}\s+NOT[ĂA] C\.T\.C\.E\.[\s\S]*?(?=\s*\n[\t ]*\xa0\+\xa0|$)')
# An entry of the table of contents the database prints after a part's heading: 'Titlul I - ...  art. 1-14'
_CONTENTS = re.compile(r'^(?:Titlul|Capitolul|Secțiunea|Secţiunea|Subsecțiunea|Subsecţiunea)\b.* - .*'
                       r'\bart\. \d+(?:\^\d+)?(?:-\d+(?:\^\d+)?)?$')
# An article run into the heading block of a division ('Secţiunea a 3-a   Cecul   ART 2.655  ...')
_RUN_IN_ARTICLE = re.compile(r'\s{3,}(?:Articolul|ART\.?|Art\.)\s+(?P<num>\d{1,3}(?:\.\d{3})*)\b\.?\s+')
_ANNEX = re.compile(r'^(ANEX[AĂ]|Anex[aă])(\s+nr\.\s*\S+)?\b')
_PARAGRAPH = re.compile(r'^\((?P<num>\d+(?:\^\d+)?)\)\s*')
_POINT = re.compile(r'^(?P<num>\d+(?:\^\d+)?)\.\s+')
_LETTER = re.compile(r'^[a-z](\^\d+)?\)\s')
_CLOSING = re.compile(r'^(Această lege a fost adoptată|Aceasta lege a fost adoptata|PRIM-MINISTRU|PREȘEDINTELE|'
                      r'Constituția României a fost adoptată|Constituţia României a fost adoptată|'
                      r'PREŞEDINTELE|p\. PREȘEDINTELE|p\. PREŞEDINTELE|PREȘEDINTELE ROMÂNIEI|Contrasemnează)')
_FORMULA = re.compile(r'(adopt[ăa] prezenta|adopt[ăa] prezentul|adopt[ăa] constitu[țţ]ia|'
                      r'hotărăște:?$|hotărăşte:?$|decretează:?$|'
                      r'emite (următorul|prezentul)|'
                      r'emite următoarea|adoptă următoarea)', re.IGNORECASE)
_QUOTE_START = re.compile(r'(cuprins|conținut|conţinut|redactare|următoarea formă)\s*:$')
DIVISIONS = {'partea': 'part', 'cartea': 'part', 'titlul': 'title', 'capitolul': 'chapter', 'secțiunea': 'section',
             'secţiunea': 'section', 'subsecțiunea': 'subsection', 'subsecţiunea': 'subsection'}

# Amending phrases, checked in order
ACTIONS = (
    (r'se modific[ăa] (și|şi) se completeaz[ăa]', 'amend'),
    (r'se abrog[ăa]', 'delete'),
    (r'se introduc|se insereaz[ăa]', 'insert'),
    (r'se modific[ăa] (și|şi) va avea|se modific[ăa] (și|şi) vor avea|se înlocuiește|se înlocuieşte', 'replace'),
    (r'se completeaz[ăa]', 'add'),
    (r'se modific[ăa]', 'amend'),
    (r'\bv(?:a|or) avea următorul cuprins', 'replace'),
)


def amendment_action(text: str) -> Optional[str]:
    """'La articolul 1, alineatul (3) se modifică și va avea următorul cuprins:' -> 'replace'."""
    for pattern, action in ACTIONS:
        if re.search(pattern, text, re.IGNORECASE):
            return action
    return None


def _amended_act(text: str) -> Optional[str]:
    """'Legea nr. 102/2005 privind ..., publicată în ...' -> 'Legea nr. 102/2005'."""
    match = re.search(r'((?:Legea|Ordonanța de urgență a Guvernului|Ordonanţa de urgenţă a Guvernului|'
                      r'Ordonanța Guvernului|'
                      r'Ordonanţa Guvernului|Hotărârea Guvernului|Codul [\w ]+?|Decretul|Ordinul)(?: [\w ]+?)? '
                      r'nr\. \d+/\d{4})', text)
    return match.group(1) if match else None


def _unbalanced(text: str) -> bool:
    """Whether a paragraph opens (or closes) a quotation it does not close (or open)."""
    # Romanian quotes close with ” or “ („Gheorghe Ionescu-Șișești“)
    return text.count('"') % 2 == 1 or text.count('„') != text.count('”') + text.count('“')


def _number(number: str) -> Optional[int]:
    """'14' -> 14, 'IV' -> 4; None for '14^2' and other numbers out of the sequence."""
    if re.fullmatch(r'\d+', number):
        return int(number)
    if re.fullmatch(r'[IVXLC]+', number):
        values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        total = 0
        for i, letter in enumerate(number):
            value = values[letter]
            total += -value if i + 1 < len(number) and values[number[i + 1]] > value else value
        return total
    return None


def _tokens(text: str) -> list[str]:
    """The paragraphs of a run of text, with labels ('(1)', 'a)', '1.') joined to the text they number."""
    parts = [' '.join(part.split()) for chunk in _GAP.split(text) for part in _SOFT_GAP.split(chunk)]
    tokens: list[str] = []
    label = ''
    for part in parts:
        if not part or re.fullmatch(r'[-.]{3,}', part):
            continue
        if _LABEL.match(part):
            label = f'{label} {part}'.strip()
            continue
        tokens.append(f'{label} {part}'.strip() if label else part)
        label = ''
    if label:
        tokens.append(label)
    return tokens


class LegislatieParser(Parser):
    """Parses a Romanian act from the Portal Legislativ web service into legalJSON."""

    def parse(self, file: str, **options) -> 'LegislatieParser':
        try:
            root = etree.parse(file).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read Portal Legislativ document {file}: {e}") from e
        text = root.findtext(f'.//{{{NS}}}Text')
        if not text or not text.strip():
            raise FileLoadError(f"{file} holds no act text")
        # Notes of the database's editor are not part of the act
        text = _EDITOR_NOTE.sub('', text)
        blocks = [block for block in _BLOCK.split(text) if block.strip()]
        self._read_front(blocks[0])
        self._read_body(blocks[1:])
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read_front(self, block: str) -> None:
        """Title, issuer, publication, considerations and enacting formula."""
        tokens = _tokens(block)
        if not tokens:
            return
        self.preface = tokens[0]
        rest = tokens[1:]
        intro: list[str] = []
        while rest and (rest[0] in ('EMITENT', 'Publicat în') or not intro or rest[0].startswith('MONITORUL')
                        or intro[-1] == 'Publicat în' or intro[-1] == 'EMITENT'):
            intro.append(rest.pop(0))
            if intro[-1].startswith('MONITORUL'):
                break
        self.recitals_init = ' '.join(intro) or None
        formula = next((i for i in range(len(rest) - 1, -1, -1) if _FORMULA.search(rest[i])), None)
        if formula is not None:
            self.formula = rest[formula]
            considerations = rest[:formula]
            # Considerations run into the formula in older texts: '..., Guvernul României adoptă prezenta ordonanţă.'
            split = re.search(r'(?:^|[,;.]\s+)((?:Guvernul|Parlamentul|Președintele|Preşedintele)\b[^,;]*$)',
                              self.formula)
            if split and split.start(1) > 0:
                considerations = considerations + [self.formula[:split.start(1)].strip()]
                self.formula = split.group(1)
            self._next_heading = ' '.join(rest[formula + 1:]) or None
        else:
            considerations = rest
            self._next_heading = None
        self.recitals = [{'eId': f'rct_{n}', 'text': text} for n, text in enumerate(considerations, start=1)]

    def _read_body(self, blocks: list[str]) -> None:
        body = BodyBuilder()
        self._closing: list[str] = []
        heading: Optional[str] = getattr(self, '_next_heading', None)
        current: Optional[dict[str, Any]] = None
        self._quoting = self._quote_mark = False

        for index, block in enumerate(blocks):
            items = [tokens for tokens in (_tokens(item) for item in _ITEM.split(block)) if tokens]
            if not items:
                continue
            first = items[0][0]
            following = (_tokens(blocks[index + 1]) or [''])[0] if index + 1 < len(blocks) else ''
            if _ANNEX.match(first) and not self._quoting:
                tokens = [token for item in items for token in item]
                annex = ChildrenBuilder()
                annex_heading = tokens[1] if len(tokens) > 1 and len(tokens[1]) < 300 else None
                for token in tokens[2 if annex_heading else 1:]:
                    if not re.fullmatch(r'-+', token):
                        annex.add(token)
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': first, 'heading': annex_heading,
                                     'children': annex.children})
                continue
            if self._closing:
                self._closing.extend(token for item in items for token in item)
                continue
            article = _ARTICLE.match(first)
            if self._quoting and current is not None and not (article and self._expected(article, current)):
                # Text an amendment introduces: a whole article, chapter or section
                for n, item in enumerate(items):
                    self._read_item(current, item, quoted_block=(n == 0))
                continue
            self._quoting = False
            division = _DIVISION.match(first)
            if division:
                tokens = [token for item in items for token in item]
                if any(_CONTENTS.match(token) for token in tokens[1:]):
                    continue
                run_in = _RUN_IN_ARTICLE.search(block)
                if run_in:
                    # Read the article as a block of its own, after the division
                    blocks.insert(index + 1, f"Articolul {run_in.group('num').replace('.', '')}     "
                                             f"{block[run_in.end():]}")
                    block = block[:run_in.start()]
                    tokens = [token for item in _ITEM.split(block) for token in _tokens(item)]
                    following = (_tokens(blocks[index + 1]) or [''])[0]
                heading = (' '.join(tokens[2:]) or None) if _ARTICLE.match(following) else None
                body.division(DIVISIONS.get(division.group('kind').lower(), 'chapter'), first,
                              heading=tokens[1] if len(tokens) > 1 else None,
                              token=division.group('num').replace('^', '-'))
                continue
            if not article:
                tokens = [token for item in items for token in item]
                if _CLOSING.match(first) or current is None:
                    self._closing.extend(tokens) if current is not None else self.recitals.extend(
                        {'eId': f'rct_{len(self.recitals) + 1}', 'text': token} for token in tokens)
                else:
                    # Text between articles that heads nothing (e.g. a note): it stays with the article above
                    for token in tokens:
                        current['children'].add(token)
                continue
            number = article.group('num') or '1'
            sole = bool(article.group('sole')) or number.upper() == 'UNIC'
            current = {'children': ChildrenBuilder(), 'act': None, 'number': _number(number)}
            article_heading, heading = heading, None
            if article_heading is None and len(items[0]) > 1:
                # Older texts print the title after the number, two spaces before the text
                inline = _INLINE_HEADING.match(_GAP.split(_ITEM.split(block)[0].strip(), 1)[-1].strip())
                # The title is the start of the first paragraph, which it does not run past
                if inline and not re.search(r'\b(din|de|la|a|al|ale|în|cu|și|şi|prin|privind|pentru)$',
                                            inline.group('heading')) and not _GAP.search(inline.group('heading')) \
                        and items[0][1].startswith(' '.join(inline.group('heading').split())) \
                        and len(items[0][1]) > len(' '.join(inline.group('heading').split())):
                    article_heading = ' '.join(inline.group('heading').split())
                    items[0][1] = items[0][1][len(article_heading):].strip()
                elif (len(items[0]) > 2 or len(items) > 1) and len(items[0][1]) < 200 \
                        and not re.search(r'[.;:,!?"”]$|:|\b[a-z]\)$', items[0][1]) and items[0][1][:1].isupper() \
                        and not _LABEL.match(items[0][1].split()[0]):
                    # Or as a paragraph of its own
                    article_heading = items[0].pop(1)
            for n, item in enumerate(items):
                self._read_item(current, item[1:] if n == 0 else item)
                if self._closing:
                    break
            children = current['children'].children
            last = items[-1][-1]
            if _ARTICLE.match(following) and not self._quoting and not self._closing and children \
                    and len(last) < 250 and not re.search(r'[.;:,"”]$', last) and not _LABEL.match(last) \
                    and children[-1]['text'].endswith(last) and (len(children) > 1 or children[-1]['text'] != last):
                # The title printed above the next article ends this block
                if children[-1]['text'] == last:
                    children.pop()
                else:
                    children[-1]['text'] = children[-1]['text'][:-len(last)].rstrip()
                heading = last
            body.article('Articol unic' if sole else first.rstrip('.'), article_heading, children,
                         token='1' if sole else number.replace('^', '-'))
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        if self._closing:
            adopted = [t for t in self._closing
                       if t.startswith(('Această lege', 'Aceasta lege', 'Constituția', 'Constituţia'))]
            signature = [t for t in self._closing if t not in adopted and not re.fullmatch(r'-+', t)]
            self.conclusions = {'conclusion_text': ' '.join(adopted) or None, 'signature': ' '.join(signature) or None}

    @staticmethod
    def _expected(article: re.Match, current: dict[str, Any]) -> bool:
        """Whether an article is the one that follows the current article (and not text quoted by it)."""
        number = _number(article.group('num') or '')
        return number is not None and current['number'] is not None and number == current['number'] + 1

    def _read_item(self, current: dict[str, Any], tokens: list[str], quoted_block: bool = False) -> None:
        """The paragraphs of an item of an article: its own text, amending points or the text they introduce."""
        children: ChildrenBuilder = current['children']
        for position, token in enumerate(tokens):
            if _CLOSING.match(token):
                self._quoting = False
                self._closing.extend(tokens[position:])
                return
            point = _POINT.match(token)
            action = amendment_action(token)
            new_point = bool(point and action) and not token.startswith(('"', '„'))
            if self._quoting and not (new_point and not quoted_block):
                child = children.children[-1]
                child['text'] = f"{child['text']} {token}"
                if child.get('amendment') is not None:
                    child['amendment']['quoted'].append({'kind': 'text', 'text': token.strip('"„”')})
                if self._quote_mark and _unbalanced(token):
                    # The closing quotation mark
                    self._quoting = self._quote_mark = False
                continue
            quoted_block = False
            found = _amended_act(token)
            if found and action:
                current['act'] = found
            paragraph = _PARAGRAPH.match(token)
            child: Optional[dict[str, Any]]
            if paragraph:
                child = children.add(token, number=paragraph.group('num'),
                                     token=paragraph.group('num').replace('^', '-'))
            elif new_point:
                child = children.add(token)
            elif children.children and (_LETTER.match(token) or point or token[:1].islower()):
                children.extend(token)
                child = None
            else:
                child = children.add(token)
            if child is not None and action and (new_point or _QUOTE_START.search(token) or 'urmează' in token
                                                 or re.search(r'se abrog', token) or 'cuprins:' in token):
                inline = re.search(r'(?:cuprins|conținut|conţinut)\s*:\s*["„](.+)$', token)
                child['amendment'] = {'action': action, 'instruction': token[:inline.start(1) - 1].strip() if inline
                                      else token, 'amended_act': _amended_act(token) or current['act'],
                                      'quoted': [{'kind': 'text', 'text': inline.group(1).strip('"„”')}] if inline
                                      else []}
            # Quoted text follows an instruction ending '... cu următorul cuprins:', or opens with a quotation mark
            self._quote_mark = _unbalanced(token)
            # ('... cu acelaşi conţinut:' in a provision that amends nothing introduces no quotation)
            self._quoting = bool(_QUOTE_START.search(token) and action) or self._quote_mark
