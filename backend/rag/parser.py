"""
parser.py — Multi-format document text extraction for AIDA.

Extracts text from PDFs, Markdown (.md), Plain text (.txt), and Word docs (.docx),
returning page-indexed records for chunking and embedding.
"""

import os
import re
from typing import List, Dict, Any

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import docx
except ImportError:
    docx = None


def parse_pdf(filepath: str) -> List[Dict[str, Any]]:
    """
    Extract text from a PDF file, page by page.

    Args:
        filepath: Path to the PDF file.

    Returns:
        List of dicts: [{"text": "...", "source": "filename.pdf", "page": 1}, ...]
    """
    if not pdfplumber:
        print("[Parser] Warning: pdfplumber not installed, skipping PDF extraction.")
        return []

    pages = []
    filename = os.path.basename(filepath)

    try:
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    pages.append({
                        "text": text.strip(),
                        "source": filename,
                        "page": i + 1,
                    })
    except Exception as e:
        print(f"[Parser] Error reading PDF {filename}: {e}")

    return pages


def parse_text_file(filepath: str, chars_per_page: int = 1500) -> List[Dict[str, Any]]:
    """
    Extract text from a Markdown (.md) or Text (.txt) file, splitting into logical pages.
    """
    pages = []
    filename = os.path.basename(filepath)

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()

        if not content:
            return []

        # Check for form feed or major markdown headings
        if "\f" in content:
            raw_pages = content.split("\f")
        else:
            # Split into chunks of approx chars_per_page along paragraph breaks
            paragraphs = content.split("\n\n")
            raw_pages = []
            current_page = []
            current_len = 0

            for p in paragraphs:
                p_len = len(p)
                if current_len + p_len > chars_per_page and current_page:
                    raw_pages.append("\n\n".join(current_page))
                    current_page = [p]
                    current_len = p_len
                else:
                    current_page.append(p)
                    current_len += p_len + 2

            if current_page:
                raw_pages.append("\n\n".join(current_page))

        for i, text in enumerate(raw_pages):
            clean_text = text.strip()
            if clean_text:
                pages.append({
                    "text": clean_text,
                    "source": filename,
                    "page": i + 1,
                })

    except Exception as e:
        print(f"[Parser] Error reading text file {filename}: {e}")

    return pages


def parse_docx(filepath: str) -> List[Dict[str, Any]]:
    """Extract text from a .docx file."""
    if not docx:
        return []

    filename = os.path.basename(filepath)
    try:
        doc = docx.Document(filepath)
        full_text = "\n\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        if full_text:
            return [{
                "text": full_text,
                "source": filename,
                "page": 1,
            }]
    except Exception as e:
        print(f"[Parser] Error reading docx {filename}: {e}")

    return []


def parse_document(filepath: str) -> List[Dict[str, Any]]:
    """Parse single document based on extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return parse_pdf(filepath)
    elif ext in (".md", ".txt"):
        return parse_text_file(filepath)
    elif ext == ".docx":
        return parse_docx(filepath)
    return []


def parse_all_documents(docs_dir: str) -> List[Dict[str, Any]]:
    """
    Parse all supported documents (PDF, MD, TXT, DOCX) in a directory.
    """
    all_pages = []

    if not os.path.exists(docs_dir):
        print(f"[Parser] Directory not found: {docs_dir}")
        return []

    supported_extensions = (".pdf", ".md", ".txt", ".docx")

    for filename in sorted(os.listdir(docs_dir)):
        ext = os.path.splitext(filename)[1].lower()
        if ext in supported_extensions:
            filepath = os.path.join(docs_dir, filename)
            print(f"  Parsing: {filename}")
            pages = parse_document(filepath)
            all_pages.extend(pages)
            print(f"    -> {len(pages)} pages extracted from {filename}")

    return all_pages


# Backward compatibility alias
parse_all_pdfs = parse_all_documents
