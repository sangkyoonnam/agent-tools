"""Notion blocks to Markdown converter."""

from __future__ import annotations

import re
from pathlib import Path

from .assets import get_downloader


def _sanitize(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip(". ")
    return name or "Untitled"


def rich_text_to_md(rich_texts: list[dict]) -> str:
    parts = []
    for rt in rich_texts:
        text = rt.get("plain_text", "")
        annotations = rt.get("annotations", {})
        href = rt.get("href")

        if annotations.get("code"):
            text = f"`{text}`"
        if annotations.get("bold"):
            text = f"**{text}**"
        if annotations.get("italic"):
            text = f"*{text}*"
        if annotations.get("strikethrough"):
            text = f"~~{text}~~"
        if annotations.get("underline"):
            text = f"<u>{text}</u>"
        if href:
            text = f"[{text}]({href})"

        parts.append(text)
    return "".join(parts)


def block_to_md(
    block: dict,
    indent: int = 0,
    children_map: dict | None = None,
    page_dir: Path | None = None,
) -> str:
    block_type = block.get("type", "")
    data = block.get(block_type, {})
    prefix = "  " * indent
    children_map = children_map or {}

    def get_text() -> str:
        return rich_text_to_md(data.get("rich_text", []))

    def get_children(block_id: str) -> str:
        children = children_map.get(block_id, [])
        if not children:
            return ""
        lines = []
        for child in children:
            lines.append(block_to_md(child, indent + 1, children_map, page_dir))
        return "\n" + "\n".join(lines)

    def resolve_file_url(notion_file: dict, bid: str) -> str:
        """Queue Notion-hosted files for download. Keep external URLs as-is."""
        file_info = notion_file.get("file", {})
        ext_info = notion_file.get("external", {})

        if file_info:
            url = file_info.get("url", "")
            if page_dir and url:
                return get_downloader().enqueue(url, page_dir, bid)
            return url
        elif ext_info:
            return ext_info.get("url", "")
        return notion_file.get("url", "")

    block_id = block.get("id", "")

    match block_type:
        case "paragraph":
            text = get_text()
            result = f"{prefix}{text}"
            result += get_children(block_id)
            return result

        case "heading_1":
            return f"{prefix}# {get_text()}"
        case "heading_2":
            return f"{prefix}## {get_text()}"
        case "heading_3":
            return f"{prefix}### {get_text()}"

        case "bulleted_list_item":
            result = f"{prefix}- {get_text()}"
            result += get_children(block_id)
            return result

        case "numbered_list_item":
            result = f"{prefix}1. {get_text()}"
            result += get_children(block_id)
            return result

        case "to_do":
            checked = "x" if data.get("checked") else " "
            result = f"{prefix}- [{checked}] {get_text()}"
            result += get_children(block_id)
            return result

        case "toggle":
            result = f"{prefix}- {get_text()}"
            result += get_children(block_id)
            return result

        case "code":
            lang = data.get("language", "")
            text = get_text()
            return f"{prefix}```{lang}\n{text}\n{prefix}```"

        case "quote":
            text = get_text()
            lines = text.split("\n")
            result = "\n".join(f"{prefix}> {line}" for line in lines)
            result += get_children(block_id)
            return result

        case "callout":
            icon = data.get("icon", {}).get("emoji", "")
            text = get_text()
            result = f"{prefix}> {icon} {text}"
            result += get_children(block_id)
            return result

        case "divider":
            return f"{prefix}---"

        case "image":
            url = resolve_file_url(data, block_id)
            caption = rich_text_to_md(data.get("caption", []))
            if caption:
                return f"{prefix}![{caption}]({url})"
            return f"{prefix}![]({url})"

        case "bookmark":
            url = data.get("url", "")
            caption = rich_text_to_md(data.get("caption", []))
            return f"{prefix}[{caption or url}]({url})"

        case "link_preview":
            url = data.get("url", "")
            return f"{prefix}[{url}]({url})"

        case "embed":
            url = data.get("url", "")
            return f"{prefix}[Embed: {url}]({url})"

        case "file":
            url = resolve_file_url(data, block_id)
            caption = rich_text_to_md(data.get("caption", []))
            return f"{prefix}[{caption or 'File'}]({url})"

        case "pdf":
            url = resolve_file_url(data, block_id)
            return f"{prefix}[PDF]({url})"

        case "table":
            children = children_map.get(block_id, [])
            return _table_to_md(children, prefix)

        case "table_row":
            return ""  # handled by table

        case "column_list":
            parts = []
            for child in children_map.get(block_id, []):
                parts.append(block_to_md(child, indent, children_map, page_dir))
            return "\n\n".join(parts)

        case "column":
            parts = []
            for child in children_map.get(block_id, []):
                parts.append(block_to_md(child, indent, children_map, page_dir))
            return "\n".join(parts)

        case "child_page":
            title = data.get("title", "Untitled")
            return f"{prefix}[[{_sanitize(title)} [{block_id}]]]"

        case "child_database":
            title = data.get("title", "Untitled Database")
            return f"{prefix}[[{_sanitize(title)} [{block_id}]]]"

        case "synced_block":
            parts = []
            for child in children_map.get(block_id, []):
                parts.append(block_to_md(child, indent, children_map, page_dir))
            return "\n".join(parts)

        case "equation":
            expr = data.get("expression", "")
            return f"{prefix}$$\n{expr}\n{prefix}$$"

        case "video":
            url = resolve_file_url(data, block_id)
            return f"{prefix}[Video]({url})"

        case "audio":
            url = resolve_file_url(data, block_id)
            return f"{prefix}[Audio]({url})"

        case _:
            text = get_text()
            if text:
                return f"{prefix}{text}"
            return f"{prefix}<!-- unsupported block: {block_type} -->"


def _table_to_md(rows: list[dict], prefix: str) -> str:
    if not rows:
        return ""

    md_rows = []
    for row in rows:
        cells = row.get("table_row", {}).get("cells", [])
        cell_texts = [rich_text_to_md(cell) for cell in cells]
        md_rows.append(f"{prefix}| " + " | ".join(cell_texts) + " |")

    if len(md_rows) >= 1:
        num_cols = len(rows[0].get("table_row", {}).get("cells", []))
        separator = f"{prefix}| " + " | ".join(["---"] * num_cols) + " |"
        md_rows.insert(1, separator)

    return "\n".join(md_rows)


def database_to_md(title: str, properties_schema: dict, items: list[dict]) -> str:
    """Convert a Notion database to a markdown table."""
    lines = []
    lines.append(f"# {title}")
    lines.append("")

    prop_names = []
    title_prop = None
    for name, schema in properties_schema.items():
        if schema.get("type") == "title":
            title_prop = name
        else:
            prop_names.append(name)

    if title_prop:
        prop_names.insert(0, title_prop)

    if not items:
        lines.append("*Empty database*")
        return "\n".join(lines)

    lines.append("| " + " | ".join(prop_names) + " |")
    lines.append("| " + " | ".join(["---"] * len(prop_names)) + " |")

    for item in items:
        props = item.get("properties", {})
        cells = []
        for name in prop_names:
            cells.append(_property_to_text(props.get(name, {})))
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def _property_to_text(prop: dict) -> str:
    prop_type = prop.get("type", "")

    match prop_type:
        case "title":
            return rich_text_to_md(prop.get("title", []))
        case "rich_text":
            return rich_text_to_md(prop.get("rich_text", []))
        case "number":
            val = prop.get("number")
            return str(val) if val is not None else ""
        case "select":
            sel = prop.get("select")
            return sel.get("name", "") if sel else ""
        case "multi_select":
            return ", ".join(s.get("name", "") for s in prop.get("multi_select", []))
        case "date":
            date = prop.get("date")
            if not date:
                return ""
            start = date.get("start", "")
            end = date.get("end", "")
            return f"{start} → {end}" if end else start
        case "checkbox":
            return "Yes" if prop.get("checkbox") else "No"
        case "url":
            return prop.get("url", "") or ""
        case "email":
            return prop.get("email", "") or ""
        case "phone_number":
            return prop.get("phone_number", "") or ""
        case "formula":
            formula = prop.get("formula", {})
            f_type = formula.get("type", "")
            return str(formula.get(f_type, ""))
        case "relation":
            return ", ".join(r.get("id", "") for r in prop.get("relation", []))
        case "rollup":
            rollup = prop.get("rollup", {})
            r_type = rollup.get("type", "")
            if r_type == "array":
                return ", ".join(_property_to_text(item) for item in rollup.get("array", []))
            return str(rollup.get(r_type, ""))
        case "people":
            return ", ".join(p.get("name", "") for p in prop.get("people", []))
        case "files":
            files = prop.get("files", [])
            return ", ".join(f.get("name", "") for f in files)
        case "created_time":
            return prop.get("created_time", "")
        case "last_edited_time":
            return prop.get("last_edited_time", "")
        case "created_by":
            return prop.get("created_by", {}).get("name", "")
        case "last_edited_by":
            return prop.get("last_edited_by", {}).get("name", "")
        case "status":
            status = prop.get("status")
            return status.get("name", "") if status else ""
        case "unique_id":
            uid = prop.get("unique_id", {})
            prefix = uid.get("prefix", "")
            number = uid.get("number", "")
            return f"{prefix}-{number}" if prefix else str(number)
        case _:
            return ""
