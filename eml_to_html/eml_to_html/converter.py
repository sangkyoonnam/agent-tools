"""EML to HTML conversion logic."""

import email
import email.policy
from email.message import EmailMessage
from pathlib import Path


def parse_eml(path: Path) -> EmailMessage:
    """Parse an EML file and return an EmailMessage object."""
    with open(path, "rb") as f:
        return email.message_from_binary_file(f, policy=email.policy.default)


def extract_html_body(msg: EmailMessage) -> str | None:
    """Extract HTML body from an email message."""
    html = msg.get_body(preferencelist=("html",))
    if html:
        return html.get_content()
    return None


def extract_text_body(msg: EmailMessage) -> str | None:
    """Extract plain text body from an email message."""
    text = msg.get_body(preferencelist=("plain",))
    if text:
        return text.get_content()
    return None


def text_to_html(text: str) -> str:
    """Convert plain text to basic HTML."""
    import html as html_module

    escaped = html_module.escape(text)
    paragraphs = escaped.split("\n\n")
    body = "\n".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs)
    return body


def build_html(msg: EmailMessage, *, headers: bool = False) -> str:
    """Extract the HTML body content from an email message."""
    html_body = extract_html_body(msg)
    if html_body is None:
        text_body = extract_text_body(msg)
        if text_body:
            html_body = text_to_html(text_body)
        else:
            html_body = "<p>(empty)</p>"

    if not headers:
        return html_body

    subject = msg.get("Subject", "(no subject)")
    header_block = (
        '<div style="border-bottom:1px solid #ccc; padding-bottom:12px; margin-bottom:20px;'
        ' font-family:sans-serif; font-size:14px; color:#555;">\n'
        f'  <div><strong>Subject:</strong> {subject}</div>\n'
        f'  <div><strong>From:</strong> {msg.get("From", "")}</div>\n'
        f'  <div><strong>To:</strong> {msg.get("To", "")}</div>\n'
        f'  <div><strong>Date:</strong> {msg.get("Date", "")}</div>\n'
        '</div>'
    )
    return (
        f'<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n'
        f'</head>\n<body>\n'
        f'{header_block}\n{html_body}\n</body>\n</html>'
    )


def convert(src: Path, dst: Path, *, headers: bool = False) -> None:
    """Convert a single EML file to HTML."""
    msg = parse_eml(src)
    html = build_html(msg, headers=headers)
    dst.write_text(html, encoding="utf-8")
