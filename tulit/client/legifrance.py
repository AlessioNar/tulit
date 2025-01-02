import requests
from tulit.client.client import Client
import argparse

class LegifranceClient(Client):
    def __init__(self, client_id, client_secret, download_dir='./data/france/legifrance', log_dir='./data/logs'):
        super().__init__(download_dir, log_dir)
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app"

    def get_token(self):
        token_url = "https://sandbox-oauth.piste.gouv.fr/api/oauth/token"
        payload = {
            'grant_type': 'client_credentials',            
            "scope": "openid",
            "client_id": self.client_id,
            "client_secret": self.client_secret,        
            }
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
        return response.json()['access_token']

    def get_dossier_legislatif(self, dossier_id):
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
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    
def main():
    parser = argparse.ArgumentParser(description='Legifrance Client')
    parser.add_argument('--client_id', type=str, help='Client ID for OAuth')
    parser.add_argument('--client_secret', type=str, help='Client Secret for OAuth')
    parser.add_argument('--dossier_id', type=str, required=True, help='Dossier ID to retrieve')
    args = parser.parse_args()
    
    client = LegifranceClient(args.client_id, args.client_secret)
    dossier = client.get_dossier_legislatif(args.dossier_id)
    print(dossier)

if __name__ == "__main__":
    main()