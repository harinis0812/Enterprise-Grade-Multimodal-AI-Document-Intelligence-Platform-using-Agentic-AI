import os
import tempfile
from pathlib import Path

_ocr = None


def get_ocr():
    global _ocr
    if _ocr is None:
        paddlex_cache = os.environ.get(
            "PADDLE_PDX_CACHE_HOME",
            str(Path(__file__).resolve().parent.parent.parent / ".paddlex")
        )
        os.environ.setdefault("PADDLE_PDX_CACHE_HOME", paddlex_cache)
        os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))
        from paddleocr import PaddleOCR

        _ocr = PaddleOCR(
            lang="en",
            enable_mkldnn=False
        )
    return _ocr


def extract_text_from_image(file_path):
    ocr = get_ocr()
    result = ocr.predict(file_path)

    extracted_text = []

    for res in result:

        if isinstance(res, dict):

            rec_texts = res.get("rec_texts", [])

            extracted_text.extend(rec_texts)

    return " ".join(extracted_text)
