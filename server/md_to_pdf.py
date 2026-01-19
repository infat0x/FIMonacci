"""
Markdown -> PDF converter (simple, dependency-light).

Requirement: generate a .md file first, then convert it to PDF via Python.
This module provides the conversion step.
"""

from __future__ import annotations

import re
from typing import List


def _md_inline_to_rl(markdown_text: str) -> str:
    """
    Convert a small subset of Markdown inline syntax to ReportLab paragraph markup.
    """
    s = markdown_text

    # Escape XML-ish characters first to avoid breaking Paragraph markup
    s = (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    # Code spans: `code`
    # NOTE: do NOT escape quotes in the tag attributes; ReportLab's parser expects normal markup.
    s = re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', s)

    # Bold: **text**
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)

    # Italic: *text*
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)

    return s


def convert_markdown_file_to_pdf(md_path: str, pdf_path: str) -> None:
    """
    Convert a Markdown file to a PDF file.

    Uses ReportLab to produce a clean, readable document with headings and bullets.
    """
    # Import here so the server can still run without reportlab until PDF is requested.
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        ListFlowable,
        ListItem,
    )
    from reportlab.platypus.flowables import HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    with open(md_path, "r", encoding="utf-8") as f:
        raw_lines = f.read().splitlines()

    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "FIMNormal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#111827"),
    )
    h1 = ParagraphStyle(
        "FIMH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        spaceAfter=8,
        textColor=colors.HexColor("#0B1220"),
    )
    h2 = ParagraphStyle(
        "FIMH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#0B1220"),
    )
    h3 = ParagraphStyle(
        "FIMH3",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor("#0B1220"),
    )
    meta = ParagraphStyle(
        "FIMMeta",
        parent=normal,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#374151"),
    )

    story: List[object] = []

    def flush_bullets(buffer: List[str]) -> None:
        if not buffer:
            return
        items = []
        for b in buffer:
            txt = _md_inline_to_rl(b.strip())
            items.append(ListItem(Paragraph(txt, normal), leftIndent=0))
        story.append(
            ListFlowable(
                items,
                bulletType="bullet",
                leftIndent=14,
                bulletFontName="Helvetica-Bold",
                bulletFontSize=10,
                bulletColor=colors.HexColor("#0EA5A4"),
            )
        )
        story.append(Spacer(1, 4))

    bullet_buf: List[str] = []

    for line in raw_lines:
        l = line.rstrip()

        # Horizontal rule
        if re.fullmatch(r"\s*-{3,}\s*", l):
            flush_bullets(bullet_buf)
            bullet_buf = []
            story.append(Spacer(1, 6))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB")))
            story.append(Spacer(1, 10))
            continue

        # Headings
        if l.startswith("# "):
            flush_bullets(bullet_buf)
            bullet_buf = []
            story.append(Paragraph(_md_inline_to_rl(l[2:].strip()), h1))
            story.append(Spacer(1, 6))
            continue
        if l.startswith("## "):
            flush_bullets(bullet_buf)
            bullet_buf = []
            story.append(Paragraph(_md_inline_to_rl(l[3:].strip()), h2))
            continue
        if l.startswith("### "):
            flush_bullets(bullet_buf)
            bullet_buf = []
            story.append(Paragraph(_md_inline_to_rl(l[4:].strip()), h3))
            continue

        # Bullets
        if re.match(r"^\s*-\s+", l):
            bullet_buf.append(re.sub(r"^\s*-\s+", "", l))
            continue

        # Blank line -> paragraph break
        if not l.strip():
            flush_bullets(bullet_buf)
            bullet_buf = []
            story.append(Spacer(1, 6))
            continue

        # Metadata-like bold prefix lines (e.g. "**Incident ID:** ...")
        if l.strip().startswith("**") and l.strip().endswith("**") is False:
            flush_bullets(bullet_buf)
            bullet_buf = []
            story.append(Paragraph(_md_inline_to_rl(l.strip()), meta))
            continue

        # Normal paragraph
        flush_bullets(bullet_buf)
        bullet_buf = []
        story.append(Paragraph(_md_inline_to_rl(l.strip()), normal))

    flush_bullets(bullet_buf)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Security Incident Report",
        author="FIMonacci",
    )
    doc.build(story)

