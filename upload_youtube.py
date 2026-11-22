
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parent

VIDEO = ROOT / "shorts/short-2-math/output/short-2-final.mp4"
TOKEN = ROOT / "token.json"

TITLE = "The ×11 Math Trick That Feels Like Magic!"
DESCRIPTION = """Learn the quick multiplication trick for multiplying
any two-digit number by 11.

Try it yourself: 63 × 11!

#Shorts #MathTricks #Maths"""

TAGS = ["Shorts", "Math Tricks", "Mental Math", "Maths"]

if not VIDEO.exists():
    raise FileNotFoundError(f"Video not found: {VIDEO}")

if not TOKEN.exists():
    raise FileNotFoundError("token.json not found. Run auth_login.py first.")

credentials = Credentials.from_authorized_user_file(
    str(TOKEN),
    scopes=[
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube"
    ]
)

youtube = build("youtube", "v3", credentials=credentials)

body = {
    "snippet": {
        "title": TITLE,
        "description": DESCRIPTION,
        "tags": TAGS,
        "categoryId": "27"
    },
    "status": {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": False
    }
}

media = MediaFileUpload(
    str(VIDEO),
    mimetype="video/mp4",
    resumable=True
)

print("Uploading video privately...")

request = youtube.videos().insert(
    part="snippet,status",
    body=body,
    media_body=media
)

response = request.execute()

print("\nUPLOAD SUCCESSFUL!")
print("Video ID:", response["id"])
print(
    "YouTube Studio:",
    "https://studio.youtube.com/video/" + response["id"] + "/edit"
)
