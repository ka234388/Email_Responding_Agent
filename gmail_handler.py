# gmail_handler.py
import base64
import os
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify"  # to mark emails as read
]

def authenticate_gmail():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def get_unread_emails(service):
    results = service.users().messages().list(
        userId="me", labelIds=["INBOX"], q="is:unread"
    ).execute()
    messages = results.get("messages", [])
    emails = []
    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()
        headers = msg_data["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender  = next((h["value"] for h in headers if h["name"] == "From"), "")
        # Extract body
        body = ""
        parts = msg_data["payload"].get("parts", [])
        if parts:
            for part in parts:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    body = base64.urlsafe_b64decode(data).decode("utf-8")
                    break
        else:
            data = msg_data["payload"]["body"].get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8")

        emails.append({
            "id": msg["id"],
            "sender": sender,
            "subject": subject,
            "body": body
        })
    return emails

def send_reply(service, original_sender, subject, reply_text):
    message = MIMEText(reply_text)
    message["to"] = original_sender
    message["subject"] = f"Re: {subject}"
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    print(f"✅ Reply sent to {original_sender}")

def mark_as_read(service, msg_id):
    service.users().messages().modify(
        userId="me", id=msg_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()