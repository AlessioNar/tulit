"""
Finlex Akoma Ntoso Parser

Finlex (Finland) publishes statutes in Akoma Ntoso 3.0 with its own
containers in the body:

- the enacting clause (formula) of an amending statute lists in blocks what
  it repeals, amends and inserts ('kumotaan', 'muutetaan', 'lisätään');
- ``hcontainer[@name="conclusions"]`` holds the preparatory works
  (esityöt: 'HE 1/1998', 'PeVM 10/1998', ...) and the signatures; they
  become the conclusions;
- in a consolidated text, ``hcontainer[@name="amendmentEntryIntoForceAndApplianceProvisions"]``
  holds the entry into force of each amending statute
  ('27.11.2020/869: Tämä laki tulee voimaan ...'); it becomes an annex;
- ``hcontainer[@name="attachment"]`` (liite) becomes an annex, a line per
  paragraph or table row;
- a statute without sections (an asetus of a few sentences) has its text in
  ``hcontainer[@name="statuteTextWrapper"]``: it becomes one unnumbered article.
"""
from typing import Optional

from lxml import etree

from tulit.parser.structure import element_text
from tulit.parser.xml.akomantoso.base import AkomaNtosoParser

BLOCK_TAGS = ('p', 'heading', 'num', 'content', 'signature', 'role', 'person', 'hcontainer')


class FinlexAKNParser(AkomaNtosoParser):
    """Parser for Finnish statutes in Finlex's Akoma Ntoso."""

    def _containers(self, name: str) -> list:
        return self.root.findall(f'.//akn:hcontainer[@name="{name}"]', namespaces=self.namespaces)

    def _text(self, element: Optional[etree._Element]) -> Optional[str]:
        return element_text(element, BLOCK_TAGS) or None if element is not None else None

    def get_formula(self) -> None:
        """The enacting clause, with what an amending statute repeals, amends and inserts ('kumotaan ...')."""
        formula = self.root.find('.//akn:preamble/akn:formula', namespaces=self.namespaces)
        if formula is None:
            return super().get_formula()
        self.formula = element_text(formula, BLOCK_TAGS + ('block', 'blockContainer')) or None
        return self.formula

    def get_conclusions(self) -> None:
        conclusions = self._containers('conclusions')
        if not conclusions:
            return super().get_conclusions()
        preliminary = conclusions[0].find('.//akn:hcontainer[@name="preliminaryWork"]', namespaces=self.namespaces)
        signatures = conclusions[0].find('.//akn:hcontainer[@name="signatures"]', namespaces=self.namespaces)
        works = [self._text(p) for p in preliminary.findall('.//akn:p', namespaces=self.namespaces)] \
            if preliminary is not None else []
        self.conclusions = {'conclusion_text': '; '.join(w for w in works if w) or None,
                            'signature': self._text(signatures)}

    def _lines(self, container: etree._Element) -> list[str]:
        """The text of a container a paragraph (or table row) at a time."""
        lines = []
        for block in container.iter():
            if not isinstance(block.tag, str):
                continue
            name = etree.QName(block).localname
            in_row = any(etree.QName(a).localname == 'tr' for a in block.iterancestors())
            if name == 'tr' or (name == 'p' and not in_row):
                text = element_text(block, BLOCK_TAGS + ('td', 'th'))
                if text:
                    lines.append(text)
        return lines

    def get_articles(self) -> None:
        super().get_articles()
        if self.articles:
            return
        for container in self._containers('statuteTextWrapper'):
            lines = self._lines(container)
            if lines:
                self.articles.append({'eId': 'art_1', 'num': None, 'heading': None, 'parent': None,
                                      'children': [{'eId': f'unp_{n}', 'text': text}
                                                   for n, text in enumerate(lines, start=1)]})
                self.structure.append({'eId': 'art_1', 'type': 'article'})

    def get_annexes(self) -> None:
        self.annexes = []
        for attachment in self._containers('attachment'):
            lines = self._lines(attachment)
            if lines:
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': lines[0], 'heading': None,
                                     'children': [{'eId': f'unp_{n}', 'text': text}
                                                  for n, text in enumerate(lines[1:], start=1)]})
        for container in self._containers('amendmentEntryIntoForceAndApplianceProvisions'):
            children = []
            for n, provision in enumerate(container.findall('akn:hcontainer', namespaces=self.namespaces), start=1):
                text = self._text(provision)
                if text:
                    children.append({'eId': provision.get('eId') or f'unp_{n}', 'text': text})
            heading = container.find('akn:heading', namespaces=self.namespaces)
            self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': None,
                                 'heading': self._text(heading), 'children': children})

    def parse(self, file: str, **options) -> 'FinlexAKNParser':
        super().parse(file, **options)
        if getattr(self, 'root', None) is not None:
            self.get_annexes()
        return self
