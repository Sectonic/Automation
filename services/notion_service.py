"""Notion API service for data source backed database operations."""

import requests
import time
from typing import Any, Dict, Optional


class NotionService:
    """Service for interacting with Notion API."""
    
    def __init__(self, api_key: str, notion_version: str = "2025-09-03", max_retries: int = 5, base_backoff: float = 1.0):
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": notion_version,
            "Content-Type": "application/json",
        }
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self._session = requests.Session()
    
    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform a Notion API request with simple retry/backoff for rate limits."""

        url = f"{self.base_url}{path}"
        attempt = 0

        while True:
            response = self._session.request(method, url, headers=self.headers, json=payload)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                try:
                    sleep_seconds = float(retry_after)
                except (TypeError, ValueError):
                    sleep_seconds = self.base_backoff * (2 ** attempt)
                time.sleep(max(sleep_seconds, self.base_backoff))
                attempt += 1
            elif 500 <= response.status_code < 600 and attempt < self.max_retries:
                time.sleep(self.base_backoff * (2 ** attempt))
                attempt += 1
            else:
                response.raise_for_status()
                return response.json()

            if attempt >= self.max_retries:
                response.raise_for_status()
    
    def query_database(self, database_id: str, filter_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query a Notion database with optional filters."""

        payload: Dict[str, Any] = {}
        if filter_dict:
            payload["filter"] = filter_dict

        return self._request("POST", f"/data_sources/{database_id}/query", payload)
    
    def create_page(self, database_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new page in a Notion data source."""

        payload = {
            "parent": {
                "data_source_id": database_id,
            },
            "properties": properties,
        }

        return self._request("POST", "/pages", payload)
    
    def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing Notion page."""

        payload = {"properties": properties}
        return self._request("PATCH", f"/pages/{page_id}", payload)
