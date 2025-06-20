import logging
import requests
from tulit.client.client import Client
import argparse

class LegifranceClient(Client):
    def __init__(self, client_id, client_secret, download_dir='./data/france/legifrance', log_dir='./data/logs'):
        super().__init__(download_dir, log_dir)
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app"
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_token(self):
        token_url = "https://sandbox-oauth.piste.gouv.fr/api/oauth/token"
        payload = {
            'grant_type': 'client_credentials',            
            "scope": "openid",
            "client_id": self.client_id,
            "client_secret": self.client_secret,        
            }
        try:
            self.logger.info("Requesting OAuth token from Legifrance")
            response = requests.post(token_url, data=payload)
            response.raise_for_status()
            self.logger.info("Successfully obtained OAuth token")
            return response.json()['access_token']
        except Exception as e:
            self.logger.error(f"Failed to obtain OAuth token: {e}")
            raise

    def get_dossier_legislatif(self, dossier_id):
        try:
            token = self.get_token()
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            url = f"{self.base_url}/consult/legiPart"
            payload = {
                "searchedString": "constitution 1958",
                "date": "2021-04-15",
                "textId": "LEGITEXT000006075116"
                }
            self.logger.info(f"Requesting dossier legislatif for dossier_id: {dossier_id}")
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            self.logger.info(f"Successfully retrieved dossier legislatif for dossier_id: {dossier_id}")
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to retrieve dossier legislatif: {e}")
            raise
    
def main():
    parser = argparse.ArgumentParser(description='Legifrance Client')
    parser.add_argument('--client_id', type=str, help='Client ID for OAuth')
    parser.add_argument('--client_secret', type=str, help='Client Secret for OAuth')
    parser.add_argument('--dossier_id', type=str, required=True, help='Dossier ID to retrieve')
    args = parser.parse_args()
    
    client = LegifranceClient(args.client_id, args.client_secret)
    try:
        dossier = client.get_dossier_legislatif(args.dossier_id)
        logging.info(f"Dossier retrieved: {dossier}")
        print(dossier)
    except Exception as e:
        logging.error(f"Error in main: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()