import requests
from tulit.client.client import Client

class LegiluxClient(Client):
    def __init__(self, download_dir, log_dir):
        super().__init__(download_dir, log_dir)
        #self.endpoint = "https://legilux.public.lu/eli/etat/leg/loi"

    def build_request_url(self, eli) -> str:
        """
        Build the request URL based on the source and parameters.
        """
        url = eli
        return url
    
    def fetch_content(self, url):
        """
        Fetch the content of the document.
        """
        headers = {"Accept": "application/xml"}
        response = requests.get(url, headers=headers)
        return response

    def download(self, eli):
        file_paths = []
        url = self.build_request_url(eli)
        response = self.fetch_content(url)        
        filename = eli.split('loi/')[1].replace('/', '_')
        if response.status_code == 200:
            file_paths.append(self.handle_response(response, filename=filename))
            print(f"Document downloaded successfully and saved to {file_paths}")
            return file_paths
        else:
            print(f"Failed to download document. Status code: {response.status_code}")
            return None

if __name__ == "__main__":
    downloader = LegiluxClient(download_dir='./tests/data/legilux', log_dir='./tests/metadata/logs')
    downloader.download(eli='http://data.legilux.public.lu/eli/etat/leg/loi/2006/07/31/n2/jo')