"""
Parser for Belgian legislation in the HTML of eJustice (Moniteur belge and Justel).

The Moniteur belge / Belgisch Staatsblad, the official journal, publishes
each act as adopted; Justel, its consolidation service, publishes the text
as amended. Both pages give the text as lines separated by line breaks, in
French or Dutch:

- the title ('30 JUILLET 2018. - Loi relative à ...') gives the preface;
- the opening up to the first heading or article ('PHILIPPE, Roi des
  Belges, ... ce qui suit :') gives the formula, with the citations of an
  order ('Vu ...', 'Considérant ...', 'Gelet op ...') and the report to the
  King as recitals;
- headings ('TITRE 1er. - ...', 'CHAPITRE II. - ...', 'HOOFDSTUK 2. - ...')
  become divisions;
- each article ('Art. 4. § 1er. ...', 'Artikel 1. ...') becomes an article:
  its paragraphs ('§ 1er.') become par_N, and where it has none each
  alinéa becomes a child; points ('1°', 'a)', '-') are folded into the
  child above. Text quoted by an amendment («...») stays in the amending
  article, which carries a structured ``amendment``;
- the promulgation, date and signatures become the conclusions, and the
  annexes (Annexe, Bijlage) the annexes. The parliamentary references
  after the signatures are left out.

Justel's amendment markers ('[1 ... ]1') and its notes on them are left out.
"""
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, eid_token

ROW = '\u2063'
"""Marks a line that is a table row."""
ANCHOR = '\u2064'
"""Marks a line that starts at one of Justel's anchors (an article or a heading of the act itself)."""
_BLOCKS = ('p', 'div', 'tr', 'li', 'table', 'h1', 'h2', 'h3', 'h4')
_DIVISION = re.compile(
    r'^(?P<kind>LIVRE|TITRE|SOUS-TITRE|CHAPITRE|SECTION|SOUS-SECTION|PARTIE|BOEK|TITEL|ONDERTITEL|HOOFDSTUK|AFDELING|'
    r'ONDERAFDELING|DEEL)'
    r'(?:\s+(?P<num>[IVXLC]+|\d+)(?:er|re|e|ste|de)?(?P<suffix>\s*(?:/\d+|bis|ter|quater|[A-Z]\b))?'
    r'|\s+(?P<special>PRELIMINAIRE|PREMIER|PREMIERE|VOORAFGAAND|VOORAFGAANDE|INLEIDEND|INLEIDENDE))?'
    r'\s*\.?\s*(?:-|–)\s*(?P<heading>.+)$', re.IGNORECASE)
_PRELIMINARY = re.compile(r'^(?P<kind>TITRE|CHAPITRE|VOORAFGAANDE TITEL|VOORAFGAAND HOOFDSTUK|INLEIDENDE TITEL|'
                          r'INLEIDEND HOOFDSTUK)(?:\s+PRELIMINAIRE)?\.?\s*(?:-|–)\s*(?P<heading>.+)$')
_ARTICLE = re.compile(
    # 'Art. I.' (the Constitution's transitional articles), 'Article 1er.', 'Art. I.2.', 'Art. 7bis.', 'Art. 51/1.'
    r'^(?:Article|Art\.|Artikel)\s+(?P<num>[IVXLC]+(?=\s*\.\s)|'
    r'(?:[IVXLC]+[.:])?\d+(?:er|re|e)?(?:[.:/]\d+)*(?:\s?(?:bis|ter|quater|'
    r'quinquies|sexies|septies|octies|novies|decies))?(?:/\d+)?)\s*\.\s*(?P<rest>.*)$')
_SOLE_ARTICLE = re.compile(r'^(?:Article unique|Enig artikel)\s*\.\s*(?P<rest>.*)$', re.IGNORECASE)
_PARAGRAPH = re.compile(r'^§\s*(?P<num>\d+(?:er|e)?(?:/\d+)?(?:bis|ter|quater)?)\.\s')
_POINT = re.compile(r'^(\d+°|[a-z]\)|-|–|•|\d+\))\s?')
_CITATION = re.compile(r'^(Vu |Considérant|Sur la proposition|Sur l\'avis|Après délibération|Gelet op|Overwegende|'
                       r'Op de voordracht|Na beraadslaging|Op voorstel)', re.IGNORECASE)
_FORMULA_END = re.compile(r'(ce qui suit|arrêté et arrêtons|arrête|arrete|hetgeen volgt|besluiten Wij|besluit|'
                          r'Nous avons arrêté)\s*:?\s*$', re.IGNORECASE)
_CLOSING = re.compile(r'^(Promulguons|Kondigen|Donné à|Gegeven te|Fait à|Bruxelles, le|Namur, le|Brussel, \d|'
                      r'Namen, \d|Eupen, den|Gedaan te)')
_NOTES = re.compile(r'^(_{3,}|Note$|Nota$|Notes$|Nota\'s$)')
_ANNEX = re.compile(r'^(Annexe|ANNEXE|Bijlage|BIJLAGE)(\s+[\w/.-]+)?\.?(\s*(?:-|–).*|[.:]?\s+[A-Z].*)?$')
# Justel numbers the annexes as articles N1, N2, ... under a heading 'ANNEXES.' / 'BIJLAGEN.'
_JUSTEL_ANNEX = re.compile(r'^Art\.\s*N\d*\s*\.\s*(?P<rest>.*)$')
_JUSTEL_ANNEXES = re.compile(r'^(ANNEXES|Annexes|BIJLAGEN|Bijlagen)\s*\.?$')
# 'Bijlage 1 bij het decreet van 7 december 2018 ...', after the parliamentary references
_ANNEX_AFTER_NOTES = re.compile(r'^(Annexe|ANNEXE|Bijlage|BIJLAGE)\s+\S+\s+(bij|à|au|aux|de|van)\b')
_JUSTEL_NOTE = re.compile(r'^(\(\d+\)\s*<|\(NOTE|\(NOTA|-{5,})')
_INLINE_NOTE = re.compile(r'\s*<[^<>]{0,400}?(?:En vigueur|In werking|Inséré|Ingevoegd|Abrogé|Opgeheven|Remplacé|'
                          r'Vervangen|L \d{4}-|W \d{4}-|AR \d{4}-|KB \d{4}-|DCFR|DVR)[^<>]*>')

# Amending phrases, checked in order; Dutch puts the participle at the end ('wordt een lid toegevoegd')
# The Dutch participle comes at the end of the sentence ('wordt een lid toegevoegd'); a dot inside a number
# ('artikel I.2') does not end it
_SENTENCE = r'(?:[^.;:]|\.(?=\S))*'
ACTIONS = (
    (rf'\b(est|sont) (chaque fois )?(abrogée?s?|supprimée?s?)\b|\b(wordt|worden)\b{_SENTENCE}\bopgeheven\b', 'delete'),
    (rf'\b(est|sont) insérée?s?\b|\bil est inséré\b|\b(wordt|worden)\b{_SENTENCE}\bingevoegd\b', 'insert'),
    (r'\b(est|sont) (chaque fois )?(complétée?s?|ajoutée?s?)\b'
     rf'|\b(wordt|worden)\b{_SENTENCE}\b(aangevuld|toegevoegd)\b(?=\s*([,.:;]|$|luidende|als volgt|met|die|dat))',
     'add'),
    (rf'\b(est|sont) (chaque fois )?remplacée?s?\b|\b(wordt|worden)\b{_SENTENCE}\bvervangen\b', 'replace'),
    (r'\b(est|sont) modifiée?s?\b|modifications suivantes|volgende wijzigingen|\b(wordt|worden) gewijzigd\b', 'amend'),
)
# A general repeal of whatever is contrary ('... qui y sont contraires sont abrogés') amends no act
_DEROGATION = re.compile(r'\bcontraires?\b.*\babrogée?s?\b|\bstrijdig\w*\b.*\bopgeheven\b', re.IGNORECASE)
SUBTITLE_RANK = 1.5
# ... nor after a modal verb ('kunnen niet worden gewijzigd dan bij een wet')
_SUBORDINATE = re.compile(r"\b(lorsque|lorsqu'|quand|totdat|zodra|wanneer|indien|tenzij|kan|kunnen|mag|mogen|moet|"
                          r"moeten)\b[^,.;:]*", re.IGNORECASE)
DIVISIONS = {'livre': 'part', 'boek': 'part', 'partie': 'part', 'deel': 'part', 'titre': 'title', 'titel': 'title',
             'sous-titre': 'subtitle', 'ondertitel': 'subtitle', 'chapitre': 'chapter', 'hoofdstuk': 'chapter',
             'section': 'section', 'afdeling': 'section', 'sous-section': 'subsection', 'onderafdeling': 'subsection'}


def amendment_action(text: str) -> Optional[str]:
    """'L'article 3 ... est remplacé par ce qui suit :' -> 'replace'; '... wordt opgeheven.' -> 'delete'."""
    if _DEROGATION.search(text):
        return None
    # Not in quoted words, nor in a subordinate clause ('lorsque celle-ci est abrogée', 'totdat zij worden gewijzigd')
    text = _SUBORDINATE.sub('', re.sub(r'"[^"]*"|«[^»]*»|“[^”]*”', '""', text))
    for pattern, action in ACTIONS:
        if re.search(pattern, text, re.IGNORECASE):
            return action
    return None


def _amended_act(text: str, previous: Optional[str] = None) -> Optional[str]:
    """
    The act named in an amending instruction ('... de la loi du 8 décembre 1992 relative à ...').

    'du même arrêté' / 'van hetzelfde besluit' refer to the act named before (``previous``).
    """
    if re.search(r'\b(du même|de la même|van hetzelfde|van dezelfde)\b', text):
        return previous
    match = re.search(r"\b(?:de la |de l'|du |des |van de |van het )?((?:loi|arrêté|décret|ordonnance|Code|wet|besluit|"
                      r"decreet|ordonnantie|Wetboek|Codex)\b[^,;:]*)", text)
    return match.group(1).strip() if match else previous


_IMAGE = re.compile(r'^(Pour la consultation du tableau|Voor de raadpleging van de tabel|Zur Ansicht der Tabelle)')
_GLUED_ARTICLE = re.compile(r'\s((?:Article|Artikel|Art\.)\s+[\dIVXLC]\S*\s*\.\s.*)$')
_PLACE_DATE = re.compile(r"^(Donné à|Gegeven te|Fait à|Gedaan te|[A-Z][\w'’ .-]+, (le |den )?\d{1,2}(er)? \w+ \d{4})")


def _split_glued(lines: list[str]):
    """Lines with a heading and an article run together ('HOOFDSTUK 1. - ... Artikel I.1. ...'), split."""
    for line in lines:
        match = (_DIVISION.match(line) or _PRELIMINARY.match(line)) and _GLUED_ARTICLE.search(line)
        if match:
            yield line[:match.start()]
            yield match.group(1)
        else:
            yield line


QUOTES = ('«', '“', '"')


def _quote_delta(line: str, inside: bool) -> int:
    """How a line changes the depth of quoted text: guillemets and curly quotes pair up; a lone straight quote
    opens a quotation outside one and closes it inside."""
    delta = line.count('«') + line.count('“') - line.count('»') - line.count('”')
    if line.count('"') % 2:
        delta += -1 if inside else 1
    return delta


def _annex_title(line: str) -> dict[str, Optional[str]]:
    """'Annexe 2. Taux ...' -> num 'Annexe 2', heading 'Taux ...'."""
    match = re.match(r'^((?:Annexe|ANNEXE|Bijlage|BIJLAGE)(?:\s+(?!-)[\w/]+(?:er|re)?)?)\s*[.:\-–]?\s*(.*)$', line)
    if not match:
        return {'num': line, 'heading': None}
    return {'num': match.group(1), 'heading': match.group(2) or None}


def _conclusions(lines: list[str]) -> Optional[dict[str, Optional[str]]]:
    """The promulgation (up to the place and date) and the signatures."""
    if not lines:
        return None
    split = next((i for i, line in enumerate(lines) if i and _PLACE_DATE.match(line)), 1)
    return {'conclusion_text': ' '.join(lines[:split]), 'signature': ' '.join(lines[split:]) or None}


def _is_marker(sup: etree._Element) -> bool:
    """A Justel amendment marker: a red superscript number linking to its note."""
    return bool(sup.xpath('.//font[@color="red"] | .//a[@href="#t"] | .//span[contains(@style, "red")]'))


def _lines(element: etree._Element, anchors: bool = False) -> list[str]:
    """
    The text of an element as lines, at line breaks and block ends, without Justel's markers.

    ``anchors``: mark the lines that start at an anchor of Justel with ANCHOR.
    """
    copy = html.fromstring(html.tostring(element, encoding='unicode'))
    for sup in copy.xpath('.//sup'):
        if not _is_marker(sup):
            continue
        # '[<sup>1</sup> ...]<sup>1</sup>': drop the bracket with its marker
        previous, parent = sup.getprevious(), sup.getparent()
        if previous is not None:
            previous.tail = re.sub(r'[\[\]]\s*$', '', previous.tail or '')
        else:
            parent.text = re.sub(r'[\[\]]\s*$', '', parent.text or '')
        tail = sup.tail
        if previous is not None:
            previous.tail = (previous.tail or '') + (tail or '')
        else:
            parent.text = (parent.text or '') + (tail or '')
        parent.remove(sup)
    for node in copy.xpath('.//script | .//style | .//button | .//*[contains(@class, "no-print")]'):
        node.getparent().remove(node)
    parts: list[str] = []

    def walk(node: etree._Element) -> None:
        if not isinstance(node.tag, str):
            return
        if node.tag == 'tr':
            # A table row is one line, marked so that it joins the text above it
            cells = [' '.join(cell.text_content().split()) for cell in node.xpath('./td | ./th')]
            parts.append('\n' + ROW + ' | '.join(cell for cell in cells if cell) + '\n')
            return
        if node.tag == 'br' or (node.tag == 'a' and re.match(r'^(Art|LNK)', node.get('name') or '')):
            # Justel anchors each article and heading: they start a line
            parts.append('\n' + (ANCHOR if anchors and node.tag == 'a' else ''))
        if node.text and node.tag != 'br':
            parts.append(node.text)
        for child in node:
            walk(child)
            if child.tail:
                parts.append(child.tail)
        if node.tag in _BLOCKS:
            parts.append('\n')

    walk(copy)
    lines = []
    for line in ''.join(parts).split('\n'):
        anchored = line.startswith(ANCHOR)
        line = ' '.join(_INLINE_NOTE.sub('', line.lstrip(ANCHOR)).split())
        if line and line != ROW and not _IMAGE.match(line):
            lines.append(ANCHOR + line if anchored else line)
    return lines


class EJusticeParser(Parser):
    """Parses a Belgian act (Moniteur belge or Justel HTML) into legalJSON."""

    def parse(self, file: str, **options) -> 'EJusticeParser':
        try:
            root = html.parse(file).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read eJustice document {file}: {e}") from e
        if root is None:
            raise FileLoadError(f"{file} is empty")
        text = root.xpath('//div[@id="list-title-3"]')
        main = root.xpath('//main[contains(@class, "article-text")]')
        if text:
            self._read_justel(root, text[0])
        elif main:
            self._read_moniteur(root, main[0])
        else:
            raise FileLoadError(f"{file} holds no act text")
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read_justel(self, root: etree._Element, text: etree._Element) -> None:
        title = root.xpath('//div[@id="list-title-1"]//p[contains(@class, "list-item--title")]')
        if title:
            self.preface = re.sub(r'\s*\((NOTE|NOTA)\s*:.*$', '', ' '.join(title[0].text_content().split())) or None
        preamble = root.xpath('//div[@id="list-title-sw_prev"]')
        if preamble:
            self._read_opening(_lines(preamble[0])[1:])
        lines = _lines(text, anchors=True)[1:]
        self._read_body(lines, justel=True)
        signatures = root.xpath('//div[@id="list-title-sw_sign"]')
        if signatures:
            closing = _lines(signatures[0])[1:]
            if closing:
                self.conclusions = _conclusions(closing)

    def _read_moniteur(self, root: etree._Element, main: etree._Element) -> None:
        title = root.xpath('//p[contains(@class, "intro-text")]')
        if title:
            # Without the call of the footnote on the parliamentary documents
            self.preface = re.sub(r'\s*\(\d\)$', '', ' '.join(title[0].text_content().split())) or None
        lines = _lines(main)
        start = next((i for i, line in enumerate(lines) if self._starts_body(line)), len(lines))
        self._read_opening(lines[:start])
        self._read_body(lines[start:], justel=False)

    @staticmethod
    def _starts_body(line: str) -> bool:
        return bool(_ARTICLE.match(line) or _SOLE_ARTICLE.match(line) or _DIVISION.match(line)
                    or _PRELIMINARY.match(line))

    @staticmethod
    def _ends_quotation(line: str, article: Optional[dict[str, Any]], body: BodyBuilder) -> bool:
        """Whether a line in quoted text is the act's own: its closing formula, its next article or division."""
        if line.startswith(QUOTES):
            return False
        if _CLOSING.match(line) and line.startswith(('Promulguons', 'Kondigen')):
            return True

        def follows(number: Optional[str], last: Optional[str]) -> bool:
            return bool(number and last and number.isdigit() and last.isdigit() and int(number) == int(last) + 1)

        match = _ARTICLE.match(line)
        if match:
            return article is not None and follows(match.group('num'), article['token'])
        match = _DIVISION.match(line)
        if match:
            kind = DIVISIONS.get(match.group('kind').lower())
            last = next((c for c in reversed(body.chapters) if c['type'] == kind), None)
            return last is not None and follows(match.group('num'), eid_token(last['num']))
        return False

    def _read_opening(self, lines: list[str]) -> None:
        """The report to the King, the citations and the enacting formula."""
        formula: list[str] = []
        recitals: list[str] = []
        before: list[str] = []
        ended = False
        for line in lines:
            if _CITATION.match(line.lstrip('« ')) and not ended:
                recitals.append(line)
            elif ended and self.preface and line in self.preface:
                # The title, repeated after the enacting formula
                continue
            elif recitals and (_FORMULA_END.search(line) or re.match(r'^(Nous avons|Wij hebben|Arrête|Besluit)', line)):
                formula.append(line)
                ended = True
            elif recitals and not ended:
                # A citation running over several lines
                recitals.append(line)
            elif recitals or formula or re.match(r'^[A-Z]+, (Roi|Koning)|^(Le|La|Les|De|Het) .*(Gouvernement|Regering|'
                                                 r'Parlement|Collège|College|Conseil|Raad)', line, re.IGNORECASE):
                formula.append(line)
                ended = ended or bool(_FORMULA_END.search(line))
            else:
                before.append(line)
        if not formula and not recitals:
            formula = [line for line in before if not (self.preface and line in self.preface)]
            before = []
        if before:
            # The report to the King ('RAPPORT AU ROI', 'VERSLAG AAN DE KONING') precedes the act
            recitals = [' '.join(before)] + recitals
        self.recitals = [{'eId': f'rct_{n}', 'text': text} for n, text in enumerate(recitals, start=1)]
        self.formula = ' '.join(formula) or None

    def _read_body(self, lines: list[str], justel: bool) -> None:
        lines = list(_split_glued(lines))
        body = BodyBuilder()
        article: Optional[dict[str, Any]] = None
        annex: Optional[ChildrenBuilder] = None
        closing: list[str] = []
        quoting = 0
        in_note = False
        after_notes = False
        paragraphs = False
        last_act: list[Optional[str]] = [None]

        def flush() -> None:
            nonlocal article
            if article is not None:
                body.article(article['num'], None, article['children'].children, token=article['token'])
            article = None

        def add_line(text: str) -> None:
            nonlocal paragraphs
            children = article['children']
            match = _PARAGRAPH.match(text)
            if match:
                paragraphs = True
                child = children.add(text, number=match.group('num'),
                                     token=re.sub(r'(er|e)$', '', match.group('num')).replace('/', '-'))
            elif children.children and (_POINT.match(text) or paragraphs):
                children.extend(text)
                return
            else:
                child = children.add(text)
            action = amendment_action(text)
            if action:
                act = _amended_act(text, last_act[0])
                last_act[0] = act
                child['amendment'] = {'action': action, 'instruction': text, 'amended_act': act, 'quoted': []}

        for line in lines:
            if line.startswith(ANCHOR):
                # Justel anchors only the act's own articles and headings: a quotation
                # left open (a straight quote never closed) ends there
                line = line[len(ANCHOR):]
                quoting = 0
            if line.startswith(ROW):
                # A table row joins the child (or the annex) above it
                row = line[len(ROW):].strip()
                if annex is not None:
                    annex.add(row)
                elif article is not None:
                    article['children'].extend(row)
                elif closing:
                    closing.append(row)
                continue
            if quoting and self._ends_quotation(line, article, body):
                # A quotation left open (decret/2025/01/23/2025000875, article 31) ends at the closing
                # formula or at the act's next article or division
                quoting = 0
            if quoting:
                # Text quoted by an amendment, up to the closing guillemet
                children = article['children']
                current = children.children[-1] if children.children else None
                if current is not None and current.get('amendment') is not None:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': line.strip('«»“”" ')})
                children.extend(line)
                quoting = max(quoting + _quote_delta(line, True), 0)
                continue
            if justel and _JUSTEL_NOTE.match(line):
                in_note = True
                continue
            if in_note and not self._starts_body(line):
                continue
            in_note = False
            if closing and _NOTES.match(line):
                # The parliamentary references; annexes may still follow them
                after_notes = True
                continue
            if after_notes:
                if annex is None and not (_ANNEX.match(line) or _ANNEX_AFTER_NOTES.match(line)):
                    continue
                if annex is None or _ANNEX_AFTER_NOTES.match(line):
                    annex = ChildrenBuilder()
                    self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', **_annex_title(line),
                                         'children': annex.children})
                    continue
            if justel and _JUSTEL_ANNEX.match(line):
                flush()
                rest = _JUSTEL_ANNEX.match(line).group('rest')
                if annex is not None and not annex.children and self.annexes[-1]['heading'] is None:
                    # the annex a heading 'ANNEXE.' just opened
                    if rest:
                        self.annexes[-1].update(_annex_title(rest))
                    continue
                annex = ChildrenBuilder()
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}',
                                     **(_annex_title(rest) if rest else {'num': None, 'heading': None}),
                                     'children': annex.children})
                continue
            if justel and annex is None and _JUSTEL_ANNEXES.match(line) and (article is not None or body.articles):
                continue
            if annex is not None:
                if _ANNEX.match(line):
                    annex = ChildrenBuilder()
                    self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', **_annex_title(line),
                                         'children': annex.children})
                elif re.match(r'^(Vu pour être annexé|Gezien om gevoegd te worden)', line):
                    continue
                elif self.annexes[-1]['heading'] is None and not annex.children and len(line) < 300:
                    self.annexes[-1]['heading'] = line
                else:
                    annex.add(line)
                continue
            if (article is not None or body.articles) and _ANNEX.match(line):
                flush()
                annex = ChildrenBuilder()
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', **_annex_title(line),
                                     'children': annex.children})
                continue
            if closing or (_CLOSING.match(line) and (article is not None or body.articles)):
                flush()
                closing.append(line)
                continue
            if line.startswith(QUOTES) and article is not None:
                children = article['children']
                current = children.children[-1] if children.children else None
                if current is not None and current.get('amendment') is not None:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': line.strip('«»“”" ')})
                children.extend(line)
                quoting = max(_quote_delta(line, False), 0)
                continue
            match = _DIVISION.match(line) or _PRELIMINARY.match(line)
            if match and not line.startswith(QUOTES):
                flush()
                kind = match.group('kind').split()[-1].lower()
                number = line[:line.index(match.group('heading'))].rstrip(' .-–')
                groups = match.groupdict()
                token = groups.get('num') and groups['num'] + re.sub(r'[\s/]', '', groups.get('suffix') or '').lower()
                preliminary = groups.get('special') or re.search(r'PRELIMINAIRE|VOORAFGAAND|INLEIDEND', line.upper())
                token = token or ('0' if preliminary else None)
                type_ = DIVISIONS.get(kind, 'chapter')
                # a sub-title (loi 2018/07/30/2018040581, titre 3) sits between the title and its chapters
                body.division(type_, number, heading=match.group('heading'), token=token,
                              rank=SUBTITLE_RANK if type_ == 'subtitle' else None)
                continue
            match = _ARTICLE.match(line) or _SOLE_ARTICLE.match(line)
            if match:
                flush()
                groups = match.groupdict()
                number = groups.get('num')
                article = {'num': line[:len(line) - len(match.group('rest'))].strip(), 'children': ChildrenBuilder(),
                           'token': re.sub(r'[.:/]', '-', re.sub(r'(er|re|e)$', '', number)).replace(' ', '')
                           if number else '1'}
                paragraphs = False
                if match.group('rest'):
                    add_line(match.group('rest'))
                    quoting = max(_quote_delta(match.group('rest'), False), 0)
                continue
            if article is not None:
                add_line(line)
                quoting = max(_quote_delta(line, False), 0)
        flush()
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        if closing:
            self.conclusions = _conclusions(closing)
