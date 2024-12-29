from tulit.download.download import Client
import requests
import logging
from datetime import datetime


class NormattivaClient(Client):
    def __init__(self, download_dir, log_dir):
        super().__init__(download_dir, log_dir)
        self.endpoint = "https://www.normattiva.it/do/atto/caricaAKN"
    
    def build_request_url(self, params=None) -> str:
        """
        Build the request URL based on the source and parameters.
        """
        uri = f"https://www.normattiva.it/eli/id/{params['date']}//{params['codiceRedaz']}/CONSOLIDATED"
        # In case we want to use the NIR:URI instead of ELI
        #uri = f"https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:{params['date']};{params['number']}"
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
            
            # Make a GET request to the URI to get the cookies        
            cookies_response = requests.get(uri)
            cookies_response.raise_for_status()
            cookies = cookies_response.cookies

            headers = {
                'Accept': "text/xml",
                'Accept-Encoding': "gzip, deflate, br, zstd",
                'Accept-Language': "en-US,en;q=0.9",
                
            }                     
            response = requests.get(url, headers=headers, cookies=cookies)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logging.error(f"Error sending GET request: {e}")
            return None    
        
    def download(self, dataGU, codiceRedaz, dataVigenza = datetime.today().strftime('%Y%m%d')):     
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
        
        uri, url = self.build_request_url(params)
        response = self.fetch_content(uri, url)
        
        # If the response in HTML, raise an error saying that the date or codiceRedaz is wrong
        if 'text/html' in response.headers.get('Content-Type', ''):
            logging.error(f"Error downloading document: there is not an XML file with the following parameters: {params}")
            return None
        
        file_path = self.handle_response(response=response, filename=f"{params['dataGU']}_{params['codiceRedaz']}_VIGENZA_{params['dataVigenza']}")
        document_paths.append(file_path)
        return document_paths

# Example usage
if __name__ == "__main__":
    
    downloader = NormattivaClient(download_dir='./tests/data/akn/italy', log_dir='./tests/logs')
    #documents = downloader.download(dataGU='19410716', codiceRedaz='041U0633')
    documents = downloader.download(dataGU='19410716', codiceRedaz='041U0633', dataVigenza='20211231')

    
    print(documents)
