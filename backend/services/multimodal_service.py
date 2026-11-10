import io
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from backend.services.ocr_service import extract_text_from_image


@dataclass
class ExtractedTable:
    page_number: int
    table_index: int
    headers: List[str]
    rows: List[List[str]]
    markdown: str
    row_count: int
    col_count: int
    bbox: Optional[List[float]] = None
    has_continuity_marker: bool = False
    limitations: Optional[str] = None


@dataclass
class VisualElement:
    page_number: int
    element_index: int
    element_type: str  # "Chart/Diagram", "Vector Graphic", "Embedded Image"
    captions: List[str]
    associated_labels: List[str]
    drawing_count: int
    image_count: int
    bbox: Optional[List[float]] = None
    analysis_status: str = "detected"  # "detected" | "analyzed" | "uninterpretable"
    chart_type: Optional[str] = None
    legend: List[str] = field(default_factory=list)
    extracted_observations: List[str] = field(default_factory=list)


@dataclass
class MultimodalDocumentResult:
    full_text: str
    total_pages: int
    tables: List[ExtractedTable] = field(default_factory=list)
    visual_elements: List[VisualElement] = field(default_factory=list)
    ocr_pages: List[int] = field(default_factory=list)
    page_evidence_map: Dict[int, List[str]] = field(default_factory=dict)
    summary_metadata: Dict[str, Any] = field(default_factory=dict)


CAPTION_REGEX = re.compile(
    r"(?i)\b(figure|fig\.|chart|graph|diagram|plot|illustration|exhibit|table)\s*(\d+[A-Za-z0-9_.-]*|[A-Z])?[:.]?\s*([^\n\r]+)",
    re.MULTILINE
)

LABEL_REGEX = re.compile(
    r"(?i)\b(q[1-4]|20\d\d|fy\d\d|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|revenue|expenses|profit|loss|growth|total|target|actual|\$|%)\b"
)


def format_table_to_markdown(headers: List[str], rows: List[List[str]]) -> str:
    """Formats headers and rows into clean Markdown table syntax."""
    if not headers and not rows:
        return ""
    
    clean_headers = [str(h or "").replace("\n", " ").strip() for h in headers]
    if not clean_headers and rows:
        col_count = max(len(r) for r in rows)
        clean_headers = [f"Col {i+1}" for i in range(col_count)]

    col_count = len(clean_headers)
    
    clean_rows = []
    for r in rows:
        row_cells = [str(c or "").replace("\n", " ").strip() for c in r]
        # Pad or trim to match header column count
        if len(row_cells) < col_count:
            row_cells.extend([""] * (col_count - len(row_cells)))
        elif len(row_cells) > col_count:
            row_cells = row_cells[:col_count]
        clean_rows.append(row_cells)

    lines = [
        "| " + " | ".join(clean_headers) + " |",
        "| " + " | ".join(["---"] * col_count) + " |"
    ]
    for r in clean_rows:
        lines.append("| " + " | ".join(r) + " |")

    return "\n".join(lines)


def detect_tables_from_page(page: fitz.Page, page_num: int) -> List[ExtractedTable]:
    """
    Extracts structured tables from a PyMuPDF page using find_tables().
    Preserves row/column structure, cell values, and headers.
    """
    tables: List[ExtractedTable] = []
    try:
        tabs = page.find_tables()
        for idx, tab in enumerate(tabs, start=1):
            raw_data = tab.extract()
            if not raw_data or len(raw_data) == 0:
                continue

            headers = [str(c or "").strip() for c in raw_data[0]]
            rows = []
            for r in raw_data[1:]:
                clean_r = [str(c or "").strip() for c in r]
                # Filter out entirely empty rows
                if any(clean_r):
                    rows.append(clean_r)

            # Generate markdown table
            try:
                md_tab = tab.to_markdown()
                if not md_tab or not md_tab.strip():
                    md_tab = format_table_to_markdown(headers, rows)
            except Exception:
                md_tab = format_table_to_markdown(headers, rows)

            # Check for continuity indicators in headers
            hdr_str = " ".join(headers).lower()
            has_cont = bool(re.search(r"\b(?:cont(?:inued|\.)?|part\s*\d+)\b", hdr_str))
            limitation_note = (
                "Table indicates multi-page continuation; cross-page row alignment should be verified."
                if has_cont
                else "Page-isolated table; multi-page row continuity should be verified."
            )

            tables.append(
                ExtractedTable(
                    page_number=page_num,
                    table_index=idx,
                    headers=headers,
                    rows=rows,
                    markdown=md_tab,
                    row_count=len(rows),
                    col_count=len(headers),
                    bbox=list(tab.bbox) if hasattr(tab, "bbox") else None,
                    has_continuity_marker=has_cont,
                    limitations=limitation_note
                )
            )
    except Exception as exc:
        print(f"[MultimodalService] Table extraction warning on page {page_num}: {exc}")

    return tables


def detect_visual_elements_from_page(
    page: fitz.Page,
    page_num: int,
    page_text: str
) -> List[VisualElement]:
    """
    Detects charts, graphs, and diagrams using vector drawing heuristics,
    image heuristics, and caption/label regex extractions.
    """
    visuals: List[VisualElement] = []
    try:
        drawings = page.get_drawings()
        images = page.get_images()

        drawing_count = len(drawings)
        image_count = len(images)

        # Look for explicit captions in the page text
        captions: List[str] = []
        for match in CAPTION_REGEX.finditer(page_text):
            full_cap = match.group(0).strip()
            if len(full_cap) >= 6:
                captions.append(full_cap[:160])

        # Extract surrounding labels
        labels: List[str] = []
        for line in page_text.splitlines():
            line_str = line.strip()
            if LABEL_REGEX.search(line_str) and len(line_str) <= 80:
                labels.append(line_str)

        # Heuristic classification
        is_chart_or_diagram = drawing_count >= 8
        is_embedded_image = image_count >= 1

        if is_chart_or_diagram or is_embedded_image or captions:
            element_type = "Chart/Diagram" if is_chart_or_diagram else "Embedded Image"

            # Determine specific chart type
            all_text_context = " ".join(captions + labels).lower()
            if "bar" in all_text_context:
                chart_type = "Bar Chart"
            elif "line" in all_text_context or "trend" in all_text_context:
                chart_type = "Line Graph"
            elif "pie" in all_text_context or "donut" in all_text_context:
                chart_type = "Pie Chart"
            elif any(w in all_text_context for w in ["flow", "workflow", "process", "pipeline", "architecture"]):
                chart_type = "Flowchart/Diagram"
            elif "scatter" in all_text_context:
                chart_type = "Scatter Plot"
            elif is_chart_or_diagram:
                chart_type = "Vector Graphic / Diagram"
            elif is_embedded_image:
                chart_type = "Document Image"
            else:
                chart_type = None

            # Extract legend candidates
            legends: List[str] = []
            for line in page_text.splitlines():
                l_s = line.strip()
                if re.match(r"(?i)^(legend|series|key)\s*[:\-]", l_s):
                    legends.append(l_s[:100])

            # Extract structured observations
            observations: List[str] = []
            if chart_type:
                observations.append(f"Classified visual as: {chart_type}")
            if captions:
                observations.append(f"Caption: {captions[0]}")
            if labels:
                observations.append(f"Observed data labels: {', '.join(labels[:4])}")
            if legends:
                observations.append(f"Legend: {', '.join(legends[:2])}")

            # Determine analysis status: only mark analyzed if semantic cues or specific chart patterns exist
            if captions or labels or (chart_type and chart_type not in ["Document Image", "Vector Graphic / Diagram"]):
                analysis_status = "analyzed"
            else:
                analysis_status = "detected"

            visuals.append(
                VisualElement(
                    page_number=page_num,
                    element_index=1,
                    element_type=element_type,
                    captions=captions[:4],
                    associated_labels=labels[:6],
                    drawing_count=drawing_count,
                    image_count=image_count,
                    analysis_status=analysis_status,
                    chart_type=chart_type,
                    legend=legends[:4],
                    extracted_observations=observations
                )
            )
    except Exception as exc:
        print(f"[MultimodalService] Visual detection warning on page {page_num}: {exc}")

    return visuals


def extract_multimodal_pdf(pdf_source) -> MultimodalDocumentResult:
    """
    Processes a PDF file path or bytes, extracting text, tables, visual diagrams,
    and performing OCR on scanned pages where appropriate.
    """
    if isinstance(pdf_source, (bytes, bytearray)):
        doc_ctx = fitz.open(stream=pdf_source, filetype="pdf")
    else:
        doc_ctx = fitz.open(str(pdf_source))

    all_page_texts: List[str] = []
    all_tables: List[ExtractedTable] = []
    all_visuals: List[VisualElement] = []
    ocr_pages: List[int] = []
    evidence_map: Dict[int, List[str]] = {}

    with doc_ctx as document:
        total_pages = len(document)

        for page in document:
            page_num = page.number + 1
            evidence_types: List[str] = []

            # 1. Native text extraction
            raw_text = page.get_text("text").strip()

            # 2. Extract tables
            tables = detect_tables_from_page(page, page_num)
            if tables:
                all_tables.extend(tables)
                evidence_types.append("table")

            # 3. Detect visual content (charts, graphs, diagrams)
            visuals = detect_visual_elements_from_page(page, page_num, raw_text)
            if visuals:
                all_visuals.extend(visuals)
                evidence_types.append("chart")

            # 4. Scanned page & Mixed-content detection with OCR
            # Calculate image coverage area on page to detect embedded scanned content
            page_rect = page.rect
            page_area = max(page_rect.width * page_rect.height, 1.0)
            page_images = page.get_images()
            total_img_area = 0.0
            for img_info in page_images:
                try:
                    rects = page.get_image_rects(img_info[0])
                    for r in rects:
                        total_img_area += r.width * r.height
                except Exception:
                    pass
            img_coverage = total_img_area / page_area

            page_text_content = ""
            if len(raw_text) < 35:
                # Scanned page or blank page: attempt OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                temp_img = Path(tempfile.gettempdir()) / f"temp_ocr_{uuid.uuid4().hex}_p{page_num}.png"
                try:
                    pix.save(str(temp_img))
                    ocr_text = extract_text_from_image(str(temp_img)).strip()
                    if ocr_text:
                        page_text_content = ocr_text
                        ocr_pages.append(page_num)
                        evidence_types.append("ocr")
                    else:
                        page_text_content = raw_text
                        if raw_text:
                            evidence_types.append("text")
                except Exception as ocr_err:
                    print(f"[MultimodalService] OCR error on page {page_num}: {ocr_err}")
                    page_text_content = raw_text
                    if raw_text:
                        evidence_types.append("text")
                finally:
                    if temp_img.exists():
                        try:
                            temp_img.unlink()
                        except Exception:
                            pass
            else:
                # Page has native text
                page_text_content = raw_text
                evidence_types.append("text")

                # Mixed-content inspection: If images cover > 15% of page area,
                # extract and OCR embedded image regions without duplicating native text
                if img_coverage > 0.15 and page_images:
                    ocr_snippets: List[str] = []
                    for img_info in page_images:
                        xref = img_info[0]
                        try:
                            rects = page.get_image_rects(xref)
                            sub_area = sum(r.width * r.height for r in rects)
                            if (sub_area / page_area) >= 0.05:
                                base_image = document.extract_image(xref)
                                img_bytes = base_image.get("image")
                                img_ext = base_image.get("ext", "png")
                                if img_bytes:
                                    temp_mixed = Path(tempfile.gettempdir()) / f"temp_mixed_{uuid.uuid4().hex}.{img_ext}"
                                    try:
                                        temp_mixed.write_bytes(img_bytes)
                                        extracted_img_text = extract_text_from_image(str(temp_mixed)).strip()
                                        if extracted_img_text and len(extracted_img_text) > 10:
                                            # Avoid duplication if native text already captured it
                                            if extracted_img_text.lower() not in raw_text.lower():
                                                ocr_snippets.append(extracted_img_text)
                                    finally:
                                        if temp_mixed.exists():
                                            try:
                                                temp_mixed.unlink()
                                            except Exception:
                                                pass
                        except Exception:
                            pass

                    if ocr_snippets:
                        page_text_content = (
                            raw_text
                            + f"\n\n[Scanned Region via OCR | Page {page_num}]\n"
                            + "\n".join(ocr_snippets)
                        )
                        ocr_pages.append(page_num)
                        evidence_types.append("ocr")

            if not evidence_types:
                evidence_types.append("text")

            evidence_map[page_num] = list(set(evidence_types))

            # Assemble unified page section with structured annotations
            page_blocks: List[str] = []
            if total_pages > 1:
                page_blocks.append(f"--- Page {page_num} ---")

            if page_text_content:
                page_blocks.append(page_text_content)

            # Append structured markdown tables into document text
            for t in tables:
                page_blocks.append(f"\n[Table {t.table_index} | Page {page_num}]\n{t.markdown}")

            # Append visual element summaries into document text
            for v in visuals:
                cap_str = "; ".join(v.captions) if v.captions else "No explicit caption"
                lbl_str = ", ".join(v.associated_labels) if v.associated_labels else "None"
                chart_type_str = f" | Type: {v.chart_type}" if v.chart_type else ""
                status_str = f" | Status: {v.analysis_status}"
                page_blocks.append(
                    f"\n[Visual Element: {v.element_type}{chart_type_str}{status_str} | Page {page_num}]\n"
                    f"Caption: {cap_str}\n"
                    f"Extracted Labels: {lbl_str}"
                )

            all_page_texts.append("\n".join(page_blocks))

    full_text = "\n\n".join(all_page_texts)

    summary_meta = {
        "total_pages": total_pages,
        "tables_detected": len(all_tables),
        "charts_detected": len(all_visuals),
        "ocr_pages": ocr_pages,
        "evidence_types_found": list({et for et_list in evidence_map.values() for et in et_list})
    }

    return MultimodalDocumentResult(
        full_text=full_text,
        total_pages=total_pages,
        tables=all_tables,
        visual_elements=all_visuals,
        ocr_pages=ocr_pages,
        page_evidence_map=evidence_map,
        summary_metadata=summary_meta
    )


def extract_multimodal_image(image_path: str) -> MultimodalDocumentResult:
    """
    Extracts text and metadata from image documents (.jpg, .jpeg, .png)
    via OCR, tagging evidence as OCR/image.
    """
    ocr_text = extract_text_from_image(image_path).strip()
    
    # Check for potential table structure in OCR text (lines with numbers/pipes)
    lines = [l.strip() for l in ocr_text.splitlines() if l.strip()]
    has_table_like_data = any("|" in l or "\t" in l for l in lines)
    
    evidence_types = ["ocr", "image"]
    if has_table_like_data:
        evidence_types.append("table")

    page_blocks = [
        "--- Page 1 ---",
        f"[Image Document via OCR]\n{ocr_text}"
    ]

    summary_meta = {
        "total_pages": 1,
        "tables_detected": 1 if has_table_like_data else 0,
        "charts_detected": 0,
        "ocr_pages": [1],
        "evidence_types_found": evidence_types
    }

    return MultimodalDocumentResult(
        full_text="\n".join(page_blocks),
        total_pages=1,
        tables=[],
        visual_elements=[],
        ocr_pages=[1],
        page_evidence_map={1: evidence_types},
        summary_metadata=summary_meta
    )
