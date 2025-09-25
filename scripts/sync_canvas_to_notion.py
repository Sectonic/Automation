"""Sync Canvas calendar events to a Notion database."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

import requests
from icalendar import Calendar
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.notion_service import NotionService


ICS_FEED_URL = (
    "https://gatech.instructure.com/feeds/calendars/"
    "user_4dcnumFkgDj28IbshxzypwvW4JI5PAKOlhCV2fEp.ics"
)
NOTION_DATABASE_ID = "2745992a-07ba-81a0-ad24-000b6dcb3d8f"


@dataclass
class CalendarEvent:
    title: str
    course: Optional[str]
    due_date: date
    summary: str

SUMMARY_PATTERN = re.compile(r"^(?P<title>.*?)\s*\[(?P<course>[^\]]+)\]\s*$")

def fetch_ics(url: str) -> str:
    """Download the ICS feed content from the provided URL."""

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def parse_events(ics_content: str) -> List[CalendarEvent]:
    """Parse ICS text into a list of calendar events."""

    calendar = Calendar.from_ical(ics_content)
    events: List[CalendarEvent] = []

    for component in calendar.walk():
        if component.name != "VEVENT":
            continue

        summary = component.get("SUMMARY")
        if not summary:
            continue

        summary_text = str(summary)
        match = SUMMARY_PATTERN.match(summary_text)
        if match:
            title = match.group("title").strip()
            course = match.group("course").strip()
        else:
            title = summary_text.strip()
            course = None

        dtstart = component.get("DTSTART")
        if not dtstart:
            continue

        dt_value = dtstart.dt
        if isinstance(dt_value, datetime):
            due = dt_value.date()
        elif isinstance(dt_value, date):
            due = dt_value
        else:
            continue

        events.append(CalendarEvent(title=title, course=course, due_date=due, summary=summary_text))

    return events


def upsert_notion_page(notion_service: NotionService, event: CalendarEvent) -> None:
    """Create a Notion database entry for the given event."""
    
    query_response = notion_service.query_database(
        database_id=NOTION_DATABASE_ID,
        filter_dict={
            "and": [
                {
                    "property": "Summary",
                    "rich_text": {
                        "equals": event.summary
                    }
                },
                {
                    "property": "Date",
                    "date": {
                        "equals": event.due_date.isoformat()
                    }
                }
            ]
        }
    )
    
    results = query_response.get('results', [])
    
    if not results:
        properties = {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": event.title,
                        }
                    }
                ]
            },
            "Date": {
                "date": {
                    "start": event.due_date.isoformat(),
                }
            },
            "Done": {
                "checkbox": False
            },
            "Summary": {
                "rich_text": [
                    {
                        "text": {
                            "content": event.summary
                        }
                    }
                ]
            }
        }
        
        if event.course:
            properties["Course"] = {
                "select": {
                    "name": event.course
                }
            }
        
        notion_service.create_page(
            database_id=NOTION_DATABASE_ID,
            properties=properties
        )


def main() -> None:
    load_dotenv()
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        raise RuntimeError("Missing NOTION_API_KEY environment variable")

    ics_content = fetch_ics(ICS_FEED_URL)
    events = parse_events(ics_content)

    notion_service = NotionService(api_key)

    for event in events:
        upsert_notion_page(notion_service, event)


if __name__ == "__main__":
    main()

