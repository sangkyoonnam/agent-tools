"""Download and manage assets from Notion."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Queue, Empty
from urllib.parse import urlparse

import httpx
from rich.console import Console

console = Console()

ASSETS_DIR_NAME = "_assets"


@dataclass
class AssetTask:
    url: str
    page_dir: Path
    block_id: str
    filename: str

    @property
    def rel_path(self) -> str:
        return f"{ASSETS_DIR_NAME}/{self.filename}"

    @property
    def abs_path(self) -> Path:
        return self.page_dir / ASSETS_DIR_NAME / self.filename


class AssetDownloader:
    """Background asset downloader that runs concurrently with page sync."""

    def __init__(self, workers: int = 4):
        self.queue: Queue[AssetTask | None] = Queue()
        self.workers = workers
        self.success = 0
        self.errors = 0
        self._lock = threading.Lock()
        self._executor: ThreadPoolExecutor | None = None
        self._futures = []

    def start(self):
        """Start background download workers."""
        self._executor = ThreadPoolExecutor(max_workers=self.workers)
        for _ in range(self.workers):
            self._futures.append(self._executor.submit(self._worker))

    def enqueue(self, url: str, page_dir: Path, block_id: str) -> str:
        """Queue an asset for download. Returns the relative path for markdown."""
        filename = _make_filename(url, block_id)
        task = AssetTask(url=url, page_dir=page_dir, block_id=block_id, filename=filename)
        self.queue.put(task)
        return task.rel_path

    def stop_and_wait(self):
        """Signal workers to stop and wait for completion."""
        if not self._executor:
            return
        # Send poison pills
        for _ in range(self.workers):
            self.queue.put(None)
        self._executor.shutdown(wait=True)
        self._executor = None

    def _worker(self):
        while True:
            task = self.queue.get()
            if task is None:
                break
            self._download(task)
            self.queue.task_done()

    def _download(self, task: AssetTask):
        if task.abs_path.exists():
            with self._lock:
                self.success += 1
            return

        task.abs_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with httpx.stream("GET", task.url, follow_redirects=True, timeout=30) as resp:
                resp.raise_for_status()
                with open(task.abs_path, "wb") as f:
                    for chunk in resp.iter_bytes(8192):
                        f.write(chunk)
            with self._lock:
                self.success += 1
        except Exception as e:
            with self._lock:
                self.errors += 1
            console.print(f"[yellow]  Asset failed: {task.filename}: {e}[/yellow]")


# Module-level downloader
_downloader: AssetDownloader | None = None


def get_downloader() -> AssetDownloader:
    global _downloader
    if _downloader is None:
        _downloader = AssetDownloader()
    return _downloader


def start_downloader(workers: int = 4) -> AssetDownloader:
    global _downloader
    _downloader = AssetDownloader(workers=workers)
    _downloader.start()
    return _downloader


def _make_filename(url: str, block_id: str) -> str:
    parsed = urlparse(url.split("?")[0])
    original_name = Path(parsed.path).name
    if not original_name or original_name == "/":
        original_name = "file"
    return f"{block_id}_{original_name}"
