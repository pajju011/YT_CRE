
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_FILE = os.path.join(BASE_DIR, "client_secrets.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

if not os.path.exists(CLIENT_FILE):
    raise FileNotFoundError("client_secrets.json not found!")

flow = InstalledAppFlow.from_client_secrets_file(
    CLIENT_FILE, SCOPES
)

credentials = flow.run_local_server(
    port=0,
    access_type="offline",
    prompt="consent"
)

with open(TOKEN_FILE, "w", encoding="utf-8") as token:
    token.write(credentials.to_json())

print("\nSUCCESS: token.json created successfully!")
print("YouTube authentication completed.")
