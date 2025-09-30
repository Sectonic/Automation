from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials 
import datetime as dt
import os, json
from urllib.parse import quote

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_credentials(token_file: str, env_var: str):
    if os.path.exists(token_file):
        parsed = json.load(open(token_file))["installed"]
    else:
        parsed = json.load(os.getenv(env_var))["installed"]
    return Credentials.from_authorized_user_info(parsed, scopes=SCOPES)

def get_gmail_service(credentials: Credentials):
    return build("gmail", "v1", credentials=credentials)

def _gmail_link_from_message(headers: dict, thread_id: str, user_index: int) -> str:
    """
    Construct a Gmail web link for the message.
    user_index = 0 (personal), 1 (work)
    """
    msg_id = headers.get("Message-ID") or headers.get("Message-Id") or headers.get("Message-id")
    if msg_id:
        clean = msg_id.strip("<>")
        return f"https://mail.google.com/mail/u/{user_index}/#search/rfc822msgid%3A{quote(clean)}"
    return f"https://mail.google.com/mail/u/{user_index}/#inbox/{thread_id}"

def fetch_emails_between(service, start_time: dt.datetime, end_time: dt.datetime, user_index, source_label=None):
    q = f"after:{int(start_time.timestamp())} before:{int(end_time.timestamp())}"
    results = service.users().messages().list(userId="me", q=q).execute()
    messages = results.get("messages", [])

    email_data = []
    for m in messages:
        md = service.users().messages().get(userId="me", id=m["id"]).execute()
        headers = {h["name"]: h["value"] for h in md["payload"].get("headers", [])}
        snippet = md.get("snippet", "")
        link = _gmail_link_from_message(headers, md.get("threadId", ""), user_index)
        email_data.append({
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "snippet": snippet,
            "link": link,
            "source": source_label or "unknown",
        })
    return email_data