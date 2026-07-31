import json
from google.oauth2.credentials import Credentials

def get_creds():
    return Credentials.from_authorized_user_info(json.loads('{}'))
