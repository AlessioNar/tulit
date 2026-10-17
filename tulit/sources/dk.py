"""
Denmark: Retsinformation.
"""
import re
from typing import Any, Optional

from lxml import etree

from tulit.client.state.denmark import (
    RETSINFORMATION, RetsinformationClient, consolidated_act, normalise_eli_path
)
from tulit.parser.exceptions import FileLoadError
from tulit.sources.base import CONSOLIDATED, ORIGINAL, Retrieval, Source


class DenmarkSource(Source):
    code = 'DK'
    name = 'Denmark'
    source_name = 'Retsinformation (Civilstyrelsen)'
    languages = ('dan',)
    identifier_help = ("an ELI path such as 'lta/2018/502' for an act (lov) or its "
                       "consolidation (lovbekendtgørelse), or 'accn/A20180050230'")
    version_from_identifier = True
    eli_patterns = (re.compile(
        r'^https?://(www\.)?retsinformation\.dk/eli/(?P<id>lta/\d{4}/\d+|accn/[A-Z]\d+)(/(xml|pdf|html))?/?$'),)

    def retrieve(
        self,
        identifier: str,
        version: Optional[str],
        date: Optional[str],
        language: Optional[str],
        download_dir: str,
        metadata: bool = True,
        **options: Any,
    ) -> Retrieval:
        if date:
            raise ValueError(
                "Retsinformation is retrieved by document: an act (lov) or its current "
                "consolidation (lovbekendtgørelse); a date cannot be selected"
            )
        client = RetsinformationClient(download_dir=download_dir)
        path = normalise_eli_path(identifier)
        root = etree.parse(client.download(path)).getroot()
        is_consolidation = _meta(root, 'DocumentType', '').startswith('LBK')
        if version is None:
            version = CONSOLIDATED if is_consolidation else ORIGINAL

        if version == ORIGINAL and is_consolidation:
            act = consolidated_act(root)
            if act is None:
                raise FileLoadError(f"Cannot tell which act the consolidation {path} consolidates")
            path = act[0]
            root = etree.parse(client.download(path)).getroot()
        elif version == CONSOLIDATED and not is_consolidation:
            title = _meta(root, 'PopularTitle') or _meta(root, 'DocumentTitle') or ''
            found = client.find_consolidation(path, title)
            if found is None:
                raise FileLoadError(
                    f"No consolidation (lovbekendtgørelse) of {path} found on Retsinformation; "
                    "if the act was never amended, its original text is the text in force"
                )
            path = found
            root = etree.parse(client.download(path)).getroot()

        act = consolidated_act(root) if version == CONSOLIDATED else None
        work_path = act[0] if act else path
        meta = {
            'eli': f'{RETSINFORMATION}/eli/{work_path}' if work_path.startswith('lta/') else None,
            'date_document': act[1] if act else _meta(root, 'DiesSigni'),
            'in_force': _meta(root, 'Status') == 'Valid',
            'source': f'{RETSINFORMATION}/eli/{path}',
        }
        version_date = (_meta(root, 'StartDate') or _meta(root, 'DiesEdicti')) if version == CONSOLIDATED \
            else _meta(root, 'DiesSigni')
        return Retrieval(
            path=client.download(path),
            parser='lexdania',
            version=version,
            language='dan',
            version_date=version_date,
            meta=meta,
        )


def _meta(root: etree._Element, name: str, default: Optional[str] = None) -> Optional[str]:
    element = root.find(f'Meta/{name}')
    text = (element.text or '').strip() if element is not None else ''
    return text or default
