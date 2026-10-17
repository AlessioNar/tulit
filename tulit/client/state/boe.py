"""
Boletín Oficial del Estado (BOE) client.

This module contains the BOEClient class, which is used to download XML files from the BOE API endpoint.

The documentation for the BOE API can be found at https://www.boe.es/datosabiertos/documentos/APIsumarioBOE.pdf

"""

import logging
import os
import re
import requests
from tulit.client.client import Client
from tulit.parser.exceptions import ContentTypeError, FileLoadError, NetworkError

CONSOLIDATED_API = 'https://www.boe.es/datosabiertos/api/legislacion-consolidada/id'
GAZETTE_XML = 'https://www.boe.es/diario_boe/xml.php'
USER_AGENT = 'tulit (+https://github.com/AlessioNar/tulit)'
_BOE_ID = re.compile(r'^BOE-[AB]-\d{4}-\d+$')

class BOEClient(Client):
    def __init__(self, download_dir, log_dir=None, proxies=None):
        super().__init__(download_dir=download_dir, log_dir=log_dir, proxies=proxies)
        self.logger = logging.getLogger(self.__class__.__name__)

    def download(self, id, fmt=None):
        try:
            url = 'https://www.boe.es/diario_boe/xml.php?id='
            self.logger.info(f"Requesting BOE document with id: {id}")
            response = requests.get(url + id)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if fmt:
                if fmt == 'xml' and 'xml' not in content_type:
                    raise ContentTypeError(f"Expected XML from the BOE but got: {content_type}", content_type)
                if fmt == 'html' and 'html' not in content_type:
                    raise ContentTypeError(f"Expected HTML from the BOE but got: {content_type}", content_type)
                if fmt == 'pdf' and 'pdf' not in content_type:
                    raise ContentTypeError(f"Expected PDF from the BOE but got: {content_type}", content_type)
            self.logger.info(f"Successfully retrieved BOE document: {id}")
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"An error occurred: {e}")
            return None

    def download_consolidated(self, boe_id):
        """
        Download an act from the consolidated-legislation API.

        Saves the text (every version of every block) as ``texto.xml`` and the
        act's metadata as ``metadatos.xml`` in one folder and returns it.
        Raises FileLoadError if the act is not in the consolidated database.
        """
        boe_id = _check_id(boe_id)
        folder = os.path.join(self.download_dir, 'ES', boe_id)
        os.makedirs(folder, exist_ok=True)
        for part, filename in (('texto', 'texto.xml'), ('metadatos', 'metadatos.xml')):
            target = os.path.join(folder, filename)
            if os.path.exists(target):
                continue
            url = f'{CONSOLIDATED_API}/{boe_id}/{part}'
            try:
                # The API answers 400 without an explicit Accept header
                response = requests.get(url, headers={'Accept': 'application/xml', 'User-Agent': USER_AGENT},
                                        timeout=60)
            except requests.RequestException as e:
                raise NetworkError(f"BOE request failed for {url}: {e}") from e
            if response.status_code == 404 or b'<code>404</code>' in response.content[:500]:
                raise FileLoadError(f"{boe_id} is not in the BOE consolidated-legislation database")
            if response.status_code != 200:
                raise NetworkError(f"BOE request failed for {url}: HTTP {response.status_code}")
            with open(target, 'wb') as f:
                f.write(response.content)
        return folder

    def download_gazette(self, boe_id):
        """Download the act as published in the gazette (BOE XML); returns the file path."""
        boe_id = _check_id(boe_id)
        target = os.path.join(self.download_dir, 'ES', f'{boe_id}.xml')
        if not os.path.exists(target):
            try:
                response = requests.get(GAZETTE_XML, params={'id': boe_id},
                                        headers={'User-Agent': USER_AGENT}, timeout=60)
                response.raise_for_status()
            except requests.RequestException as e:
                raise NetworkError(f"BOE request failed for {boe_id}: {e}") from e
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(response.content)
        return target


def _check_id(boe_id):
    boe_id = boe_id.strip()
    if not _BOE_ID.match(boe_id):
        raise ValueError(f"'{boe_id}' is not a BOE identifier (e.g. 'BOE-A-2018-16673')")
    return boe_id

