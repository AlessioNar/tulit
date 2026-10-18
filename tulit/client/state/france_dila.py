"""
Client for the DILA open data: the Journal officiel (JORF) and consolidated legislation (LEGI).

The Direction de l'information légale et administrative (DILA) publishes,
under the Licence Ouverte, the XML of the Journal officiel and of Légifrance's
consolidated legislation on https://echanges.dila.gouv.fr/OPENDATA/:

- a global dump of each base (``Freemium_jorf_global_*.tar.gz``,
  ``Freemium_legi_global_*.tar.gz``, about 1 GB each);
- daily archives of what changed since (``JORF_YYYYMMDD-HHMMSS.tar.gz``,
  ``LEGI_...``), a few MB each, from the date of the last global dump.

A text published in the Journal officiel since the last global dump is
found in the daily archives of the days after it was signed. Anything else
needs the global dump, downloaded and extracted once (``dump_dir``).
"""
import datetime
import glob
import io
import json
import os
import re
import tarfile
from typing import Callable, Iterable, Optional

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tulit.client.client import Client
from tulit.parser.exceptions import FileLoadError, NetworkError, UnsupportedError

OPENDATA = 'https://echanges.dila.gouv.fr/OPENDATA'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
_ARCHIVE = re.compile(r'href="(?P<name>(?P<fund>JORF|LEGI)_(?P<date>\d{8})-(?P<time>\d{6})\.tar\.gz)"')
_GLOBAL = re.compile(r'href="(?P<name>Freemium_(?P<fund>jorf|legi)_global_(?P<date>\d{8})-\d{6}\.tar\.gz)"')
_ID = re.compile(r'(?P<prefix>JORF|LEGI)(?P<kind>TEXT|ARTI|SCTA|CONT)(?P<digits>\d{12})')


def id_path(identifier: str) -> str:
    """'JORFTEXT000054988304' -> 'JORF/TEXT/00/00/54/98/83/JORFTEXT000054988304', as the DILA files are laid out."""
    match = _ID.fullmatch(identifier)
    if not match:
        raise ValueError(f"'{identifier}' is not a DILA identifier")
    digits = match.group('digits')
    pairs = '/'.join(digits[i:i + 2] for i in range(0, 10, 2))
    return f"{match.group('prefix')}/{match.group('kind')}/{pairs}/{identifier}"


def text_meta(root: etree._Element) -> dict[str, Optional[str]]:
    """Identifier, NOR, number, nature and dates of a TEXTE_VERSION or TEXTELR file."""
    def find(name: str) -> Optional[str]:
        value = root.findtext(f'.//{name}')
        return value.strip() if value and value.strip() else None

    return {'id': find('META_COMMUN/ID'), 'cid': find('CID'), 'eli': find('META_COMMUN/ID_ELI'),
            'nature': find('META_COMMUN/NATURE'), 'nor': find('NOR'), 'num': find('NUM'),
            'date_texte': find('DATE_TEXTE'), 'date_publi': find('DATE_PUBLI'), 'title': find('TITREFULL')}


def _safe_extract(tar: tarfile.TarFile, target: str) -> None:
    """Extract an archive into ``target`` only: no absolute paths, '..', links or devices."""
    if hasattr(tarfile, 'data_filter'):
        tar.extractall(target, filter='data')
        return
    root = os.path.realpath(target)
    for member in tar.getmembers():
        path = os.path.realpath(os.path.join(target, member.name))
        if not (path == root or path.startswith(root + os.sep)) or not (member.isfile() or member.isdir()):
            raise FileLoadError(f"Unsafe member in the DILA archive: {member.name}")
    tar.extractall(target)


class DilaClient(Client):
    """Finds French texts in the DILA open data (daily archives, or a local global dump) and extracts their files."""

    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        retry = Retry(total=5, connect=5, read=5, backoff_factor=2,
                      status_forcelist=(429, 500, 502, 503, 504), allowed_methods=('GET',))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if proxies:
            self.session.proxies.update(proxies)

    def _get(self, url: str) -> bytes:
        try:
            response = self.session.get(url, timeout=600)
        except requests.RequestException as e:
            raise NetworkError(f"DILA request failed for {url}: {e}") from e
        if response.status_code == 404:
            raise FileLoadError(f"DILA has nothing at {url}")
        if response.status_code != 200:
            raise NetworkError(f"DILA returned HTTP {response.status_code} for {url}")
        return response.content

    # Daily archives

    def archives(self, fund: str = 'JORF') -> list[tuple[str, str]]:
        """The daily archives of a base ('JORF' or 'LEGI'): (file name, date 'YYYY-MM-DD'), oldest first."""
        listing = self._get(f'{OPENDATA}/{fund}/').decode('utf-8', errors='replace')
        found = {(m.group('name'), f"{m.group('date')[:4]}-{m.group('date')[4:6]}-{m.group('date')[6:]}")
                 for m in _ARCHIVE.finditer(listing) if m.group('fund') == fund}
        return sorted(found)

    def first_day(self, fund: str = 'JORF') -> Optional[str]:
        """The date from which the daily archives cover the base (that of the last global dump)."""
        days = [date for _, date in self.archives(fund)]
        return days[0] if days else None

    def archive_files(self, name: str, fund: str = 'JORF') -> dict[str, bytes]:
        """The XML files of a daily archive, by path inside it (kept in the download directory)."""
        target = os.path.join(self.download_dir, 'FR', 'archives', name)
        if os.path.exists(target):
            with open(target, 'rb') as f:
                content = f.read()
        else:
            content = self._get(f'{OPENDATA}/{fund}/{name}')
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(content)
        files = {}
        with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as archive:
            for member in archive:
                if member.isfile() and member.name.endswith('.xml'):
                    files[member.name] = archive.extractfile(member).read()
        return files

    def find_in_archives(self, names: Iterable[str], match: Callable[[dict], bool],
                         fund: str = 'JORF') -> Optional[tuple[str, dict[str, bytes]]]:
        """The first text in the given daily archives whose metadata ``match`` accepts: (id, archive files)."""
        for name in names:
            files = self.archive_files(name, fund)
            for path, content in files.items():
                if '/texte/version/' not in path:
                    continue
                meta = text_meta(etree.fromstring(content))
                if match(meta):
                    return meta['id'], files
        return None

    def find_published(self, match: Callable[[dict], bool], signed: str, days: int = 45) -> tuple[str, dict]:
        """A text published in the Journal officiel within ``days`` of ``signed`` (its signature date)."""
        start = datetime.date.fromisoformat(signed)
        end = (start + datetime.timedelta(days=days)).isoformat()
        names = [name for name, date in self.archives('JORF') if signed <= date <= end]
        found = self.find_in_archives(names, match)
        if found is None:
            raise FileLoadError(f"No text signed on {signed} matches in the Journal officiel archives up to {end}")
        return found

    def find_by_id(self, identifier: str) -> tuple[str, dict]:
        """A JORFTEXT in the daily archives, by bisecting them on its identifier (identifiers grow with time)."""
        names = [name for name, _ in self.archives('JORF')]
        number = int(identifier[-12:])
        low, high = 0, len(names) - 1
        while low <= high:
            middle = (low + high) // 2
            files = self.archive_files(names[middle])
            numbers = [int(m.group('digits')) for path in files for m in [_ID.search(path)]
                       if m and m.group('kind') == 'TEXT' and '/texte/version/' in path]
            if any(path.endswith(f'/{identifier}.xml') and '/texte/version/' in path for path in files):
                return identifier, files
            if not numbers or number > max(numbers):
                low = middle + 1
            else:
                high = middle - 1
        raise FileLoadError(f"{identifier} is not in the Journal officiel daily archives")

    # Local global dump

    def global_dump(self, fund: str) -> tuple[str, str]:
        """The latest global dump of a base ('JORF' or 'LEGI'): (file name, date 'YYYY-MM-DD')."""
        listing = self._get(f'{OPENDATA}/{fund.upper()}/').decode('utf-8', errors='replace')
        found = sorted((m.group('date'), m.group('name')) for m in _GLOBAL.finditer(listing)
                       if m.group('fund') == fund.lower())
        if not found:
            raise FileLoadError(f"DILA publishes no global {fund.upper()} dump at {OPENDATA}/{fund.upper()}/")
        date, name = found[-1]
        return name, f'{date[:4]}-{date[4:6]}-{date[6:]}'

    def download_dump(self, fund: str, dump_dir: str, extract: bool = True,
                      progress: Optional[Callable[[int, Optional[int]], None]] = None) -> str:
        """
        Download the latest global dump of a base ('JORF' or 'LEGI', about 1 GB) into ``dump_dir`` and
        extract it there; returns the dump's root folder ('<fund>/global'), or the archive's path when
        ``extract`` is False. A download already complete is not repeated; ``progress(done, total)`` is
        called as the archive arrives.
        """
        fund = fund.upper()
        if fund not in ('JORF', 'LEGI'):
            raise UnsupportedError(f"Unknown DILA base '{fund}': choose JORF or LEGI")
        name, _ = self.global_dump(fund)
        os.makedirs(dump_dir, exist_ok=True)
        archive = os.path.join(dump_dir, name)
        url = f'{OPENDATA}/{fund}/{name}'
        try:
            total = int(self.session.head(url, timeout=60).headers.get('Content-Length') or 0) or None
        except requests.RequestException:
            total = None
        if not (os.path.exists(archive) and total and os.path.getsize(archive) == total):
            partial = f'{archive}.part'
            done = os.path.getsize(partial) if os.path.exists(partial) else 0
            headers = {'Range': f'bytes={done}-'} if done else {}
            try:
                with self.session.get(url, stream=True, timeout=600, headers=headers) as response:
                    if response.status_code not in (200, 206):
                        raise NetworkError(f"DILA returned HTTP {response.status_code} for {url}")
                    if response.status_code == 200:
                        done = 0
                    with open(partial, 'ab' if done else 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1 << 20):
                            f.write(chunk)
                            done += len(chunk)
                            if progress:
                                progress(done, total)
            except requests.RequestException as e:
                raise NetworkError(f"DILA download failed for {url} (run again to resume): {e}") from e
            os.replace(partial, archive)
        if not extract:
            return archive
        with tarfile.open(archive, 'r:gz') as tar:
            _safe_extract(tar, dump_dir)
        return self.dump_root(dump_dir, fund)

    @staticmethod
    def dump_root(dump_dir: str, fund: str) -> str:
        """The 'jorf/global' or 'legi/global' folder of an extracted dump, wherever it lies under ``dump_dir``."""
        for depth in range(0, 4):
            pattern = os.path.join(dump_dir, *(['*'] * depth), fund.lower(), 'global')
            found = glob.glob(pattern)
            if found:
                return found[0]
        raise FileLoadError(f"{dump_dir} holds no extracted DILA {fund} dump ({fund.lower()}/global)")

    def dump_index(self, root: str) -> list[dict[str, Optional[str]]]:
        """Metadata of every text in a dump, read once and kept next to it (or in the download directory)."""
        name = '.tulit_dila_index.json'
        for folder in (root, self.download_dir):
            path = os.path.join(folder, name)
            if os.path.exists(path):
                with open(path, encoding='utf-8') as f:
                    return json.load(f)
        index = []
        for folder, _, files in os.walk(root):
            if not folder.endswith(os.path.join('texte', 'version')) and '/texte/version/' not in folder + '/':
                continue
            for file in files:
                if file.endswith('.xml'):
                    path = os.path.join(folder, file)
                    try:
                        meta = text_meta(etree.parse(path).getroot())
                    except etree.XMLSyntaxError:
                        continue
                    meta['path'] = os.path.relpath(path, root)
                    meta.pop('title', None)
                    index.append(meta)
        for folder in (root, self.download_dir):
            try:
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, name), 'w', encoding='utf-8') as f:
                    json.dump(index, f)
                break
            except OSError:
                continue
        return index

    def dump_files(self, root: str, version_path: str) -> dict[str, bytes]:
        """The files of one text in a dump: its folder (LEGI), or its version, structure, sections, articles (JORF)."""
        version_file = os.path.join(root, version_path)
        parts = version_path.split(os.sep)
        if 'texte' in parts and parts.index('texte') > 1 and parts[parts.index('texte') - 1].startswith(
                ('JORFTEXT', 'LEGITEXT')) and not version_path.startswith('texte'):
            # LEGI: every file of the text lies under its folder
            folder = os.path.join(root, *parts[:parts.index('texte')])
            files = {}
            for current, _, names in os.walk(folder):
                for file in names:
                    if file.endswith('.xml'):
                        with open(os.path.join(current, file), 'rb') as f:
                            files[os.path.relpath(os.path.join(current, file), root)] = f.read()
            return files
        # JORF: the files are spread by kind, at paths made from their identifiers
        files: dict[str, bytes] = {}

        def add(relative: str) -> Optional[bytes]:
            path = os.path.join(root, relative)
            if not os.path.exists(path):
                return None
            with open(path, 'rb') as f:
                files[relative] = f.read()
            return files[relative]

        add(os.path.relpath(version_file, root))
        identifier = os.path.basename(version_file)[:-4]
        add(f'texte/struct/{id_path(identifier)}.xml')
        return self._with_linked(files, lambda kind, ident: add(f'{kind}/{id_path(ident)}.xml'))

    @staticmethod
    def _with_linked(files: dict[str, bytes], add: Callable[[str, str], Optional[bytes]]) -> dict[str, bytes]:
        """Add the sections and articles the structure files link to, recursively."""
        pending = list(files.values())
        seen = set()
        while pending:
            root = etree.fromstring(pending.pop())
            for link in root.iter('LIEN_SECTION_TA', 'LIEN_ART'):
                identifier = link.get('id')
                if not identifier or identifier in seen:
                    continue
                seen.add(identifier)
                content = add('section_ta' if link.tag == 'LIEN_SECTION_TA' else 'article', identifier)
                if content is not None and link.tag == 'LIEN_SECTION_TA':
                    pending.append(content)
        return files

    # Files of one text

    def text_files(self, identifier: str, files: dict[str, bytes]) -> dict[str, bytes]:
        """The files of text ``identifier`` among the files of a daily archive."""
        by_id = {}
        for path in files:
            match = _ID.search(os.path.basename(path))
            if match:
                by_id.setdefault((path.split('/global/')[-1].split('/')[0], match.group(0)), path)
        chosen: dict[str, bytes] = {}
        for kind in ('texte/version', 'texte/struct'):
            path = next((p for p in files if f'/{kind}/' in p and p.endswith(f'/{identifier}.xml')), None)
            if path:
                chosen[path] = files[path]

        def add(kind: str, ident: str) -> Optional[bytes]:
            path = by_id.get((kind, ident))
            if path is None:
                return None
            chosen[path] = files[path]
            return files[path]

        return self._with_linked(chosen, add)

    def save(self, identifier: str, files: dict[str, bytes]) -> str:
        """Write the files of one text to its own folder in the download directory and return the folder."""
        folder = os.path.join(self.download_dir, 'FR', identifier)
        for path, content in files.items():
            # Version and structure files share their name: keep them apart by kind
            kind = next((k for k in ('version', 'struct', 'article', 'section_ta')
                         if f'/{k}/' in f'/{path}'), 'other')
            target = os.path.join(folder, kind, os.path.basename(path))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(content)
        if not files:
            raise FileLoadError(f"No files found for {identifier}")
        return folder
