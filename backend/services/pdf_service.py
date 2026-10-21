import fitz
import os
import uuid

from backend.services.ocr_service import extract_text_from_image


def extract_text_from_pdf(pdf_path):

    document = fitz.open(pdf_path)

    extracted_text = []

    total_pages = len(document)

    for page in document:

        # Try normal text extraction first
        page_text = page.get_text().strip()

        if page_text:
            if total_pages > 1:
                extracted_text.append(f"--- Page {page.number + 1} ---\n{page_text}")
            else:
                extracted_text.append(page_text)

        else:
            # Scanned PDF: convert page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

            image_path = (
                f"backend/uploads/temp_{uuid.uuid4().hex}_page_{page.number}.png"
            )

            try:
                pix.save(image_path)

                # OCR the converted image
                ocr_text = extract_text_from_image(image_path)

                if total_pages > 1:
                    extracted_text.append(f"--- Page {page.number + 1} ---\n{ocr_text}")
                else:
                    extracted_text.append(ocr_text)

            finally:
                # Always remove temporary image safely
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as cleanup_error:
                        print(
                            f"[PDF Service] Clean up warning: "
                            f"Could not remove {image_path}: {cleanup_error}"
                        )

    document.close()

    return "\n".join(extracted_text)