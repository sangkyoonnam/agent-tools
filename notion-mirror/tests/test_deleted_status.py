from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notion_mirror.mirror import (
    mark_deleted_remote_pages,
    mark_markdown_deleted,
    set_frontmatter_status,
)


def test_set_frontmatter_status_adds_sync_status_when_missing(tmp_path):
    note = tmp_path / "page.md"
    note.write_text(
        "---\n"
        "title: \"Example\"\n"
        "notion_id: \"abc\"\n"
        "---\n\n"
        "# Example\n\n"
        "Body stays here.\n",
        encoding="utf-8",
    )

    set_frontmatter_status(note, "deleted")

    text = note.read_text(encoding="utf-8")
    assert "sync_status: deleted\n" in text
    assert "Body stays here." in text
    assert note.exists()


def test_set_frontmatter_status_replaces_existing_sync_status(tmp_path):
    note = tmp_path / "page.md"
    note.write_text(
        "---\n"
        "title: Example\n"
        "sync_status: complete\n"
        "---\n\n"
        "# Example\n",
        encoding="utf-8",
    )

    set_frontmatter_status(note, "deleted")

    text = note.read_text(encoding="utf-8")
    assert "sync_status: deleted\n" in text
    assert "sync_status: complete\n" not in text


def test_mark_markdown_deleted_preserves_file_and_records_reason(tmp_path):
    note = tmp_path / "page.md"
    note.write_text(
        "---\n"
        "title: Example\n"
        "---\n\n"
        "# Example\n",
        encoding="utf-8",
    )

    mark_markdown_deleted(note, reason="notion_archived")

    text = note.read_text(encoding="utf-8")
    assert note.exists()
    assert "sync_status: deleted\n" in text
    assert "delete_reason: notion_archived\n" in text
    assert "deleted_at: " in text


class FakeClient:
    def __init__(self, pages):
        self.pages = pages

    def get_page(self, page_id):
        value = self.pages[page_id]
        if isinstance(value, Exception):
            raise value
        return value


def test_mark_deleted_remote_pages_marks_archived_without_removing_file(tmp_path):
    note = tmp_path / "page.md"
    note.write_text(
        "---\n"
        "title: Example\n"
        "notion_id: abc-123\n"
        "sync_status: complete\n"
        "---\n\n"
        "# Example\n",
        encoding="utf-8",
    )
    client = FakeClient({"abc-123": {"id": "abc-123", "archived": True}})

    result = mark_deleted_remote_pages(client, tmp_path)

    text = note.read_text(encoding="utf-8")
    assert result == [note]
    assert note.exists()
    assert "sync_status: deleted\n" in text
    assert "delete_reason: notion_archived\n" in text


def test_mark_deleted_remote_pages_marks_object_not_found_without_removing_file(tmp_path):
    note = tmp_path / "missing.md"
    note.write_text(
        "---\n"
        "title: Missing\n"
        "notion_id: missing-123\n"
        "sync_status: complete\n"
        "---\n\n"
        "# Missing\n",
        encoding="utf-8",
    )
    client = FakeClient({"missing-123": RuntimeError("object_not_found")})

    result = mark_deleted_remote_pages(client, tmp_path)

    text = note.read_text(encoding="utf-8")
    assert result == [note]
    assert note.exists()
    assert "sync_status: deleted\n" in text
    assert "delete_reason: notion_not_found\n" in text
