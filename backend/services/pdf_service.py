import fitz
import os
import uuid

from backend.services.multimodal_service import extract_multimodal_pdf
from backend.services.ocr_service import extract_text_from_image


def extract_text_from_pdf(pdf_source):
    """
    Extracts text, tables, and visual diagram annotations from a PDF file path or raw PDF byte stream.
    Supports in-memory stream parsing to prevent Windows file-handle locking.
    Leverages the enhanced Phase 4 Multimodal Ingestion Pipeline.
    """
    try:
        result = extract_multimodal_pdf(pdf_source)
        return result.full_text
    except Exception as exc:
        # Fallback to direct PyMuPDF basic extraction if multimodal parser encounters an edge case
        print(f"[PDF Service] Multimodal extraction fallback triggered: {exc}")
        extracted_text = []
        if isinstance(pdf_source, (bytes, bytearray)):
            doc_ctx = fitz.open(stream=pdf_source, filetype="pdf")
        else:
            doc_ctx = fitz.open(str(pdf_source))

        with doc_ctx as document:
            total_pages = len(document)
            for page in document:
                page_text = page.get_text().strip()
                if page_text:
                    if total_pages > 1:
                        extracted_text.append(f"--- Page {page.number + 1} ---\n{page_text}")
                    else:
                        extracted_text.append(page_text)
                else:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    image_path = f"backend/uploads/temp_{uuid.uuid4().hex}_page_{page.number}.png"
                    try:
                        pix.save(image_path)
                        ocr_text = extract_text_from_image(image_path)
                        if total_pages > 1:
                            extracted_text.append(f"--- Page {page.number + 1} ---\n{ocr_text}")
                        else:
                            extracted_text.append(ocr_text)
                    finally:
                        if os.path.exists(image_path):
                            try:
                                os.remove(image_path)
                            except Exception:
                                pass
        return "\n".join(extracted_text)

