"""
France: Journal officiel (JORF) and Légifrance consolidated legislation (LEGI), from the DILA open data.

The original version is the text as published in the Journal officiel; the
consolidated version is Légifrance's text in force on a date. Both come from
the XML the DILA publishes under the Licence Ouverte
(https://echanges.dila.gouv.fr/OPENDATA/):

- texts published since the last global dump (July 2025) are found in the
  daily archives, from their signature date; their consolidated version is
  rebuilt from the daily LEGI archives up to the date asked for;
- anything older needs the global dumps (Freemium_jorf_global_*.tar.gz,
  Freemium_legi_global_*.tar.gz, about 1 GB each), downloaded and extracted
  once and given as ``dump_dir``.

Légifrance itself (and its PISTE API, which needs credentials) is not used.
"""
import datetime
import glob
import os
import re
import unicodedata
from typing import Any, Callable, Optional

from lxml import etree

from tulit.client.state.france_dila import DilaClient, text_meta
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source

_TEXT_ID = re.compile(r'^(JORFTEXT|LEGITEXT)\d{12}$')
_NOR = re.compile(r'^[A-Z]{4}\d{7}[A-Z]$')
_ELI = re.compile(r'legifrance\.gouv\.fr/eli/(?P<type>[a-z_]+)/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/'
                  r'(?P<ref>[^/]+)')
_TITLE = re.compile(r'^(?P<nature>loi organique|loi constitutionnelle|loi|ordonnance|décret|decret|arrêté|arrete)'
                    r'\s+(?:n\s*°|no|nº)?\s*(?P<num>\d{2,4}-\d+)?\s*du\s+(?P<day>\d{1,2})(?:er)?\s+(?P<month>\w+)\s+'
                    r'(?P<year>\d{4})', re.IGNORECASE)
MONTHS = ('janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin', 'juillet', 'aout', 'septembre', 'octobre',
          'novembre', 'decembre')
NATURES = {'loi organique': 'LOI_ORGANIQUE', 'loi constitutionnelle': 'LOI_CONSTIT', 'loi': 'LOI',
           'ordonnance': 'ORDONNANCE', 'decret': 'DECRET', 'arrete': 'ARRETE'}
OPEN = '2999-01-01'
"""The date the DILA gives what has none."""
MAX_LEGI_ARCHIVES = 60
"""Daily LEGI archives scanned at most to rebuild a consolidated text; beyond, the global dump is needed."""


def _plain(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


def reference(identifier: str) -> dict[str, Optional[str]]:
    """
    What an identifier says about a text: its id, NOR, number, nature and signature date.

    'JORFTEXT000037085952', 'JUSC1732261L', 'Loi n° 2018-493 du 20 juin 2018' or its ELI.
    """
    text = identifier.strip()
    found: dict[str, Optional[str]] = {'id': None, 'nor': None, 'num': None, 'nature': None, 'date': None}
    if _TEXT_ID.match(text):
        found['id'] = text
        return found
    if _NOR.match(text):
        found['nor'] = text
        return found
    match = _ELI.search(text)
    if match:
        found['date'] = datetime.date(int(match.group('year')), int(match.group('month')),
                                      int(match.group('day'))).isoformat()
        ref = match.group('ref')
        if _NOR.match(ref):
            found['nor'] = ref
        elif re.match(r'^\d{2,4}-\d+$', ref):
            found['num'] = ref
        found['nature'] = match.group('type').upper()
        return found
    match = _TITLE.match(_plain(text))
    if match and _plain(match.group('month')) in MONTHS:
        found['nature'] = NATURES.get(_plain(match.group('nature')))
        found['num'] = match.group('num')
        found['date'] = datetime.date(int(match.group('year')), MONTHS.index(_plain(match.group('month'))) + 1,
                                      int(match.group('day'))).isoformat()
        return found
    raise ValueError(f"'{identifier}' is not a French text reference; use {FranceSource.identifier_help}")


def _matcher(ref: dict[str, Optional[str]]) -> Callable[[dict], bool]:
    """Whether the metadata of a text is the text a reference names."""
    def match(meta: dict) -> bool:
        if ref['id']:
            return ref['id'] in (meta.get('id'), meta.get('cid'))
        if ref['nor']:
            return meta.get('nor') == ref['nor']
        if ref['num']:
            # The DILA leaves the date of some texts open (2999-01-01; loi 2025-1251)
            return meta.get('num') == ref['num'] and (not ref['date'] or meta.get('date_texte') in (ref['date'], OPEN))
        return (meta.get('date_texte') == ref['date']
                and (not ref['nature'] or (meta.get('nature') or '').upper() == ref['nature']))
    return match


def _version_date(folder: str, date: Optional[str]) -> Optional[str]:
    """The start of the latest change in force on ``date`` among the links of a LEGI structure."""
    starts = []
    for path in glob.glob(os.path.join(folder, '**', '*.xml'), recursive=True):
        root = etree.parse(path).getroot()
        if root.tag not in ('TEXTELR', 'SECTION_TA'):
            continue
        for link in root.iter('LIEN_ART', 'LIEN_SECTION_TA'):
            start = link.get('debut')
            if start and start != '2999-01-01' and (date is None or start <= date):
                starts.append(start)
    return max(starts) if starts else None


class FranceSource(Source):
    code = 'FR'
    name = 'France'
    source_name = 'Journal officiel and Légifrance (DILA open data)'
    versions = (ORIGINAL, CONSOLIDATED)
    languages = ('fra',)
    options = ('dump_dir',)
    identifier_help = ("a JORFTEXT or LEGITEXT identifier, a NOR (e.g. 'JUSC1732261L'), a title such as "
                       "'Loi n° 2018-493 du 20 juin 2018', or its ELI "
                       "('https://www.legifrance.gouv.fr/eli/loi/2018/6/20/JUSC1732261L/jo/texte')")
    eli_patterns = (re.compile(r'^(?P<id>https?://www\.legifrance\.gouv\.fr/eli/.+)$'),)

    def retrieve(
        self,
        identifier: str,
        version: str,
        date: Optional[str],
        language: Optional[str],
        download_dir: str,
        metadata: bool = True,
        dump_dir: Optional[str] = None,
        **options: Any,
    ) -> Retrieval:
        ref = reference(identifier)
        client = DilaClient(download_dir=download_dir)
        if version == ORIGINAL and date:
            raise ValueError("A date selects a consolidated version; the original version has none")
        target = date or datetime.date.today().isoformat()
        if dump_dir:
            folder, meta = self._from_dump(client, dump_dir, ref, version)
        elif version == ORIGINAL:
            folder, meta = self._published(client, ref)
        else:
            folder, meta = self._consolidated(client, ref, target)
        meta = {key: value for key, value in meta.items() if value and value != OPEN}
        version_date = meta.get('date_publi') if version == ORIGINAL else _version_date(folder, target)
        return Retrieval(
            path=folder,
            parser='fr-dila',
            parser_options={'date': target} if version == CONSOLIDATED else {},
            version=version,
            language='fra',
            version_date=version_date,
            meta={'eli': meta.get('eli'), 'date_document': meta.get('date_texte'),
                  'date_publication': meta.get('date_publi'), 'nor': meta.get('nor'), 'number': meta.get('num'),
                  'source': meta.get('source')},
        )

    @staticmethod
    def _published(client: DilaClient, ref: dict) -> tuple[str, dict]:
        """A text as published, from the daily Journal officiel archives."""
        first = client.first_day('JORF')
        if ref['date'] and first and ref['date'] < first:
            raise FileLoadError(f"The DILA daily archives start on {first}; for a text signed on {ref['date']}, "
                                f"download and extract the global JORF dump and pass dump_dir")
        if ref['date']:
            identifier, files = client.find_published(_matcher(ref), ref['date'])
        elif ref['id'] and ref['id'].startswith('JORFTEXT'):
            identifier, files = client.find_by_id(ref['id'])
        else:
            raise ValueError("Without the global dump, a text is found by its JORFTEXT identifier, its title "
                             "('Décret n° 2026-959 du 15 octobre 2026') or its ELI, which give its date")
        files = client.text_files(identifier, files)
        folder = client.save(identifier, files)
        meta = FranceSource._meta(folder)
        meta['source'] = 'https://echanges.dila.gouv.fr/OPENDATA/JORF/'
        return folder, meta

    @staticmethod
    def _consolidated(client: DilaClient, ref: dict, target: str) -> tuple[str, dict]:
        """A consolidated text rebuilt from the daily LEGI archives since its publication."""
        published, meta = FranceSource._published(client, ref)
        start = meta.get('date_publi') or ref['date']
        names = [name for name, day in client.archives('LEGI') if start <= day <= target]
        if len(names) > MAX_LEGI_ARCHIVES:
            raise FileLoadError(f"Rebuilding the consolidated text would read {len(names)} daily LEGI archives; "
                                f"download and extract the global LEGI dump and pass dump_dir")
        cid = meta['id']
        files: dict[str, bytes] = {}
        for name in names:
            for path, content in client.archive_files(name, 'LEGI').items():
                # A text's LEGI files lie under a folder named after it; later archives replace earlier files
                if f'/{cid}/' in path:
                    files[path.split(f'/{cid}/', 1)[1]] = content
        if not files:
            raise FileLoadError(f"No consolidated version of {cid} in the daily LEGI archives up to {target}")
        folder = client.save(f'{cid}_LEGI', files)
        meta.update({key: value for key, value in FranceSource._meta(folder).items() if value})
        meta['source'] = 'https://echanges.dila.gouv.fr/OPENDATA/LEGI/'
        return folder, meta

    @staticmethod
    def _from_dump(client: DilaClient, dump_dir: str, ref: dict, version: str) -> tuple[str, dict]:
        """A text from an extracted global dump (JORF for the original, LEGI for the consolidated version)."""
        fund = 'JORF' if version == ORIGINAL else 'LEGI'
        root = client.dump_root(dump_dir, fund)
        match = _matcher(ref)
        candidates = [meta for meta in client.dump_index(root) if match(meta)]
        if not candidates:
            raise FileLoadError(f"The {fund} dump in {dump_dir} has no text matching {ref}")
        # In LEGI, prefer the text currently in force
        chosen = sorted(candidates, key=lambda m: 'non_vigueur' in m['path'])[0]
        files = client.dump_files(root, chosen['path'])
        folder = client.save(chosen['id'], files)
        meta = FranceSource._meta(folder)
        meta['source'] = os.path.join(root, chosen['path'])
        return folder, meta

    @staticmethod
    def _meta(folder: str) -> dict:
        for path in glob.glob(os.path.join(folder, 'version', '*.xml')):
            return text_meta(etree.parse(path).getroot())
        return {}
