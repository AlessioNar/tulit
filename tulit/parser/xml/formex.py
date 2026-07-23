import os
import re
import json
import argparse
import logging
from copy import deepcopy
from typing import Optional, Any
from lxml import etree

# Amendment instruction verbs, in a syntactic frame so that incidental words
# ("value added tax") never match: "is replaced by", "are hereby deleted",
# "shall be inserted", "is amended as follows", ...
_AMEND_VERB_RE = re.compile(
    r"(?:is|are|shall be)\s+(?:hereby\s+)?"
    r"(replaced|substituted|inserted|added|deleted|repealed|amended)\b",
    re.IGNORECASE,
)

_AMEND_ACTIONS = {
    'replaced': 'replace', 'substituted': 'replace',
    'inserted': 'insert', 'added': 'add',
    'deleted': 'delete', 'repealed': 'delete',
    'amended': 'amend',
}

# EU act citations, both numbering families:
#   "Implementing Regulation (EU) No 540/2011", "Regulation (EU) 2019/124"
#   "Directive 2009/128/EC", "Decision 2011/172/CFSP"
_CITED_ACT_RE = re.compile(
    r"(?:Commission\s+|Council\s+|European Parliament and of the Council\s+)?"
    r"(?:Implementing\s+|Delegated\s+)?"
    r"(?:Regulation|Directive|Decision|Guideline)\s+"
    r"(?:\((?:EU|EC|EEC|Euratom|EU,\s*Euratom)\)\s+(?:No\s+)?\d{1,4}/\d{2,4}"
    r"|\d{2,4}/\d{1,4}/(?:EU|EC|EEC|CFSP|Euratom))"
)

from tulit.parser.xml.xml import XMLParser
from tulit.parser.parser import LegalJSONValidator, create_formex_normalizer
from tulit.parser.strategies.article_extraction import FormexArticleStrategy

class Formex4Parser(XMLParser):
    """
    A parser for processing and extracting content from Formex XML files.

    The parser handles XML documents following the Formex schema for legal documents.
    It inherits from the XMLParser class and provides methods to extract various components
    like preface, preamble, chapters, articles, and conclusions.
    """

    def __init__(self) -> None:
        """
        Initializes the Formex4Parser object with the Formex namespace.
        """
        # Initialize with Formex-specific normalizer
        super().__init__(normalizer=create_formex_normalizer())

        # Define the namespace mapping
        self.namespaces = {
            'fmx': 'http://formex.publications.europa.eu/schema/formex-05.56-20160701.xd'
        }
        
        # Initialize article extraction strategy
        self.article_strategy = FormexArticleStrategy()
    
    def get_preface(self) -> None:
        """
        Extracts the preface from the document. It is assumed that the preface is contained within
        the TITLE and P elements.
        
        """
        
        return super().get_preface(preface_xpath='.//TITLE', paragraph_xpath='.//P')
    
    def get_preamble(self) -> None:
        """
        Extracts the preamble from the document. It is assumed that the preamble is contained within
        the PREAMBLE element, while notes are contained within the NOTE elements.
        
        """
        
        return super().get_preamble(preamble_xpath='.//PREAMBLE', notes_xpath='.//NOTE')
    
    def get_formula(self) -> None:
        """
        Extracts the formula from the preamble. The formula is assumed to be contained within the
        PREAMBLE.INIT element.
        
        Returns
        -------
        str
            Formula text from the preamble.
        """
        self.formula = self.preamble.findtext('PREAMBLE.INIT')
        return self.formula

    
    def get_citations(self) -> None:
        """
        Extracts citations from the preamble. Citations are assumed to be contained within the GR.VISA
        and VISA elements. The citation identifier is set as the index of the citation in the preamble.

        Returns
        -------
        list
            List of dictionaries containing citation data with keys:
            - 'eId': Citation identifier, which is the index of the citation in the preamble
            - 'text': Citation text
        """
        def extract_eId(citation, index):
            return f'cit_{index + 1}'
            
        
        return super().get_citations(
            citations_xpath='.//GR.VISA',
            citation_xpath='.//VISA',
            extract_eId=extract_eId
        )
    
    def get_recitals(self) -> None:
        """
        Extracts recitals from the preamble. Recitals are assumed to be contained within the GR.CONSID
        and CONSID elements. The introductory recital is extracted separately. The recital identifier
        is set as the index of the recital in the preamble.

        Returns
        -------
        list or None
            List of dictionaries containing recital text and eId for each
            recital. Returns None if no recitals are found.
        """
        
        def extract_intro(recitals_section):        
            intro_text = self.preamble.findtext('.//GR.CONSID.INIT')
            self.recitals_intro = intro_text            
        
        def extract_eId(recital):
            eId = recital.findtext('.//NO.P')
            # Remove () and return eId in the format rct_{number}
            eId = eId.strip('()')  # Remove parentheses
            return f'rct_{eId}'
            
        return super().get_recitals(
            recitals_xpath='.//GR.CONSID', 
            recital_xpath='.//CONSID',
            text_xpath='.//TXT',
            extract_intro=extract_intro,
            extract_eId=extract_eId
        )
    
    def get_preamble_final(self) -> None:
        """
        Extracts the final preamble text from the document. The final preamble text is assumed to be
        contained within the PREAMBLE.FINAL element.
        """
        
        return super().get_preamble_final(preamble_final_xpath='.//PREAMBLE.FINAL')

    def get_body(self) -> None:
        """
        Extracts the body section from the document. The body is assumed to be contained within the
        ENACTING.TERMS element.
        """
        return super().get_body('.//ENACTING.TERMS')
    
    def get_chapters(self) -> None:
        """
        Extracts chapter information from the document. Chapter numbers and headings are assumed to be
        contained within the TITLE element. The chapter identifier is set as the index of the chapter
        in the document.

        Returns
        -------
        list
            List of dictionaries containing chapter data with keys:
            - 'eId': Chapter identifier
            - 'chapter_num': Chapter number
            - 'chapter_heading': Chapter heading text
        """
        def extract_eId(chapter, index):
            return f'cpt_{index+1}'
        
        def get_headings(chapter):
            if len(chapter.findall('.//HT')) > 0:
                chapter_num = chapter.findall('.//HT')[0]
                chapter_num = "".join(chapter_num.itertext()).strip()  # Ensure chapter_num is a string
                if len(chapter.findall('.//HT')) > 1:      
                    chapter_heading = chapter.findall('.//HT')[1]
                    chapter_heading = "".join(chapter_heading.itertext()).strip()
                else:
                    return None, None
            else: 
                return None, None
                                
            return chapter_num, chapter_heading
        
        
        return super().get_chapters(
            chapter_xpath='.//TITLE',
            num_xpath='.//HT',
            heading_xpath='.//HT',
            extract_eId=extract_eId,
            get_headings=get_headings
        )
        
            
    def get_articles(self) -> None:
        """
        Extracts articles from the ENACTING.TERMS section using FormexArticleStrategy.
        
        This method delegates article extraction to the strategy pattern,
        reducing code duplication and improving testability.

        Returns
        -------
        list
            Articles with identifier and content.
        """
        self.articles = []
        
        if self.body is not None:
            # Use strategy for extraction
            self.articles = self.article_strategy.extract_articles(
                self.body,
                remove_notes=True
            )
            
            # Add article-specific fields (heading from STI.ART) and
            # structured amendment objects, uniform with annex children
            for article in self.articles:
                article_elem = self.body.xpath(
                    f".//ARTICLE[@IDENTIFIER][starts-with(@IDENTIFIER, '{article['eId'][4:]}')"
                    f" or starts-with(@IDENTIFIER, '3{article['eId'][4:]}')]"
                )[0]
                article['heading'] = (
                    article_elem.findtext('.//STI.ART') or
                    article_elem.findtext('.//STI.ART//P')
                )
                self._attach_article_amendments(article, article_elem)
            
            # Standardize children numbering to 001.001 format
            self._standardize_children_numbering()
            
            return self.articles
        else:
            print('No enacting terms XML tag has been found')
            return []
            
    def _extract_elements(self, parent: etree._Element, xpath: str, children: list[dict[str, Any]]) -> None:
        """
        Helper method to extract text and metadata from elements.

        Parameters
        ----------
        parent : lxml.etree._Element
            The parent element to search within.
        xpath : str
            The XPath expression to locate the elements.
        children : list
            The list to append the extracted elements to.
        """
        elements = parent.findall(xpath)
        for index, element in enumerate(elements):
            
            text = self.clean_text(element)
            
            if text is not None and text != '' and text != ';':
                child = {
                    "eId": element.get("IDENTIFIER") or element.get("ID") or element.get("NO.P") or (str(len(children)+1).zfill(3)) or str(index).zfill(3),
                    "text": text, 
                    "amendment": False                  
                }
                children.append(child)
    
    def _attach_article_amendments(self, article: dict[str, Any], article_elem: etree._Element) -> None:
        """
        Replaces the boolean 'amendment' of article children with the same
        structured amendment object used for annex children (or None).

        The elements are re-selected with the same XPath logic the article
        strategy uses, so children and elements pair up positionally; if the
        counts diverge, a text-only analysis is applied instead.
        """
        if article_elem.xpath('.//QUOT.S | .//QUOT.START'):
            elems = article_elem.xpath('.//ALINEA[not(ancestor::QUOT.S)]')
        elif article_elem.xpath('.//PARAG[not(ancestor::QUOT.S)]'):
            elems = article_elem.xpath('.//PARAG[not(ancestor::QUOT.S)]')
        else:
            elems = article_elem.xpath('.//ALINEA')

        if len(elems) == len(article['children']):
            for child, elem in zip(article['children'], elems):
                child['amendment'] = self._analyze_amendment(elem)
        else:
            for child in article['children']:
                text = child.get('text') or ''
                action = self._amendment_action(text)
                child['amendment'] = ({
                    'action': action,
                    'instruction': text,
                    'amended_act': self._cited_act(text),
                    'quoted': [],
                } if action else None)

    def _standardize_children_numbering(self) -> None:
        """
        Standardize article children numbering to format: 001.001, 001.002, etc.
        where the first number is the article number and the second is the child index.
        """
        import re
        for article in self.articles:
            # Extract article number from eId (format: art_1 -> 1)
            article_num_match = re.search(r'art_(\d+)', article['eId'])
            article_num = int(article_num_match.group(1)) if article_num_match else 0
            
            # Renumber all children with standardized format
            for idx, child in enumerate(article['children'], start=1):
                child['eId'] = f"{article_num:03d}.{idx:03d}"
    
    def get_conclusions(self) -> None:
        """
        Extracts conclusions from the document. The conclusion text is assumed to be contained within the FINAL
        section of the document. The signature details are assumed to be contained within the SIGNATURE element.
        

        Returns
        -------
        dict
            Dictionary containing the conclusion text and signature details.
        """
        self.conclusions = {}
        final_section = self.root.find('.//FINAL')
        if final_section is not None:
            conclusion_text = "".join(final_section.findtext('.//P')).strip()
            self.conclusions['conclusion_text'] = conclusion_text

            signature_section = final_section.find('.//SIGNATURE')
            if signature_section is not None:
                place = signature_section.findtext('.//PL.DATE/P').strip()
                date = signature_section.findtext('.//PL.DATE/P/DATE')
                signatory = signature_section.findtext('.//SIGNATORY/P/HT')
                title = signature_section.findtext('.//SIGNATORY/P[2]/HT')

                self.conclusions['signature'] = {
                    'place': place,
                    'date': date,
                    'signatory': signatory,
                    'title': title
                }
        return self.conclusions
        

    def get_annexes(self, annex_files: list[str]) -> list[dict[str, Any]]:
        """
        Extracts annexes from a list of Formex annex files.

        In Formex, each annex is stored in a separate file whose root element is
        ``ANNEX``. Each annex contains a ``TITLE`` (with ``TI`` for the annex number
        and ``STI`` for the heading) and a ``CONTENTS`` element holding the body.

        Parameters
        ----------
        annex_files : list of str
            Paths to Formex annex files (root element ``ANNEX``), in document order.

        Returns
        -------
        list
            List of dictionaries containing annex data with keys:
            - 'eId': Annex identifier (e.g. 'anx_1')
            - 'num': Annex number/title (e.g. 'ANNEX I')
            - 'heading': Annex subtitle, or None
            - 'children': List of {'eId', 'text'} content blocks
        """
        self.annexes = []
        for index, annex_file in enumerate(annex_files, start=1):
            try:
                tree = etree.parse(annex_file)
            except Exception as e:
                self.logger.warning(f"Could not parse annex file {annex_file}: {e}")
                continue

            annex_root = tree.getroot()
            base_dir = os.path.dirname(os.path.abspath(annex_file))
            annex = self._extract_annex(annex_root, index, base_dir=base_dir)
            if annex is not None:
                self.annexes.append(annex)

        return self.annexes

    def _resolve_inclusions(self, element: etree._Element, base_dir: Optional[str], _depth: int = 0) -> None:
        """
        Replaces ``INCL.ELEMENT`` references with the content of the referenced file.

        Formex documents can externalise content (e.g. quoted sub-documents in
        annexes) into separate files referenced through
        ``<INCL.ELEMENT FILEREF="..."/>``. This method parses each referenced
        file found under ``element`` and grafts its content in place of the
        reference so that text extraction sees the full annex body.

        Parameters
        ----------
        element : lxml.etree._Element
            Subtree in which to resolve inclusions, modified in place.
        base_dir : str or None
            Directory against which FILEREF values are resolved. If None,
            inclusions are left untouched.
        _depth : int
            Internal recursion guard for nested inclusions.
        """
        if base_dir is None or _depth > 2:
            return

        # INCL.ELEMENT inside BIB.INSTANCE is a manifest declaration, not a
        # content reference — only resolve inclusions in the document body.
        for incl in element.xpath('.//INCL.ELEMENT[not(ancestor::BIB.INSTANCE)]'):
            fileref = incl.get('FILEREF')
            if not fileref:
                continue
            path = os.path.join(base_dir, fileref)
            if not os.path.exists(path):
                self.logger.warning(f"Included file not found: {path}")
                continue
            try:
                included_root = etree.parse(path).getroot()
            except Exception as e:
                self.logger.warning(f"Could not parse included file {path}: {e}")
                continue

            # An included ANNEX contributes only its CONTENTS: its own TITLE
            # would duplicate the referencing annex's title. If the host annex
            # has no title of its own, it adopts the included one instead.
            if included_root.tag == 'ANNEX':
                incl_title = included_root.find('TITLE')
                if (_depth == 0 and element.tag == 'ANNEX'
                        and element.find('TITLE') is None and incl_title is not None):
                    element.insert(0, incl_title)
                included_contents = included_root.find('.//CONTENTS')
                if included_contents is not None:
                    included_root = included_contents

            # Bibliographic metadata of the included document is not content
            for bib in included_root.findall('.//BIB.INSTANCE') + included_root.findall('.//BIB.DOC'):
                bib_parent = bib.getparent()
                if bib_parent is not None:
                    bib_parent.remove(bib)

            self._resolve_inclusions(included_root, base_dir, _depth + 1)

            parent = incl.getparent()
            if parent is not None:
                included_root.tail = incl.tail
                parent[parent.index(incl)] = included_root

    def _extract_annex(self, annex_root: etree._Element, index: int, base_dir: Optional[str] = None) -> Optional[dict[str, Any]]:
        """
        Extracts a single annex from an ANNEX root element.

        Parameters
        ----------
        annex_root : lxml.etree._Element
            The ANNEX root element.
        index : int
            1-based position of the annex, used for eId and child numbering.
        base_dir : str, optional
            Directory of the annex file, used to resolve INCL.ELEMENT
            references to external content files.

        Returns
        -------
        dict or None
            Annex dictionary, or None if the element is not an annex.
        """
        if annex_root is None or annex_root.tag != 'ANNEX':
            return None

        self._resolve_inclusions(annex_root, base_dir)

        title = annex_root.find('.//TITLE')
        num = None
        heading = None
        if title is not None:
            ti = title.find('TI')
            sti = title.find('STI')
            if ti is not None:
                num = self._title_text(ti)
            if sti is not None:
                heading = self._title_text(sti)

        children = []
        contents = annex_root.find('.//CONTENTS')
        if contents is not None:
            children = self._extract_annex_children(contents, index)

        return {
            'eId': f'anx_{index}',
            'num': num,
            'heading': heading,
            'children': children,
        }

    def _extract_annex_children(self, contents: etree._Element, annex_index: int) -> list[dict[str, Any]]:
        """
        Extracts content blocks from an annex CONTENTS element.

        The output is uniform with article children: each block becomes a
        ``{'eId': '<annex:03d>.<child:03d>', 'text': ..., 'amendment': ...}``
        dictionary, matching the standardized ``001.001`` numbering that
        article children receive.
        Lists are expanded so every item (with its number) is its own child,
        grouped sequences contribute their heading and their blocks, and
        tables additionally carry a structured ``'table'`` key with
        ``'caption'``, ``'rows'`` and ``'notes'``.

        ``'amendment'`` is ``None`` for ordinary content, and a structured
        object for children that amend another act (see
        :meth:`_analyze_amendment`). The full readable text — including
        quoted amendment payloads — always remains in ``'text'``.

        Parameters
        ----------
        contents : lxml.etree._Element
            The CONTENTS element of an annex.
        annex_index : int
            1-based position of the parent annex.

        Returns
        -------
        list
            List of child dictionaries.
        """
        children: list[dict[str, Any]] = []

        for block in self._iter_annex_blocks(contents):
            text = self._render_annex_text(block)
            if not text:
                continue

            # A quoted block following an instruction that ends with ':' is
            # that instruction's payload — attach it instead of emitting a
            # separate child (mirrors the NP > TXT + QUOT.S pattern used
            # when the quote is a sibling rather than nested).
            if (block.tag == 'QUOT.S' and children
                    and children[-1]['text'].rstrip().endswith(':')):
                prev = children[-1]
                if prev['amendment'] is None:
                    prev['amendment'] = {
                        'action': self._amendment_action(prev['text']),
                        'instruction': prev['text'],
                        'amended_act': self._cited_act(prev['text']),
                        'quoted': [],
                    }
                prev['amendment']['quoted'].append(
                    {'kind': 'structure', 'children': self._quoted_children(block)})
                prev['text'] = f"{prev['text']} {text}"
                continue

            child: dict[str, Any] = {
                'eId': f'{annex_index:03d}.{len(children) + 1:03d}',
                'text': text,
                'amendment': self._analyze_amendment(block),
            }
            if block.tag == 'TBL':
                child['table'] = {
                    'caption': self._table_caption(block),
                    'rows': self._table_rows(block),
                    'notes': self._table_notes(block),
                }
            children.append(child)
        return children

    def _iter_annex_blocks(self, element: etree._Element):
        """
        Yields paragraph-level blocks of an annex in document order.

        Containers (LIST, DLIST, GR.SEQ, grafted CONTENTS/DOC) are unwrapped
        so each item, heading, or nested block is yielded individually; leaf
        blocks (P, NP, TBL, DLIST.ITEM, QUOT.S, ...) are yielded as-is.
        """
        for node in element:
            if not isinstance(node.tag, str):
                continue
            tag = node.tag
            if tag == 'LIST':
                for item in node.findall('ITEM'):
                    yield from self._iter_annex_blocks(item)
            elif tag == 'DLIST':
                yield from node.findall('DLIST.ITEM')
            elif tag in ('GR.SEQ', 'GR.ANNOTATION', 'CONTENTS', 'DOC'):
                yield from self._iter_annex_blocks(node)
            elif tag in ('BIB.INSTANCE', 'BIB.DOC'):
                continue
            else:
                yield node

    def _render_annex_text(self, element: etree._Element) -> str:
        """
        Renders an annex block as readable text.

        Numbered points keep their number separated from the body, quoted
        amendment blocks are wrapped in quotes, tables are rendered row by
        row with cell separators, and definition list items join term and
        definition.
        """
        tag = element.tag

        if tag == 'TBL':
            caption = self._table_caption(element)
            rows = [' | '.join(row) for row in self._table_rows(element)]
            notes = self._table_notes(element)
            return '\n'.join(([caption] if caption else []) + rows + notes)

        if tag == 'NP':
            parts = []
            no_p = element.find('NO.P')
            if no_p is not None:
                # Raw text: the normalizer would strip numbers like '(1)'
                num = ' '.join(''.join(no_p.itertext()).split())
                if num:
                    parts.append(num)
            for sub in element:
                if not isinstance(sub.tag, str) or sub.tag == 'NO.P':
                    continue
                rendered = self._render_annex_text(sub)
                if rendered:
                    parts.append(rendered)
            return ' '.join(parts)

        if tag == 'TITLE':
            return self._title_text(element) or ''

        if tag == 'DLIST.ITEM':
            term = element.find('TERM')
            definition = element.find('DEFINITION')
            parts = [self.clean_text(el) for el in (term, definition) if el is not None]
            return ' — '.join(p for p in parts if p)

        if tag == 'QUOT.S':
            inner = ' '.join(
                filter(None, (self._render_annex_text(sub) for sub in element
                              if isinstance(sub.tag, str)))
            )
            return f"'{inner}'" if inner else ''

        if tag == 'DLIST':
            return ' '.join(
                filter(None, (self._render_annex_text(item)
                              for item in element.findall('DLIST.ITEM')))
            )

        # Blocks containing tables, quoted blocks, numbered points or
        # definition lists need structured rendering; anything else is plain text.
        special = element.xpath('.//TBL | .//QUOT.S | .//NP | .//DLIST.ITEM')
        if not special:
            return self.clean_text(element)

        parts = [(element.text or '').strip()]
        for sub in element:
            if isinstance(sub.tag, str):
                parts.append(self._render_annex_text(sub))
            if sub.tail and sub.tail.strip():
                parts.append(sub.tail.strip())
        return ' '.join(p for p in parts if p)

    def _title_text(self, element: etree._Element) -> Optional[str]:
        """
        Renders a TI/STI title element as a single line.

        Multiple paragraphs are joined with a space (so 'ANNEX' + 'to ...'
        do not run together) and stray quotation marks from QUOT.START
        markers around quoted annex titles are stripped.
        """
        paragraphs = element.findall('.//P')
        if paragraphs:
            parts = [self.clean_text(p) for p in paragraphs]
            text = ' '.join(p for p in parts if p)
        else:
            text = self.clean_text(element)
        return ' '.join(text.split()).strip("'‘’") or None

    def _analyze_amendment(self, element: etree._Element) -> Optional[dict[str, Any]]:
        """
        Analyzes a content block for amendment semantics.

        A block amends another act when it carries quoted payloads
        (``QUOT.S`` structures or inline ``QUOT.START``/``QUOT.END`` spans)
        or when its text matches an amendment instruction ("... is replaced
        by ...", "... is amended as follows:"). Modelled on the Akoma Ntoso
        ``mod``/``quotedText``/``quotedStructure`` triple.

        Returns
        -------
        dict or None
            ``None`` for ordinary content, otherwise::

                {
                  'action': 'replace'|'insert'|'add'|'delete'|'amend'|None,
                  'instruction': str,       # the command, without payloads
                  'amended_act': str|None,  # first act citation, best effort
                  'quoted': [               # payloads, in document order
                    {'kind': 'structure', 'children': [{'text', 'table'?}]},
                    {'kind': 'text', 'text': str},
                  ],
                }

            Quoted children carry no eIds: they are content of the amended
            act, not structure of the amending one.
        """
        if element.tag == 'TBL':
            return None

        if element.tag == 'QUOT.S':
            return {
                'action': None,
                'instruction': '',
                'amended_act': None,
                'quoted': [{'kind': 'structure',
                            'children': self._quoted_children(element)}],
            }

        quot_blocks = element.xpath('.//QUOT.S[not(ancestor::QUOT.S)]')
        inline_spans = self._inline_quoted_spans(element)
        instruction = self._instruction_text(element)
        action = self._amendment_action(instruction)

        if not quot_blocks and not inline_spans and action is None:
            return None

        quoted: list[dict[str, Any]] = []
        for quot in quot_blocks:
            quoted.append({'kind': 'structure',
                           'children': self._quoted_children(quot)})
        for span in inline_spans:
            quoted.append({'kind': 'text', 'text': span})

        return {
            'action': action,
            'instruction': instruction,
            'amended_act': self._cited_act(instruction),
            'quoted': quoted,
        }

    def _amendment_action(self, text: str) -> Optional[str]:
        """Classifies the amendment operation from the instruction verb."""
        if not text:
            return None
        match = _AMEND_VERB_RE.search(text)
        if match:
            return _AMEND_ACTIONS[match.group(1).lower()]
        return None

    def _cited_act(self, text: str) -> Optional[str]:
        """Returns the first EU act citation in the text, if any."""
        if not text:
            return None
        match = _CITED_ACT_RE.search(text)
        return match.group(0) if match else None

    def _instruction_text(self, element: etree._Element) -> str:
        """
        Renders a block's text with quoted payloads (QUOT.S) removed,
        leaving only the amendment command itself.
        """
        copy = deepcopy(element)
        for quot in copy.xpath('.//QUOT.S'):
            parent = quot.getparent()
            if parent is None:
                continue
            if quot.tail and quot.tail.strip():
                prev = quot.getprevious()
                if prev is not None:
                    prev.tail = (prev.tail or '') + quot.tail
                else:
                    parent.text = (parent.text or '') + quot.tail
            parent.remove(quot)
        return self._render_annex_text(copy)

    def _inline_quoted_spans(self, element: etree._Element) -> list[str]:
        """
        Extracts the text spans between inline QUOT.START/QUOT.END markers,
        excluding anything inside QUOT.S structures (those are payloads of
        their own).
        """
        copy = deepcopy(element)
        for quot in copy.xpath('.//QUOT.S'):
            parent = quot.getparent()
            if parent is not None:
                parent.remove(quot)
        starts = copy.xpath('.//QUOT.START')
        if not starts:
            return []
        # Private-use-area sentinels: lxml rejects ASCII control characters
        for marker in starts:
            marker.text = ''
        for marker in copy.xpath('.//QUOT.END'):
            marker.text = ''
        raw = ''.join(copy.itertext())
        spans = re.findall('\ue000(.*?)\ue001', raw, re.S)
        return [' '.join(s.split()) for s in spans if s.strip()]

    def _quoted_children(self, quot: etree._Element) -> list[dict[str, Any]]:
        """
        Extracts the content blocks of a QUOT.S payload, using the same
        block extraction as annex children (so quoted tables keep their
        structured rows). Quoted children carry no eIds or amendment field.
        """
        # A quote wrapping a grafted document (INCL.ELEMENT resolution) is
        # unwrapped to that document's CONTENTS so its blocks come out
        # individually instead of as one flattened paragraph. Only CONTENTS
        # that are top-level within the quote count (ancestry is checked
        # relative to the quote, not the whole tree).
        def _top_level_in_quote(el):
            for ancestor in el.iterancestors():
                if ancestor is quot:
                    return True
                if ancestor.tag == 'CONTENTS':
                    return False
            return True

        scopes = [c for c in quot.xpath('.//CONTENTS')
                  if _top_level_in_quote(c)] or [quot]

        children: list[dict[str, Any]] = []
        for scope in scopes:
            for block in self._iter_annex_blocks(scope):
                text = self._render_annex_text(block)
                if not text:
                    continue
                item: dict[str, Any] = {'text': text}
                if block.tag == 'TBL':
                    item['table'] = {
                        'caption': self._table_caption(block),
                        'rows': self._table_rows(block),
                        'notes': self._table_notes(block),
                    }
                children.append(item)
        return children

    def _table_caption(self, table: etree._Element) -> Optional[str]:
        """Returns the caption of a Formex TBL element, if any."""
        title = table.find('TITLE')
        if title is not None:
            caption = self.clean_text(title)
            return caption or None
        return None

    def _table_notes(self, table: etree._Element) -> list[str]:
        """
        Extracts the notes (GR.NOTES legend) of a Formex TBL element.
        """
        notes = []
        for gr_notes in table.findall('GR.NOTES'):
            for child in gr_notes:
                if not isinstance(child.tag, str):
                    continue
                text = self._render_annex_text(child)
                if text:
                    notes.append(text)
        return notes

    def _table_rows(self, table: etree._Element) -> list[list[str]]:
        """
        Extracts a Formex TBL element as a list of rows of cell texts.

        Cells are cleaned individually so values from adjacent cells can
        never run together. Row groups (BLK) contribute their TI.BLK/STI.BLK
        block titles as single-cell rows, in document order. Nested tables
        inside cells stay inline in the cell text.
        """
        rows: list[list[str]] = []

        def walk(element):
            for child in element:
                if not isinstance(child.tag, str):
                    continue
                if child.tag == 'ROW':
                    cells = [self.clean_text(cell) for cell in child.findall('CELL')]
                    if any(cells):
                        rows.append(cells)
                elif child.tag in ('TI.BLK', 'STI.BLK'):
                    title = self.clean_text(child)
                    if title:
                        rows.append([title])
                elif child.tag in ('CORPUS', 'BLK'):
                    walk(child)

        corpus = table.find('CORPUS')
        walk(corpus if corpus is not None else table)
        return rows

    def clean_text(self, element: etree._Element) -> str:
        # Replace QUOT.START and QUOT.END elements with proper quotes
        for sub_element in element.iter():
            if sub_element.tag == 'QUOT.START':                    
                sub_element.text = "'"                    
            elif sub_element.tag == 'QUOT.END':                    
                sub_element.text = "'"
                
        # Extract text and normalize using strategy
        text = "".join(element.itertext())
        text = self.normalizer.normalize(text)
        
        return text

    
    def parse(self, file: str, **options) -> "Formex4Parser":
        """
        Parses a FORMEX XML document to extract its components, which are inherited from the XMLParser class.
        If the input is a directory, searches for the correct XML file (one containing ACT or DECISION tags).

        Parameters
        ----------
        file : str
            Path to the FORMEX XML file or directory containing FORMEX files.
        **options : dict
            Optional configuration options (passed to parent XMLParser)

        Returns
        -------
        Formex4Parser
            Self for method chaining with parsed data.
        """
        from pathlib import Path

        logger = logging.getLogger(__name__)

        # Annex files (root element ANNEX) found alongside the legal act
        annex_files: list[str] = []

        # Check if input is a directory
        file_path = Path(file)
        if file_path.is_dir():
            # Search for XML files in the directory, in natural order so that
            # e.g. DOC_10.xml sorts after DOC_2.xml and annexes keep OJ order
            def natural_key(p):
                return [int(part) if part.isdigit() else part
                        for part in re.split(r'(\d+)', p.name)]
            xml_files = sorted(file_path.glob('*.xml'), key=natural_key)

            # Find the file containing ACT or DECISION tags, and collect annexes
            target_file = None
            for xml_file in xml_files:
                try:
                    with open(xml_file, 'r', encoding='utf-8') as f:
                        content = f.read(5000)  # Read first 5KB to check for tags
                        if '<ANNEX' in content:
                            annex_files.append(str(xml_file))
                        elif target_file is None and (
                            '<ACT' in content or '<DECISION' in content or '<CONS.ACT' in content
                        ):
                            target_file = str(xml_file)
                            logger.info(f"Found Formex document with legal act: {xml_file.name}")
                except Exception as e:
                    logger.debug(f"Error reading {xml_file}: {e}")
                    continue

            if target_file:
                file = target_file
            elif xml_files:
                # Fallback: use the largest XML file if no ACT/DECISION found
                largest_file = max(xml_files, key=lambda f: f.stat().st_size)
                file = str(largest_file)
                logger.warning(f"No ACT/DECISION tag found, using largest file: {largest_file.name}")
            else:
                logger.error(f"No XML files found in directory: {file_path}")
                return self

        super().parse(file, schema='formex4.xsd', format='Formex 4', **options)

        # Files that are only the target of an INCL.ELEMENT reference in
        # another annex are skipped: their content is grafted into the
        # referencing annex, so extracting them separately would duplicate it.
        annex_files = self._drop_included_annex_files(annex_files)

        # If the parsed document is itself an annex (e.g. a standalone annex
        # file, or a corrigendum directory where no legal act was found),
        # extract the collected annex files — or the document itself.
        if self.root is not None and getattr(self.root, 'tag', None) == 'ANNEX':
            logger.info("Parsed document is an annex; extracting annex content")
            self.articles = []
            if annex_files:
                self.get_annexes(annex_files)
            else:
                base_dir = os.path.dirname(os.path.abspath(str(file)))
                annex = self._extract_annex(self.root, 1, base_dir=base_dir)
                self.annexes = [annex] if annex is not None else []
            return self

        # Extract any annex files found alongside the legal act
        if annex_files:
            self.get_annexes(annex_files)

        return self

    def _drop_included_annex_files(self, annex_files: list[str]) -> list[str]:
        """
        Filters out annex files that are INCL.ELEMENT targets of other annexes.

        Manifest declarations inside BIB.INSTANCE are ignored — only body
        references count as inclusions.
        """
        if not annex_files:
            return annex_files
        referenced = set()
        for annex_file in annex_files:
            try:
                root = etree.parse(annex_file).getroot()
            except Exception:
                continue
            for incl in root.xpath('.//INCL.ELEMENT[not(ancestor::BIB.INSTANCE)]'):
                fileref = incl.get('FILEREF')
                if fileref:
                    referenced.add(os.path.basename(fileref))
        return [f for f in annex_files if os.path.basename(f) not in referenced]