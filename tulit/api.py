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
"""
import logging
import tempfile
from typing import Any, Optional

import jsonschema

from tulit.parser.exceptions import ValidationError
from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser
from tulit.sources import VERSIONS, Source, get_source, source_for_eli
from tulit.sources.eu import CELLAR_FORMATS

logger = logging.getLogger(__name__)

__all__ = ['fetch', 'CELLAR_FORMATS']

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
    source, identifier = _resolve(identifier, jurisdiction)
    version = version or source.default_version
    if version not in VERSIONS:
        raise ValueError(f"Unknown version '{version}'. Choose one of: {', '.join(VERSIONS)}")
    if version not in source.versions:
        raise ValueError(
            f"{source.name} ({source.source_name}) does not publish the {version} version; "
            f"available: {', '.join(source.versions)}"
        )

    if language and source.languages and language.lower() not in source.languages:
        raise ValueError(
            f"{source.name} publishes in {', '.join(source.languages)}, not '{language}'"
        )
    unknown = sorted(set(options) - set(source.options))
    if unknown:
        raise ValueError(f"Unsupported option(s) for {source.name}: {', '.join(unknown)}")

    if download_dir is not None:
        return _fetch_into(source, identifier, version, date, language, download_dir,
                           metadata, validate, options)
    with tempfile.TemporaryDirectory(prefix='tulit-') as tmp_dir:
        return _fetch_into(source, identifier, version, date, language, tmp_dir,
                           metadata, validate, options)


def _resolve(identifier: str, jurisdiction: Optional[str]) -> tuple[Source, str]:
    if identifier.startswith(('http://', 'https://')):
        if jurisdiction:
            source = get_source(jurisdiction)
            resolved = source.identifier_from_eli(identifier)
            if resolved is None:
                raise ValueError(f"{identifier} is not an ELI of {source.name}")
            return source, resolved
        found = source_for_eli(identifier)
        if found is None:
            raise ValueError(f"No supported source recognises the ELI {identifier}")
        return found
    return get_source(jurisdiction or 'EU'), identifier


def _fetch_into(source, identifier, version, date, language, download_dir,
                metadata, validate, options):
    retrieval = source.retrieve(identifier, version, date, language, download_dir,
                                metadata=metadata, **options)
    parser = get_parser(retrieval.parser, **retrieval.parser_options)
    parser.parse(retrieval.path)
    doc = parser.to_dict()

    if metadata:
        meta = {key: (list(value) if isinstance(value, list) else value)
                for key, value in META_DEFAULTS.items()}
        meta.update(retrieval.meta)
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
