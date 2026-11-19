"""Documentation extraction engine.

Supports:
- Markdown (.md)
- ReStructuredText (.rst)
- Plain text (.txt)
- PDF documents (via PyMuPDF)

Extracts:
- Headings and sections
- Code blocks / examples
- Function / class / parameter references
- Setup instructions and CLI commands
- Configuration references
- Retains PDF page numbers and document references
- Reports limitations for scanned PDFs without extractable text
- Read-only: never modifies original files
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

import pymupdf
from app.models.analysis import DocSection, ExtractedDocFile

CODE_BLOCK_REGEX = re.compile(r"```(?:\w+)?\n([\s\S]*?)```")
INLINE_CODE_REGEX = re.compile(r"`([^`]+)`")
CLI_COMMAND_REGEX = re.compile(r"(?:^\$|^\>|^#)\s+(.*)$|(?:\b(?:npm|pip|yarn|pnpm|python|uvicorn|git|docker|cargo|go)\s+[\w\-./\s]+)", re.MULTILINE)
SETUP_KEYWORDS = re.compile(r"(?:setup|install|installation|getting started|quickstart|prerequisites|requirements)", re.IGNORECASE)
CONFIG_REF_REGEX = re.compile(r"\b([A-Z0-9_]{3,}(?:_KEY|_PORT|_HOST|_URL|_SECRET|_DIR|_ENV|_TIMEOUT|_PATH|_ENABLED|_TOKEN))\b")


class DocumentationEngine:
    """Extracts semantic sections, code examples, and technical references from docs."""

    def extract_markdown(self, text: str, rel_path: str) -> ExtractedDocFile:
        lines = text.splitlines()
        sections: List[DocSection] = []
        code_examples: List[str] = []
        setup_instructions: List[str] = []
        cli_commands: List[str] = []
        config_refs: set[str] = set()
        func_refs: set[str] = set()
        class_refs: set[str] = set()
        param_refs: set[str] = set()

        # 1. Strip fenced code blocks from markdown text when extracting inline elements
        # to avoid capturing code block contents as inline code
        text_without_fenced_blocks = CODE_BLOCK_REGEX.sub("", text)

        # Extract code blocks
        for match in CODE_BLOCK_REGEX.finditer(text):
            code_block = match.group(1).strip()
            if code_block:
                code_examples.append(code_block)
                # Check for cli commands in code block
                for line in code_block.splitlines():
                    if line.strip().startswith(("$", ">")):
                        cli_commands.append(line.lstrip("$> ").strip())
                    elif any(line.strip().startswith(tool) for tool in ("npm ", "pip ", "python ", "git ", "docker ")):
                        cli_commands.append(line.strip())

        # Extract inline code elements (potential function/class/param refs)
        for match in INLINE_CODE_REGEX.finditer(text_without_fenced_blocks):
            item = match.group(1).strip()
            if not item:
                continue
            if "(" in item and ")" in item:
                fn_name = item.split("(")[0].strip()
                if fn_name:
                    func_refs.add(fn_name)
                    # If capitalized, also classify as class ref
                    if re.match(r"^[A-Z][a-zA-Z0-9_]+$", fn_name):
                        class_refs.add(fn_name)
            elif item.endswith("()"):
                fn_name = item[:-2].strip()
                if fn_name:
                    func_refs.add(fn_name)
                    if re.match(r"^[A-Z][a-zA-Z0-9_]+$", fn_name):
                        class_refs.add(fn_name)
            elif item.startswith("--") or item.startswith("-"):
                param_refs.add(item)
            elif item.isupper() and "_" in item:
                config_refs.add(item)
            elif re.match(r"^[A-Z][a-zA-Z0-9]+$", item):
                class_refs.add(item)
            elif re.match(r"^[a-z][a-z0-9_]{2,}$", item) and "_" in item:
                func_refs.add(item)

        # Parse sections based on markdown headings
        current_heading = "Overview"
        current_level = 1
        current_content_lines: List[str] = []
        title = None

        for line in lines:
            h_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if h_match:
                if current_content_lines or current_heading != "Overview":
                    sec_text = "\n".join(current_content_lines).strip()
                    sections.append(
                        DocSection(
                            heading=current_heading,
                            level=current_level,
                            content=sec_text,
                        )
                    )
                    if SETUP_KEYWORDS.search(current_heading):
                        setup_instructions.append(f"{current_heading}:\n{sec_text}")

                current_level = len(h_match.group(1))
                current_heading = h_match.group(2).strip()
                if title is None:
                    title = current_heading
                current_content_lines = []
            else:
                current_content_lines.append(line)

        # Append last section
        if current_content_lines:
            sec_text = "\n".join(current_content_lines).strip()
            sections.append(
                DocSection(
                    heading=current_heading,
                    level=current_level,
                    content=sec_text,
                )
            )
            if SETUP_KEYWORDS.search(current_heading):
                setup_instructions.append(f"{current_heading}:\n{sec_text}")

        # Config refs in general text
        for match in CONFIG_REF_REGEX.finditer(text):
            config_refs.add(match.group(1))

        return ExtractedDocFile(
            file_path=rel_path,
            doc_type="markdown",
            title=title or Path(rel_path).stem,
            sections=sections,
            code_examples=code_examples,
            function_references=sorted(list(func_refs)),
            class_references=sorted(list(class_refs)),
            parameter_references=sorted(list(param_refs)),
            setup_instructions=setup_instructions,
            cli_commands=list(dict.fromkeys(cli_commands)),
            config_references=sorted(list(config_refs)),
        )

    def extract_rst(self, text: str, rel_path: str) -> ExtractedDocFile:
        # Simple RST section parser
        lines = text.splitlines()
        sections: List[DocSection] = []
        code_examples: List[str] = []
        cli_commands: List[str] = []
        config_refs: set[str] = set()

        for match in CONFIG_REF_REGEX.finditer(text):
            config_refs.add(match.group(1))

        # Check for literal blocks
        for match in re.finditer(r"::\n\n((?:[ \t]+[^\n]+\n*)+)", text):
            code_examples.append(match.group(1).strip())

        sections.append(
            DocSection(
                heading="Documentation",
                level=1,
                content=text,
            )
        )

        return ExtractedDocFile(
            file_path=rel_path,
            doc_type="rst",
            title=Path(rel_path).stem,
            sections=sections,
            code_examples=code_examples,
            config_references=sorted(list(config_refs)),
        )

    def extract_plain_text(self, text: str, rel_path: str) -> ExtractedDocFile:
        config_refs = set(CONFIG_REF_REGEX.findall(text))
        return ExtractedDocFile(
            file_path=rel_path,
            doc_type="text",
            title=Path(rel_path).stem,
            sections=[DocSection(heading="Content", level=1, content=text.strip())],
            config_references=sorted(list(config_refs)),
        )

    def extract_pdf(self, file_path: Path, rel_path: str) -> ExtractedDocFile:
        """Extracts text, page numbers, code snippets, and references from PDF using PyMuPDF."""
        try:
            doc = pymupdf.open(str(file_path))
        except Exception as e:
            return ExtractedDocFile(
                file_path=rel_path,
                doc_type="pdf",
                title=Path(rel_path).stem,
                extraction_note=f"Failed to open PDF document: {str(e)}",
            )

        total_pages = len(doc)
        sections: List[DocSection] = []
        full_text_list: List[str] = []
        code_examples: List[str] = []
        config_refs: set[str] = set()
        cli_commands: List[str] = []
        setup_instructions: List[str] = []

        total_extracted_chars = 0

        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_text = page.get_text("text").strip()
            total_extracted_chars += len(page_text)
            full_text_list.append(page_text)

            if page_text:
                sections.append(
                    DocSection(
                        heading=f"Page {page_idx + 1}",
                        level=2,
                        content=page_text,
                        page_number=page_idx + 1,
                    )
                )

                # Search code-like snippets or commands
                for line in page_text.splitlines():
                    stripped = line.strip()
                    if any(stripped.startswith(cmd) for cmd in ("pip install", "npm install", "python -m", "docker run")):
                        cli_commands.append(stripped)
                    if SETUP_KEYWORDS.search(stripped):
                        setup_instructions.append(f"Page {page_idx + 1}: {stripped}")

                for match in CONFIG_REF_REGEX.finditer(page_text):
                    config_refs.add(match.group(1))

        doc.close()

        extraction_note = None
        if total_extracted_chars == 0:
            extraction_note = (
                "Scanned or image-only PDF: No extractable text found. "
                "OCR is not enabled in this deterministic analysis phase."
            )

        return ExtractedDocFile(
            file_path=rel_path,
            doc_type="pdf",
            title=Path(rel_path).stem,
            sections=sections,
            code_examples=code_examples,
            setup_instructions=setup_instructions,
            cli_commands=list(dict.fromkeys(cli_commands)),
            config_references=sorted(list(config_refs)),
            total_pages=total_pages,
            extraction_note=extraction_note,
        )

    def extract_file(self, file_path: Path, rel_path: str) -> Optional[ExtractedDocFile]:
        """Dispatches documentation extraction based on file extension."""
        ext = file_path.suffix.lower()
        if ext in {".md", ".markdown"}:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                return self.extract_markdown(content, rel_path)
            except Exception as e:
                return ExtractedDocFile(
                    file_path=rel_path,
                    doc_type="markdown",
                    extraction_note=f"Error reading file: {str(e)}",
                )
        elif ext in {".rst"}:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                return self.extract_rst(content, rel_path)
            except Exception as e:
                return ExtractedDocFile(
                    file_path=rel_path,
                    doc_type="rst",
                    extraction_note=f"Error reading file: {str(e)}",
                )
        elif ext in {".txt"}:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                return self.extract_plain_text(content, rel_path)
            except Exception as e:
                return ExtractedDocFile(
                    file_path=rel_path,
                    doc_type="text",
                    extraction_note=f"Error reading file: {str(e)}",
                )
        elif ext == ".pdf":
            return self.extract_pdf(file_path, rel_path)

        return None


documentation_engine = DocumentationEngine()
