from pathlib import Path

from pypdf import PdfReader
from docx import Document


class DocumentExtractor:
    """Extract text while preserving document page information."""

    SUPPORTED_FORMATS = {".pdf", ".docx", ".txt"}

    def extract(self, file_path):
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported file format: {extension}"
            )

        if extension == ".pdf":
            return self._extract_pdf(path)

        if extension == ".docx":
            return self._extract_docx(path)

        if extension == ".txt":
            return self._extract_txt(path)

    def _extract_pdf(self, path):
        reader = PdfReader(str(path))
        pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            pages.append({
                "page": page_number,
                "text": text.strip()
            })

        extracted_characters = sum(
            len(page["text"]) for page in pages
        )

        return {
            "file_name": path.name,
            "file_type": "pdf",
            "page_count": len(pages),
            "pages": pages,
            "needs_ocr": extracted_characters == 0,
            "extracted_characters": extracted_characters,
        }

    def _extract_docx(self, path):
        document = Document(str(path))

        paragraphs = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        # Include text inside tables.
        for table in document.tables:
            for row in table.rows:
                cells = [
                    cell.text.strip()
                    for cell in row.cells
                    if cell.text.strip()
                ]

                if cells:
                    paragraphs.append(" | ".join(cells))

        text = "\n".join(paragraphs)

        return {
            "file_name": path.name,
            "file_type": "docx",
            "page_count": None,
            "pages": [{
                "page": None,
                "text": text
            }],
            "needs_ocr": False,
            "extracted_characters": len(text),
        }

    def _extract_txt(self, path):
        text = path.read_text(encoding="utf-8-sig")

        return {
            "file_name": path.name,
            "file_type": "txt",
            "page_count": None,
            "pages": [{
                "page": None,
                "text": text.strip()
            }],
            "needs_ocr": False,
            "extracted_characters": len(text),
        }
