# -*- encoding: utf-8 -*-
from pathlib import Path
from typing import List, Union

try:
    import fitz  # PyMuPDF
    _HAS_PYMUPDF = True
except ImportError:
    _HAS_PYMUPDF = False

try:
    from rapidocr_pdf import PDFExtracter as RapidOCRExtracter
except ImportError:
    try:
        from rapidocr_pdf import RapidOCRPDF as RapidOCRExtracter
    except ImportError:
        RapidOCRExtracter = None

from ..text_splitter.chinese_text_splitter import ChineseTextSplitter


class PyMuPDFExtracter:
    """Extract text from PDFs using PyMuPDF (fitz). Much faster and more
    accurate than OCR for native-digital PDFs."""

    def __init__(self):
        if not _HAS_PYMUPDF:
            raise ImportError("PyMuPDF not installed")

    def __call__(self, pdf_path: Union[str, Path]) -> List[List]:
        """Return list of [page_index, page_text] pairs."""
        results = []
        doc = fitz.open(str(pdf_path))
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text()
            if text and text.strip():
                results.append([page_idx, text.strip()])
        doc.close()
        return results


class PDFLoader:
    def __init__(self):
        self.splitter = ChineseTextSplitter(pdf=True)
        self._pymupdf = None
        self._ocr = None
        if _HAS_PYMUPDF:
            self._pymupdf = PyMuPDFExtracter()
        if RapidOCRExtracter is not None:
            self._ocr = RapidOCRExtracter()

    def extracter(self, pdf_path: Union[str, Path]) -> List[List]:
        """Return [[page_idx, page_text], ...] — used by kb_service."""
        # Try PyMuPDF first
        if self._pymupdf is not None:
            results = self._pymupdf(pdf_path)
            if results:
                return results

        # Fall back to OCR
        if self._ocr is not None:
            return self._ocr(pdf_path)

        return []

    def __call__(self, pdf_path: Union[str, Path]) -> List[str]:
        contents = self.extracter(pdf_path)
        split_contents = [self.splitter.split_text(v[1]) for v in contents]
        return sum(split_contents, [])
