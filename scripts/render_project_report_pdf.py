from __future__ import annotations

import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "project_report.md"
TARGET = ROOT / "Project_Report.pdf"

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT_MARGIN = 54
TOP_MARGIN = 60
BOTTOM_MARGIN = 50
LINE_GAP = 14
BODY_SIZE = 10
HEADING_SIZE = 13
TITLE_SIZE = 18
MAX_WIDTH_CHARS = 92


def normalize_lines(markdown: str) -> list[tuple[str, int]]:
    lines: list[tuple[str, int]] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append(("", BODY_SIZE))
            continue

        if line.startswith("# "):
            lines.append((line[2:].strip(), TITLE_SIZE))
            lines.append(("", BODY_SIZE))
            continue

        if line.startswith("## "):
            lines.append((line[3:].strip(), HEADING_SIZE))
            continue

        if line.startswith("- "):
            wrapped = textwrap.wrap(line[2:].strip(), width=MAX_WIDTH_CHARS - 4) or [""]
            for index, chunk in enumerate(wrapped):
                prefix = "- " if index == 0 else "  "
                lines.append((f"{prefix}{chunk}", BODY_SIZE))
            continue

        if line[:2].isdigit() and line[1:3] == ". ":
            wrapped = textwrap.wrap(line, width=MAX_WIDTH_CHARS) or [line]
            for chunk in wrapped:
                lines.append((chunk, BODY_SIZE))
            continue

        wrapped = textwrap.wrap(line, width=MAX_WIDTH_CHARS) or [line]
        for chunk in wrapped:
            lines.append((chunk, BODY_SIZE))

    return lines


def paginate(lines: list[tuple[str, int]]) -> list[list[tuple[str, int]]]:
    pages: list[list[tuple[str, int]]] = []
    current_page: list[tuple[str, int]] = []
    y = PAGE_HEIGHT - TOP_MARGIN

    for text, size in lines:
        gap = LINE_GAP + max(size - BODY_SIZE, 0)
        if y - gap < BOTTOM_MARGIN:
            pages.append(current_page)
            current_page = []
            y = PAGE_HEIGHT - TOP_MARGIN

        current_page.append((text, size))
        y -= gap

    if current_page:
        pages.append(current_page)

    return pages


def escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_content_stream(page_lines: list[tuple[str, int]]) -> bytes:
    commands: list[str] = ["BT", f"1 0 0 1 {LEFT_MARGIN} {PAGE_HEIGHT - TOP_MARGIN} Tm"]
    current_size = BODY_SIZE
    commands.append(f"/F1 {current_size} Tf")

    first = True
    for text, size in page_lines:
        if not first:
            gap = LINE_GAP + max(size - BODY_SIZE, 0)
            commands.append(f"0 -{gap} Td")
        first = False

        if size != current_size:
            current_size = size
            commands.append(f"/F1 {current_size} Tf")

        safe_text = escape_pdf_text(text or " ")
        commands.append(f"({safe_text}) Tj")

    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def generate_pdf(markdown: str) -> bytes:
    pages = paginate(normalize_lines(markdown))

    objects: list[bytes] = []

    def add_object(payload: str | bytes) -> int:
        data = payload.encode("latin-1") if isinstance(payload, str) else payload
        objects.append(data)
        return len(objects)

    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    content_ids: list[int] = []

    for page_lines in pages:
        stream = build_content_stream(page_lines)
        content_id = add_object(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
        content_ids.append(content_id)
        page_ids.append(0)

    pages_id = len(objects) + len(pages) + 1
    catalog_id = pages_id + 1

    for index, content_id in enumerate(content_ids):
        page_payload = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids[index] = add_object(page_payload)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
    add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    buffer = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(buffer))
        buffer.extend(f"{index} 0 obj\n".encode("ascii"))
        buffer.extend(obj)
        buffer.extend(b"\nendobj\n")

    xref_offset = len(buffer)
    buffer.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buffer.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    )
    buffer.extend(trailer.encode("ascii"))
    return bytes(buffer)


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    TARGET.write_bytes(generate_pdf(markdown))
    print(TARGET)


if __name__ == "__main__":
    main()
