from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

import pdfplumber
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, ContentStream, NameObject, create_string_object
from reportlab.lib.colors import HexColor, black
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


LINK_COLOR = HexColor("#1155CC")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replace the contact line in the authorized resume PDF."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--old-email", required=True)
    parser.add_argument("--new-email", required=True)
    return parser.parse_args()


def contact_line_details(input_path: Path, old_email: str) -> tuple[set[int], float, float]:
    with pdfplumber.open(input_path) as document:
        if len(document.pages) != 1:
            raise ValueError("Expected the authorized resume to contain exactly one page")

        page = document.pages[0]
        matches = [word for word in page.extract_words() if word["text"] == old_email]
        if len(matches) != 1:
            raise ValueError(f"Expected one exact occurrence of {old_email!r}, found {len(matches)}")

        email_word = matches[0]
        line_chars = [
            char
            for char in page.chars
            if char["top"] < email_word["bottom"] + 1
            and char["bottom"] > email_word["top"] - 1
        ]
        mcids = {int(char["mcid"]) for char in line_chars if char.get("mcid") is not None}
        if not mcids:
            raise ValueError("The contact line does not expose tagged-content identifiers")

        return mcids, float(email_word["top"]), float(email_word["bottom"])


def remove_tagged_contact_line(page, reader: PdfReader, target_mcids: set[int]) -> None:
    content = ContentStream(page["/Contents"], reader)
    filtered_operations = []
    marked_content_stack: list[bool] = []

    for operands, operator in content.operations:
        if operator in {b"BMC", b"BDC"}:
            mcid = None
            if operator == b"BDC" and len(operands) > 1 and hasattr(operands[1], "get"):
                raw_mcid = operands[1].get("/MCID")
                if raw_mcid is not None:
                    mcid = int(raw_mcid)
            marked_content_stack.append(
                bool(marked_content_stack and marked_content_stack[-1])
                or mcid in target_mcids
            )
            filtered_operations.append((operands, operator))
            continue

        if operator == b"EMC":
            if not marked_content_stack:
                raise ValueError("Unbalanced marked-content sequence in the source resume")
            marked_content_stack.pop()
            filtered_operations.append((operands, operator))
            continue

        in_contact_line = bool(marked_content_stack and marked_content_stack[-1])
        if in_contact_line and operator == b"Tj":
            operands = [create_string_object("")]
        elif in_contact_line and operator == b"TJ":
            operands = [ArrayObject()]
        filtered_operations.append((operands, operator))

    if marked_content_stack:
        raise ValueError("Unbalanced marked-content sequence while removing the contact line")

    content.operations = filtered_operations
    page[NameObject("/Contents")] = content


def remove_contact_links(page, contact_top: float, contact_bottom: float) -> None:
    annotations = page.get("/Annots")
    if not annotations:
        return

    page_height = float(page.mediabox.height)
    band_bottom = page_height - contact_bottom - 2
    band_top = page_height - contact_top + 2
    retained = ArrayObject()

    for annotation_ref in annotations:
        annotation = annotation_ref.get_object()
        rect = annotation.get("/Rect")
        overlaps_contact_band = bool(
            rect
            and float(rect[1]) < band_top
            and float(rect[3]) > band_bottom
        )
        if not overlaps_contact_band:
            retained.append(annotation_ref)

    page[NameObject("/Annots")] = retained


def build_contact_overlay(page_width: float, page_height: float, baseline: float, email: str) -> PdfReader:
    segments = [
        ("Berkeley, CA | +1 (347) 449-4034 | ", black, None),
        (email, LINK_COLOR, f"mailto:{email}"),
        (" | ", black, None),
        (
            "LinkedIn",
            LINK_COLOR,
            "http://www.linkedin.com/in/luiz-felipe-barbosa-5989a9294",
        ),
        (" | ", black, None),
        ("GitHub", LINK_COLOR, "https://github.com/LuizFelipeBarbosa"),
        (" | ", black, None),
        ("lfpmb.com", LINK_COLOR, "http://lfpmb.com"),
    ]
    font_name = "Helvetica"
    font_size = 8.5
    total_width = sum(stringWidth(text, font_name, font_size) for text, _, _ in segments)
    if total_width > page_width - 72:
        raise ValueError("The updated contact line does not fit within the resume margins")

    stream = BytesIO()
    overlay = canvas.Canvas(stream, pagesize=(page_width, page_height))
    overlay.setFont(font_name, font_size)
    x = (page_width - total_width) / 2

    for text, color, url in segments:
        width = stringWidth(text, font_name, font_size)
        overlay.setFillColor(color)
        overlay.drawString(x, baseline, text)
        if url:
            overlay.linkURL(
                url,
                (x, baseline - 1.5, x + width, baseline + font_size + 1),
                relative=0,
            )
        x += width

    overlay.save()
    stream.seek(0)
    return PdfReader(stream)


def update_resume(input_path: Path, output_path: Path, old_email: str, new_email: str) -> None:
    target_mcids, contact_top, contact_bottom = contact_line_details(input_path, old_email)
    reader = PdfReader(input_path)
    page = reader.pages[0]

    remove_tagged_contact_line(page, reader, target_mcids)
    remove_contact_links(page, contact_top, contact_bottom)

    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)
    baseline = page_height - contact_bottom + 1.5
    overlay_page = build_contact_overlay(page_width, page_height, baseline, new_email).pages[0]
    page.merge_page(overlay_page)

    writer = PdfWriter()
    writer.add_page(page)
    if reader.metadata:
        writer.add_metadata(dict(reader.metadata))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output_file:
        writer.write(output_file)


def main() -> None:
    args = parse_args()
    update_resume(args.input, args.output, args.old_email, args.new_email)


if __name__ == "__main__":
    main()
