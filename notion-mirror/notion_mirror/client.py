"""Notion API client wrapper with rate limiting and pagination."""

from __future__ import annotations

import time
from notion_client import Client
from rich.console import Console

console = Console()


class NotionMirrorClient:
    def __init__(self, token: str):
        self.client = Client(auth=token)
        self._last_request = 0.0
        self._min_interval = 0.35  # ~3 req/sec to stay under rate limit

    def _throttle(self):
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.time()

    def search_all(
        self,
        filter_type: str | None = None,
        last_edited_after: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Search workspace. filter_type: 'page' or 'database'.

        Use limit for bounded smoke tests against large workspaces.
        """
        results = []
        cursor = None

        while True:
            self._throttle()
            params: dict = {"page_size": min(100, limit or 100)}
            if filter_type == "page":
                params["filter"] = {"value": "page", "property": "object"}
            # database filter not supported by API; filter client-side
            if cursor:
                params["start_cursor"] = cursor

            resp = self.client.search(**params)
            items = resp.get("results", [])

            if filter_type == "database":
                items = [i for i in items if i.get("object") == "database"]

            if last_edited_after:
                items = [
                    item for item in items
                    if item.get("last_edited_time", "") >= last_edited_after
                ]

            results.extend(items)

            if limit is not None and len(results) >= limit:
                return results[:limit]
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")

        return results

    def get_page(self, page_id: str) -> dict:
        self._throttle()
        return self.client.pages.retrieve(page_id=page_id)

    def get_blocks(self, block_id: str) -> list[dict]:
        """Get all child blocks, handling pagination."""
        blocks = []
        cursor = None

        while True:
            self._throttle()
            params: dict = {"block_id": block_id, "page_size": 100}
            if cursor:
                params["start_cursor"] = cursor

            resp = self.client.blocks.children.list(**params)
            blocks.extend(resp.get("results", []))

            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")

        return blocks

    def get_blocks_recursive(self, block_id: str) -> tuple[list[dict], dict[str, list[dict]]]:
        """Get all blocks recursively. Returns (top_blocks, children_map)."""
        top_blocks = self.get_blocks(block_id)
        children_map: dict[str, list[dict]] = {}

        def fetch_children(blocks: list[dict]):
            for block in blocks:
                if block.get("has_children"):
                    bid = block["id"]
                    children = self.get_blocks(bid)
                    children_map[bid] = children
                    fetch_children(children)

        fetch_children(top_blocks)
        return top_blocks, children_map

    def query_database(self, database_id: str) -> list[dict]:
        """Query all items in a database via data_sources API (2025-09-03+)."""
        # Retrieve database to get data_source_id
        db = self.get_database(database_id)
        data_sources = db.get("data_sources", [])
        if not data_sources:
            return []
        data_source_id = data_sources[0]["id"]

        items = []
        cursor = None

        while True:
            self._throttle()
            params: dict = {"data_source_id": data_source_id, "page_size": 100}
            if cursor:
                params["start_cursor"] = cursor

            resp = self.client.data_sources.query(**params)
            items.extend(resp.get("results", []))

            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")

        return items

    def get_database(self, database_id: str) -> dict:
        self._throttle()
        return self.client.databases.retrieve(database_id=database_id)
