import os
import json
import sys
from dotenv import load_dotenv
import argparse
import datetime as dt
import re
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.gmail_service import get_credentials, get_gmail_service, fetch_emails_between
from services.gemini_service import init_gemini, summarize_emails
from services.notion_service import NotionService

NOTION_DATABASE_ID = "27e5992a-07ba-80c8-8065-000b8c75750a"
TRACKING_FILE = "email_summary_tracking.json"

def load_last_run_times():
    """Load the last run times from JSON file"""
    tracking_path = Path(TRACKING_FILE)
    if tracking_path.exists():
        try:
            with open(tracking_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    return {
        "last_morning_run": None,
        "last_evening_run": None
    }

def save_last_run_time(is_morning: bool):
    """Save the current run time to JSON file"""
    tracking_data = load_last_run_times()
    now_iso = dt.datetime.utcnow().isoformat()
    
    if is_morning:
        tracking_data["last_morning_run"] = now_iso
    else:
        tracking_data["last_evening_run"] = now_iso
    
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking_data, f, indent=2)
    
    print(f"Updated tracking file: {TRACKING_FILE}")

def get_time_window(is_morning: bool):
    """Get the appropriate time window based on the last run time"""
    tracking_data = load_last_run_times()
    now = dt.datetime.now(dt.UTC)
    
    last_run_key = "last_evening_run" if is_morning else "last_morning_run"
    last_run_time = tracking_data.get(last_run_key)
    
    if last_run_time:
        try:
            start = dt.datetime.fromisoformat(last_run_time.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            start = (now - dt.timedelta(hours=12)).replace(minute=0, second=0, microsecond=0)
    else:
        start = (now - dt.timedelta(hours=12)).replace(minute=0, second=0, microsecond=0)
    
    end = now
    return start, end


def markdown_to_notion_rich_text(md: str):
    """
    Convert a single-block markdown string to Notion rich_text segments.
    Supports [text](url) links; leaves other text as-is.
    """
    segments = []
    pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    idx = 0
    for m in pattern.finditer(md):
        # text before link
        if m.start() > idx:
            segments.append({"text": {"content": md[idx:m.start()]}})
        # the link
        anchor, url = m.group(1), m.group(2)
        segments.append({"text": {"content": anchor, "link": {"url": url}}})
        idx = m.end()
    # remainder
    if idx < len(md):
        segments.append({"text": {"content": md[idx:]}})
    return segments

def main(is_morning: bool):
    start_time, end_time = get_time_window(is_morning)

    creds_personal = get_credentials("token.json", "GMAIL_SERVICE_ACCOUNT_JSON")
    creds_career   = get_credentials("token_2.json", "GMAIL_SERVICE_ACCOUNT_JSON_2")

    service_personal = get_gmail_service(creds_personal)
    service_career   = get_gmail_service(creds_career)

    emails_personal = fetch_emails_between(service_personal, start_time, end_time, 0, source_label="personal")
    emails_career   = fetch_emails_between(service_career, start_time, end_time, 1, source_label="career")

    all_emails = emails_personal + emails_career

    if not all_emails:
        print("No emails found in this window.")
        save_last_run_time(is_morning)
        return

    init_gemini()
    groups = summarize_emails(all_emails)

    notion_key = os.getenv("NOTION_API_KEY")
    notion = NotionService(api_key=notion_key)

    for g in groups:
        properties = {
            "Title": {"title": [{"text": {"content": g["title"]}}]},
            "Label": {"select": {"name": g["label"]}},
            "Summary": {"rich_text": markdown_to_notion_rich_text(g["summary"])},
            "Date": {"date": {"start": end_time.strftime('%Y-%m-%d %H:%M')}},
        }
        notion.create_page(NOTION_DATABASE_ID, properties)

    print(f"Summaries pushed to Notion")
    save_last_run_time(is_morning)

if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--morning", type=str, default="true", help="Whether this is a morning run (default: true)")
    args = parser.parse_args()

    is_morning = args.morning.lower() == "true"
    main(is_morning=is_morning)