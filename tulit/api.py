"""
High-level entry points for tulit.

``fetch`` turns an identifier into validated legalJSON in one call: it
downloads the act from its source, picks the matching parser and attaches
the document metadata.

Example
-------
>>> import tulit
>>> doc = tulit.fetch("32024R0903")
>>> doc["meta"]["eli"]
'http://data.europa.eu/eli/reg/2024/903/oj'
"""
import logging
import os
import tempfile
from typing import Any, Optional

import jsonschema

from tulit.client.eu.cellar import CellarClient
from tulit.parser.exceptions import FileLoadError, ValidationError
from tulit.parser.parser import LegalJSONValidator
from tulit.parser.registry import get_parser

logger = logging.getLogger(__name__)

CELLAR_RESOURCE = 'http://publications.europa.eu/resource/cellar/'

# Cellar download format -> registry format id of the parser that reads it
CELLAR_FORMATS = {
    'fmx4': 'formex',
    'xhtml': 'cellar-xhtml',
    'html': 'cellar-html',
}


def fetch(
    celex: str,
    format: str = 'fmx4',
    language: str = 'ENG',
    download_dir: Optional[str] = None,
    metadata: bool = True,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Download an EU act from Cellar and return it as legalJSON.

    Parameters
    ----------
    celex : str
        CELEX number of the act, e.g. '32024R0903'.
    format : str, optional
        Cellar format to download and parse: 'fmx4' (Formex 4, default),
        'xhtml' or 'html'.
    language : str, optional
        Three-letter language code of the expression, e.g. 'ENG' (default),
        'FRA', 'DEU'.
    download_dir : str, optional
        Directory where the source files are kept. When omitted, files are
        downloaded to a temporary directory that is removed afterwards.
    metadata : bool, optional
        Attach the Cellar work metadata (ELI, dates, in-force status,
        amends/repeals/corrects) as the ``meta`` object. Default True.
    validate : bool, optional
        Validate the result against the legalJSON schema. Default True.

    Returns
    -------
    dict
        The act as legalJSON.

    Raises
    ------
    ValueError
        If ``format`` is not supported.
    FileLoadError
        If Cellar has no document for the act in that format and language.
    ValidationError
        If ``validate`` is True and the result does not conform to the
        legalJSON schema.
    """
    if format not in CELLAR_FORMATS:
        raise ValueError(
            f"Unsupported format '{format}'. Choose one of: {', '.join(CELLAR_FORMATS)}"
        )

    if download_dir is not None:
        return _fetch_into(celex, format, language, download_dir, metadata, validate)
    with tempfile.TemporaryDirectory(prefix='tulit-') as tmp_dir:
        return _fetch_into(celex, format, language, tmp_dir, metadata, validate)


def _fetch_into(celex, format, language, download_dir, metadata, validate):
    client = CellarClient(download_dir=download_dir)
    paths = [p for p in (client.download(celex, format=format, language=language) or []) if p]
    if not paths:
        raise FileLoadError(
            f"No {format} document found in Cellar for {celex} in language {language.upper()}"
        )

    parser = get_parser(CELLAR_FORMATS[format])
    # A Formex act may be split over several items (DOC_1.xml, DOC_2.xml, ...);
    # the Formex parser reads the whole folder and finds the act and its annexes
    source_path = paths[0] if len(paths) == 1 else os.path.commonpath(paths)
    parser.parse(source_path)
    doc = parser.to_dict()

    if metadata:
        meta = client.get_metadata(celex)
        meta['source'] = _source_uri(paths, download_dir)
        # Only XML parsers validate their source against an XSD
        meta['valid'] = getattr(parser, 'valid', None)
        doc['meta'] = meta

    if validate:
        _validate(doc)
    return doc


def _source_uri(paths, download_dir):
    """Cellar URI of the downloaded item, or of the manifestation holding several items."""
    ids = [os.path.relpath(p, download_dir).replace(os.sep, '/') for p in paths]
    ids = [os.path.splitext(i)[0] if '/' in i else i for i in ids]
    if len(ids) == 1:
        return CELLAR_RESOURCE + ids[0]
    return CELLAR_RESOURCE + os.path.commonprefix(ids).rstrip('/').rsplit('/', 1)[0]


def _validate(doc):
    validator = LegalJSONValidator()
    try:
        jsonschema.validate(instance=doc, schema=validator.schema)
    except jsonschema.ValidationError as e:
        location = '/'.join(str(part) for part in e.absolute_path) or '(root)'
        raise ValidationError(f"Output does not conform to legalJSON at {location}: {e.message}") from e
