"""
High-level entry points for tulit.

``fetch`` turns an identifier into validated legalJSON in one call: it
downloads the act from its official source, picks the matching parser and
attaches the document metadata.

Example
-------
>>> import tulit
>>> doc = tulit.fetch("32024R0903")
>>> doc["meta"]["eli"]
'http://data.europa.eu/eli/reg/2024/903/oj'
>>> doc = tulit.fetch("10001597", jurisdiction="AT", version="consolidated")

``download`` stops before parsing and returns the official file itself, for
instance a scanned PDF that has no text to parse.
"""
import logging
import os
import tempfile
import warnings
from typing import Any, Optional

import jsonschema
from lxml import etree

from tulit.parser.exceptions import FileLoadError, UnsupportedError, ValidationError
from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser
from tulit.sources import VERSIONS, Source, get_source, source_for_eli
from tulit.sources.eu import CELLAR_FORMATS

logger = logging.getLogger(__name__)

__all__ = ['fetch', 'download', 'export', 'native_akn', 'CELLAR_FORMATS', 'EXPORT_FORMATS', 'SCHEMA_VERSION']

META_DEFAULTS = {
    'celex': None,
    'eli': None,
    'cellar_uuid': None,
    'date_document': None,
    'in_force': None,
    'amends': [],
    'repeals': [],
    'corrects': [],
    'source': None,
    'valid': None,
}


def fetch(
    identifier: str,
    jurisdiction: Optional[str] = None,
    version: Optional[str] = None,
    date: Optional[str] = None,
    language: Optional[str] = None,
    download_dir: Optional[str] = None,
    metadata: bool = True,
    validate: bool = True,
    **options: Any,
) -> dict[str, Any]:
    """
    Download an act from its official source and return it as legalJSON.

    Parameters
    ----------
    identifier : str
        The act's identifier: a CELEX number for the EU, the national
        identifier of the jurisdiction (see ``tulit.sources``), or an ELI URI.
    jurisdiction : str, optional
        'EU' or a Member State code ('AT', ...). Inferred from ELI URIs;
        defaults to 'EU' otherwise.
    version : str, optional
        'original' (the text as adopted) or 'consolidated' (the text in force
        on ``date``). Defaults to 'original' where the source publishes it.
    date : str, optional
        ISO date for consolidated versions; defaults to today.
    language : str, optional
        ISO 639-3 language code (e.g. 'eng', 'fra', 'deu'); defaults to the
        source's main language.
    download_dir : str, optional
        Directory where the source files are kept. When omitted, files are
        downloaded to a temporary directory that is removed afterwards.
    metadata : bool, optional
        Attach the ``meta`` object (identifiers, dates, version, language,
        relations). Default True.
    validate : bool, optional
        Validate the result against the legalJSON schema. Default True.
    **options
        Source-specific options, e.g. ``format='xhtml'`` for the EU.

    Returns
    -------
    dict
        The act as legalJSON.

    Raises
    ------
    ValueError
        If the jurisdiction, version or a source option is not supported.
    FileLoadError
        If the source has no document for the act.
    ValidationError
        If ``validate`` is True and the result does not conform to the
        legalJSON schema.
    """
    source, identifier, version = _check(identifier, jurisdiction, version, language, options)
    if download_dir is not None:
        return _fetch_into(source, identifier, version, date, language, download_dir,
                           metadata, validate, options)
    with tempfile.TemporaryDirectory(prefix='tulit-') as tmp_dir:
        return _fetch_into(source, identifier, version, date, language, tmp_dir,
                           metadata, validate, options)


EXPORT_FORMATS = ('akn', 'leg')
# Version of the legalJSON schema the documents follow (tulit/parser/legaljson_schema.json)
SCHEMA_VERSION = '1.0'
AKN_NAMESPACE = 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'


def export(doc: dict[str, Any], to: str = 'akn', path: Optional[str] = None, native: bool = False,
           download_dir: Optional[str] = None) -> bytes:
    """
    Convert a legalJSON document to another legal format.

    Parameters
    ----------
    doc : dict
        A legalJSON document, as ``fetch`` returns it.
    to : str, optional
        'akn' for Akoma Ntoso 3.0 XML (default), or 'leg' for a LEOS .leg
        package: a zip of Akoma Ntoso documents (``main.xml``, the act and
        one file per annex), as exchanged by LEOS and AKN4EU.
    path : str, optional
        Also write the result to this file.
    native : bool, optional
        With ``to='akn'``: instead of writing Akoma Ntoso from the legalJSON,
        return the official Akoma Ntoso file of the act, where its source
        publishes one (Italy, Finland, Luxembourg, Germany), unchanged. It keeps
        what legalJSON does not hold (inline references, notes, the source's
        metadata). Luxembourg publishes an earlier draft of Akoma Ntoso (CSD13)
        and Germany its own variant (LegalDocML.de): a warning says so. The act
        is downloaded again from the identifier, jurisdiction, version and date
        in ``doc['meta']``.
    download_dir : str, optional
        With ``native``: where to keep the downloaded file.

    Returns
    -------
    bytes
        The XML document, or the zip package.

    Raises
    ------
    UnsupportedError
        If ``to`` is not a supported format, or with ``native`` when the
        source does not publish the act in Akoma Ntoso.

    Examples
    --------
    >>> doc = tulit.fetch('32024R0903')
    >>> xml = tulit.export(doc, to='akn')
    >>> tulit.export(doc, to='leg', path='32024R0903.leg')
    >>> official = tulit.export(tulit.fetch('L. 160/2019', jurisdiction='IT'), native=True)
    """
    from tulit.exporters import to_akn, to_leg
    converters = {'akn': to_akn, 'leg': to_leg}
    if to not in converters:
        raise UnsupportedError(f"Unknown export format {to!r}; supported: {', '.join(EXPORT_FORMATS)}")
    if native:
        if to != 'akn':
            raise UnsupportedError("native is available for Akoma Ntoso (to='akn') only")
        meta = doc.get('meta') or {}
        if not (meta.get('identifier') and meta.get('jurisdiction')):
            raise UnsupportedError("native needs the act's identifier and jurisdiction in doc['meta'] "
                                   "(documents fetched with tulit 1.0 have them)")
        content = native_akn(meta['identifier'], meta['jurisdiction'], meta.get('version'),
                             meta.get('version_date') if meta.get('version') == 'consolidated' else None,
                             meta.get('language'), download_dir)
    else:
        content = converters[to](doc)
    if path:
        with open(path, 'wb') as f:
            f.write(content)
    return content


def native_akn(identifier: str, jurisdiction: Optional[str] = None, version: Optional[str] = None,
               date: Optional[str] = None, language: Optional[str] = None, download_dir: Optional[str] = None,
               **options: Any) -> bytes:
    """
    The official Akoma Ntoso file of an act, unchanged, where its source publishes one.

    Takes the same arguments as ``fetch``. Warns when the file is not in the
    Akoma Ntoso 3.0 namespace (Luxembourg's CSD13 draft, Germany's
    LegalDocML.de). Raises ``UnsupportedError`` when the source publishes
    the act in another format.
    """
    found = download(identifier, jurisdiction, version, date, language, download_dir, **options)
    path = found['path']
    source = get_source(found['jurisdiction'])
    if os.path.isdir(path) or not path.lower().endswith(('.xml', '.akn')):
        raise UnsupportedError(f"{source.source_name} does not publish {identifier} in Akoma Ntoso; "
                               f"export it without native")
    with open(path, 'rb') as f:
        content = f.read()
    try:
        root = etree.fromstring(content, etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))
    except etree.XMLSyntaxError as e:
        raise FileLoadError(f"The file {source.source_name} returned for {identifier} is not XML: {e}") from e
    if etree.QName(root).localname != 'akomaNtoso':
        raise UnsupportedError(f"{source.source_name} does not publish {identifier} in Akoma Ntoso; "
                               f"export it without native")
    namespace = etree.QName(root).namespace
    if namespace != AKN_NAMESPACE:
        warnings.warn(f"{source.source_name} publishes {identifier} in a variant of Akoma Ntoso ({namespace}), "
                      f"not in Akoma Ntoso 3.0; returned unchanged", stacklevel=2)
    return content


def download(
    identifier: str,
    jurisdiction: Optional[str] = None,
    version: Optional[str] = None,
    date: Optional[str] = None,
    language: Optional[str] = None,
    download_dir: Optional[str] = None,
    **options: Any,
) -> dict[str, Any]:
    """
    Download an act from its official source without parsing it.

    Takes the same arguments as ``fetch``. Useful for keeping the official
    file, and for acts published only as scanned PDFs, which ``fetch``
    cannot turn into legalJSON.

    Parameters
    ----------
    download_dir : str, optional
        Directory to keep the file in; a new temporary directory (which is
        not removed) when omitted.

    Returns
    -------
    dict
        ``path`` (the downloaded file), ``parser`` (the parser that reads it,
        None when tulit cannot), ``jurisdiction``, ``version``, ``language``,
        ``version_date`` and ``meta`` (what the source knows about the act,
        including its ``source`` URL).
    """
    source, identifier, version = _check(identifier, jurisdiction, version, language, options)
    download_dir = download_dir or tempfile.mkdtemp(prefix='tulit-')
    retrieval = source.retrieve(identifier, version, date, language, download_dir, metadata=True, **options)
    return {
        'path': retrieval.path,
        'parser': retrieval.parser,
        'jurisdiction': source.code,
        'version': retrieval.version,
        'language': retrieval.language,
        'version_date': retrieval.version_date,
        'meta': dict(retrieval.meta),
    }


def _check(identifier, jurisdiction, version, language, options):
    """The source and identifier, with the version and options checked against what the source offers."""
    source, identifier = _resolve(identifier, jurisdiction)
    if version is None and not source.version_from_identifier:
        version = source.default_version
    if version is not None:
        if version not in VERSIONS:
            raise UnsupportedError(f"Unknown version '{version}'. Choose one of: {', '.join(VERSIONS)}")
        if version not in source.versions:
            raise UnsupportedError(
                f"{source.name} ({source.source_name}) does not publish the {version} version; "
                f"available: {', '.join(source.versions)}"
            )

    if language and source.languages and language.lower() not in source.languages:
        raise UnsupportedError(
            f"{source.name} publishes in {', '.join(source.languages)}, not '{language}'"
        )
    unknown = sorted(set(options) - set(source.options))
    if unknown:
        raise UnsupportedError(f"Unsupported option(s) for {source.name}: {', '.join(unknown)}")
    return source, identifier, version


def _resolve(identifier: str, jurisdiction: Optional[str]) -> tuple[Source, str]:
    if identifier.startswith(('http://', 'https://')):
        if jurisdiction:
            source = get_source(jurisdiction)
            resolved = source.identifier_from_eli(identifier)
            if resolved is None:
                raise UnsupportedError(f"{identifier} is not an ELI of {source.name}")
            return source, resolved
        found = source_for_eli(identifier)
        if found is None:
            raise UnsupportedError(f"No supported source recognises the ELI {identifier}")
        return found
    return get_source(jurisdiction or 'EU'), identifier


def _fetch_into(source, identifier, version, date, language, download_dir,
                metadata, validate, options):
    retrieval = source.retrieve(identifier, version, date, language, download_dir,
                                metadata=metadata, **options)
    if retrieval.parser is None:
        raise FileLoadError(
            f"{source.name} publishes {identifier} only as a scanned document without text "
            f"({retrieval.meta.get('source') or retrieval.path}); tulit.download returns the file"
        )
    parser = get_parser(retrieval.parser, **retrieval.parser_options)
    parser.parse(retrieval.path)
    doc = parser.to_dict()

    if metadata:
        meta = {key: (list(value) if isinstance(value, list) else value)
                for key, value in META_DEFAULTS.items()}
        meta.update(retrieval.meta)
        meta.setdefault('identifier', identifier)
        meta.update({
            'jurisdiction': source.code,
            'language': retrieval.language,
            'version': retrieval.version,
            'version_date': retrieval.version_date,
        })
        # Only XML parsers validate their source against an XSD
        if getattr(parser, 'valid', None) is not None:
            meta['valid'] = parser.valid
        doc['meta'] = meta

    doc = {'schema_version': SCHEMA_VERSION, **doc}
    if validate:
        _validate(doc)
    return doc


def _validate(doc):
    validator = LegalJSONValidator()
    try:
        jsonschema.validate(instance=doc, schema=validator.schema)
    except jsonschema.ValidationError as e:
        location = '/'.join(str(part) for part in e.absolute_path) or '(root)'
        raise ValidationError(f"Output does not conform to legalJSON at {location}: {e.message}") from e
