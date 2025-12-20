from tulit.client.client import Client
import requests
import logging
from datetime import datetime
import sys


class NormattivaClient(Client):
    def __init__(self, download_dir, log_dir, proxies=None):
        super().__init__(download_dir, log_dir, proxies)
        self.endpoint = "https://www.normattiva.it/do/atto/caricaAKN"
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def build_request_url(self, params=None) -> str:
        """
        Build the request URL based on the source and parameters.
        """
        self.logger.info(f"Building request URL with params: {params}")
        uri = f"https://www.normattiva.it/eli/id/{params['date']}//{params['codiceRedaz']}/CONSOLIDATED"
        url = f"{self.endpoint}?dataGU={params['dataGU']}&codiceRedaz={params['codiceRedaz']}&dataVigenza={params['dataVigenza']}"
        
        return uri, url
                
    def fetch_content(self, uri, url) -> requests.Response:
        """
        Send a GET request to download a file

        Parameters
        ----------
        url : str
            The URL to send the request to.

        Returns
        -------
        requests.Response
            The response from the server.

        Raises
        ------
        requests.RequestException
            If there is an error sending the request.
        """
        try:
            self.logger.info(f"Fetching cookies from URI: {uri}")
            # Make a GET request to the URI to get the cookies        
            cookies_response = requests.get(uri)
            cookies_response.raise_for_status()
            cookies = cookies_response.cookies

            headers = {
                'Accept': "text/xml",
                'Accept-Encoding': "gzip, deflate, br, zstd",
                'Accept-Language': "en-US,en;q=0.9",
                
            }                     
            self.logger.info(f"Fetching content from URL: {url}")
            response = requests.get(url, headers=headers, cookies=cookies)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            self.logger.error(f"Error sending GET request: {e}")
            return None    
        
    def download(self, dataGU, codiceRedaz, dataVigenza = datetime.today().strftime('%Y%m%d'), fmt="xml"):     
        document_paths = []
        
        # Convert the dataGU to a datetime object
        dataGU = datetime.strptime(dataGU, '%Y%m%d')
            
        params = {
            # dataGU as a string in the format YYYYMMDD
            'dataGU': dataGU.strftime('%Y%m%d'),
            'codiceRedaz': codiceRedaz,
            'dataVigenza': dataVigenza,
            # dataGU as a string in the format YYYY/MM/DD
            'date': dataGU.strftime('%Y/%m/%d')
        }
        self.logger.info(f"Downloading Normattiva document with params: {params}")
        uri, url = self.build_request_url(params)
        response = self.fetch_content(uri, url)
        if response is None:
            self.logger.error("No response received from server.")
            return None
        content_type = response.headers.get('Content-Type', '')
        if fmt == 'xml' and 'xml' not in content_type:
            self.logger.error(f"Expected XML response but got: {content_type}")
            sys.exit(1)
        if fmt == 'pdf' and 'pdf' not in content_type:
            self.logger.error(f"Expected PDF response but got: {content_type}")
            sys.exit(1)
        if fmt == 'html' and 'html' not in content_type:
            self.logger.error(f"Expected HTML response but got: {content_type}")
            sys.exit(1)
        
        file_path = self.handle_response(response=response, filename=f"{params['dataGU']}_{params['codiceRedaz']}_VIGENZA_{params['dataVigenza']}")
        document_paths.append(file_path)
        self.logger.info(f"Downloaded Normattiva document to {file_path}")
        return document_paths
