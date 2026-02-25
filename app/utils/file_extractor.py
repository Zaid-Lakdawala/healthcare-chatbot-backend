from PyPDF2 import PdfReader
from docx import Document


class FileExtractor:

    @staticmethod
    def extract(file):
        filename = file.filename.lower()

        if filename.endswith(".txt"):
            return file.read().decode("utf-8")

        if filename.endswith(".pdf"):
            reader = PdfReader(file)
            return "".join(page.extract_text() or "" for page in reader.pages)

        if filename.endswith(".docx"):
            doc = Document(file)
            return "\n".join([p.text for p in doc.paragraphs])

        return file.read().decode("utf-8", errors="ignore")
