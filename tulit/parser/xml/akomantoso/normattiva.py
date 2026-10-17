"""
Normattiva Akoma Ntoso Parser

Parser for the Akoma Ntoso export of Normattiva, the official portal of
Italian legislation (Istituto Poligrafico e Zecca dello Stato for the
Presidency of the Council of Ministers). Normattiva exports an act as in
force on any date, the text as published included.

Differences from standard Akoma Ntoso handled here:

- the preface is a ``docType`` / ``docDate`` / ``docNumber`` / ``docTitle``
  paragraph ('DECRETO LEGISLATIVO 10 agosto 2018, n. 101 - Disposizioni ...');
- the preamble holds the initial formula ('IL PRESIDENTE DELLA REPUBBLICA'),
  the citations ('Visti ...', 'Acquisito ...') partly as loose paragraphs,
  and the final formula ('E M A N A il seguente decreto legislativo:');
- the editorial notes ('N O T E', 'Note all'art. 2') sit in ``section``
  elements inside articles and are left out;
- the conclusions are a formula and paragraphs (place and date, signatures)
  without a signature container;
- attachments (e.g. the articles of a ratified treaty) become annexes.

Articles that amend other acts carry a structured ``amendment``.
"""
import re
from typing import Optional

from lxml import etree

from tulit.parser.xml.akomantoso.base import AkomaNtosoParser

# Amending phrases, checked in order
ACTIONS = (
    (r"\b(?:e'|è|sono) (?:abrogat[oaie]|soppress[oaie])\b", 'delete'),
    (r"\b(?:e'|è|sono) (?:sostituit[oaie])\b|\bsostituire\b", 'replace'),
    (r"\b(?:e'|è|sono) (?:inserit[oaie]|premess[oaie])\b", 'insert'),
    (r"\b(?:e'|è|sono) (?:aggiunt[oaie])\b", 'add'),
    (r"\b(?:e'|è|sono) (?:modificat[oaie])\b|\bapportate le seguenti modificazioni\b", 'amend'),
)
_ACT = re.compile(r"((?:decreto legislativo|decreto-legge|decreto del Presidente della Repubblica|legge costituzionale|"
                  r"legge|regio decreto|decreto ministeriale)\s+\d{1,2}[°º]?\s+\w+\s+\d{4},\s*n\.\s*\d+\w*)",
                  re.IGNORECASE)


def amendment_action(text: str) -> Optional[str]:
    """'All'articolo 2 ... sono aggiunte le seguenti parole: ...' -> 'add'; '... e' abrogato.' -> 'delete'."""
    for pattern, action in ACTIONS:
        if re.search(pattern, text, re.IGNORECASE):
            return action
    return None


def _text(element: etree._Element) -> str:
    return ' '.join(''.join(element.itertext()).split())


class NormattivaAKNParser(AkomaNtosoParser):
    """Parses an act exported by Normattiva as Akoma Ntoso into legalJSON."""

    def get_preface(self) -> None:
        preface = self.root.find('.//akn:preface', namespaces=self.namespaces)
        if preface is None:
            return super().get_preface()

        def part(name: str) -> str:
            found = preface.find(f'.//akn:{name}', namespaces=self.namespaces)
            return _text(found) if found is not None else ''

        kind, date, number, title = part('docType'), part('docDate'), part('docNumber'), part('docTitle')
        # The Gazette's code at the end of the title ('(18G00129)') is not part of it
        title = re.sub(r'\s*\(\d{2,3}[A-Z]\d{4,5}\)\s*$', '', title)
        # The Constitution has neither date nor number ('0')
        number = '' if number.strip('0 ') == '' else number
        heading = ' '.join(filter(None, [kind, f'{date}, n. {number}' if number and date else date]))
        if title.upper().startswith(heading.upper()):
            heading = ''
        self.preface = ' - '.join(filter(None, [heading, title])) or None

    def get_formula(self) -> None:
        formula = self.root.find('.//akn:preamble/akn:formula[@name="formulaInizialePreambolo"]',
                                 namespaces=self.namespaces)
        if formula is None:
            formula = self.root.find('.//akn:preamble/akn:formula', namespaces=self.namespaces)
        self.formula = _text(formula) if formula is not None else None

    def get_citations(self) -> None:
        """The citations, and the paragraphs among them ('Acquisito il parere ...', 'Sulla proposta ...')."""
        preamble = self.root.find('.//akn:preamble', namespaces=self.namespaces)
        self.citations = []
        if preamble is None:
            return
        for child in preamble:
            if not isinstance(child.tag, str):
                continue
            local = etree.QName(child).localname
            if local == 'citations':
                texts = [_text(c) for c in child.findall('akn:citation', namespaces=self.namespaces)]
            elif local == 'p':
                texts = [_text(child)]
            else:
                continue
            for text in texts:
                if text:
                    self.citations.append({'eId': f'cit_{len(self.citations) + 1}', 'text': text})

    def get_recitals(self) -> None:
        self.recitals = []

    def get_preamble_final(self) -> None:
        final = self.root.find('.//akn:preamble/akn:formula[@name="formulaFinalePreambolo"]',
                               namespaces=self.namespaces)
        self.preamble_final = _text(final) if final is not None else None

    def get_body(self) -> None:
        super().get_body()
        if self.body is None:
            return
        # Editorial notes ('N O T E', 'Note all'art. 2') are sections inside articles
        for section in self.body.xpath('.//akn:article//akn:section', namespaces=self.namespaces):
            section.getparent().remove(section)

    def get_articles(self) -> None:
        super().get_articles()
        act: Optional[str] = None
        for article in self.articles:
            for child in article['children']:
                child.setdefault('amendment', None)
                text = child.get('text') or ''
                # The instruction without the text it quotes
                instruction = ' '.join(re.sub(r'«[^«»]*»', '«…»', text).split())
                action = amendment_action(instruction)
                found = _ACT.search(instruction)
                if found:
                    act = found.group(1)
                elif not re.search(r'\b(citato|medesimo|stesso) (decreto|codice|legge)\b', instruction):
                    act = act if action else None
                if action:
                    child['amendment'] = {
                        'action': action,
                        'instruction': instruction,
                        'amended_act': act,
                        'quoted': [{'kind': 'text', 'text': q.strip()} for q in re.findall(r'«([^«»]+)»', text)],
                    }

    def get_conclusions(self) -> None:
        conclusions = self.root.find('.//akn:conclusions', namespaces=self.namespaces)
        if conclusions is None:
            return
        formula = conclusions.find('akn:formula', namespaces=self.namespaces)
        paragraphs = [_text(p) for p in conclusions.findall('akn:p', namespaces=self.namespaces)]
        paragraphs = [p for p in paragraphs if p]
        place = [p for p in paragraphs if re.match(r'^Dato a |^Data a ', p)]
        rest = [p for p in paragraphs if p not in place]
        text = ' '.join(filter(None, [_text(formula) if formula is not None else '', *place]))
        self.conclusions = {'conclusion_text': text or None, 'signature': ' '.join(rest) or None}

    def parse(self, file: str, **options) -> 'NormattivaAKNParser':
        super().parse(file, **options)
        self._read_attachments()
        return self

    def _read_attachments(self) -> None:
        """Each attached document (an annex, or an article of a ratified treaty) as an annex."""
        if self.root is None:
            return
        self.annexes = []
        for doc in self.root.xpath('.//akn:attachment/akn:doc', namespaces=self.namespaces):
            body = doc.find('akn:mainBody', namespaces=self.namespaces)
            if body is None:
                continue
            paragraphs = [_text(p) for p in body.iter(f'{{{self.namespaces["akn"]}}}p')]
            children = [{'eId': f'unp_{n}', 'text': text, 'amendment': None}
                        for n, text in enumerate((t for t in paragraphs if t), start=1)]
            self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': doc.get('name'), 'heading': None,
                                 'children': children})
