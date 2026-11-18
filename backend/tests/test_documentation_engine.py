"""Unit and integration tests for DocumentationEngine:
- Markdown documentation extraction (sections, code examples, CLI commands, references)
- PDF documentation extraction (PyMuPDF, page numbers, text, scanned PDF note)
- RST & text documentation
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from app.engines.documentation_engine import DocumentationEngine


def test_markdown_documentation_extraction(tmp_path: Path):
    md_content = """# My Project Documentation

Welcome to the project.

## Installation
Run the following commands to install dependencies:
```bash
pip install -r requirements.txt
npm install
```

## Quickstart
Use `DataProcessor(name="demo")` with `--verbose` flag.
Configure `DATABASE_URL` and `API_KEY` in environment.

```python
processor = DataProcessor()
processor.process()
```
"""
    engine = DocumentationEngine()
    result = engine.extract_markdown(md_content, "docs/README.md")

    assert result.doc_type == "markdown"
    assert result.title == "My Project Documentation"
    assert len(result.sections) >= 3
    assert len(result.code_examples) == 2
    assert any("pip install" in cmd for cmd in result.cli_commands)
    assert any("npm install" in cmd for cmd in result.cli_commands)
    assert any("DATABASE_URL" in cfg for cfg in result.config_references)
    assert "DataProcessor" in result.class_references or "DataProcessor" in result.function_references


def test_pdf_extraction_with_pymupdf(tmp_path: Path):
    # Generate actual test PDF using reportlab
    pdf_path = tmp_path / "manual.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 750, "DocSync System Manual - Page 1")
    c.drawString(100, 730, "Run pip install docsync-ai to install.")
    c.drawString(100, 710, "Set GEMINI_API_KEY before running.")
    c.showPage()
    c.drawString(100, 750, "DocSync System Manual - Page 2")
    c.drawString(100, 730, "System architecture overview.")
    c.save()

    engine = DocumentationEngine()
    result = engine.extract_pdf(pdf_path, "docs/manual.pdf")

    assert result.doc_type == "pdf"
    assert result.total_pages == 2
    assert len(result.sections) == 2
    assert result.sections[0].page_number == 1
    assert result.sections[1].page_number == 2
    assert "GEMINI_API_KEY" in result.config_references
    assert result.extraction_note is None


def test_pdf_scanned_no_text_handling(tmp_path: Path):
    # PDF with blank pages (no text)
    blank_pdf = tmp_path / "blank.pdf"
    c = canvas.Canvas(str(blank_pdf), pagesize=letter)
    c.showPage()
    c.save()

    engine = DocumentationEngine()
    result = engine.extract_pdf(blank_pdf, "docs/blank.pdf")

    assert result.total_pages == 1
    assert result.extraction_note is not None
    assert "Scanned or image-only PDF" in result.extraction_note
