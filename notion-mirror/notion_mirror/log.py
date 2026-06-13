"""Sync execution logging."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path.home() / ".notion_mirror_logs"


class SyncLog:
    def __init__(self):
        LOG_DIR.mkdir(exist_ok=True)
        self.start_time = datetime.now(timezone.utc)
        self.entries: list[dict] = []
        self.log_file = LOG_DIR / f"{self.start_time.strftime('%Y%m%d_%H%M%S')}.jsonl"

    def log(self, action: str, target: str, status: str = "ok", detail: str = ""):
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "target": target,
            "status": status,
        }
        if detail:
            entry["detail"] = detail
        self.entries.append(entry)
        # Append to file immediately
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def summary(self) -> dict:
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        ok = sum(1 for e in self.entries if e["status"] == "ok")
        errors = sum(1 for e in self.entries if e["status"] == "error")
        skipped = sum(1 for e in self.entries if e["status"] == "skipped")
        return {
            "total": len(self.entries),
            "ok": ok,
            "errors": errors,
            "skipped": skipped,
            "elapsed_seconds": round(elapsed, 1),
            "log_file": str(self.log_file),
        }
