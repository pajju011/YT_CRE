
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent
TOKEN = ROOT / "token.json"

VIDEO_ID = "iT8NEPwvpRU"

# November 20, 2026, 6:00 PM IST
PUBLISH_AT = "2026-11-20T12:30:00Z"

if not TOKEN.exists():
    raise FileNotFoundError("token.json not found!")

credentials = Credentials.from_authorized_user_file(
    str(TOKEN),
    scopes=[
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube"
    ]
)

youtube = build("youtube", "v3", credentials=credentials)

response = youtube.videos().update(
    part="status",
    body={
        "id": VIDEO_ID,
        "status": {
            "privacyStatus": "private",
            "publishAt": PUBLISH_AT,
            "selfDeclaredMadeForKids": False
        }
    }
).execute()

print("SCHEDULING SUCCESSFUL!")
print("Video ID:", response["id"])
print("Scheduled time: November 20, 2026, 6:00 PM IST")
print("Visibility:", response["status"]["privacyStatus"])
print("Publish at:", response["status"]["publishAt"])
