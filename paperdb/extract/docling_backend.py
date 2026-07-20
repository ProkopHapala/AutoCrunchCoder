"""Docling backend — primary PDF extraction parser.

Uses the Docling CLI to convert PDFs to Markdown + structured JSON.
Adapts the proven approach from pyCruncher/paper_pipeline.py:convert_docling
but produces normalized structured output suitable for equation extraction.

Key design decisions (§18 D20, §17 Phase 2):
- Markdown is the central complete representation — must preserve equations in LaTeX,
  section hierarchy, reading order, tables/captions.
- Do NOT produce a separate docling.json — the single paper JSON contains the useful
  normalized Docling structure. Raw parser debug output goes to logs/debug/ only
  when --keep-parser-debug is requested.
- Reuses _strip_pdf_links from pyCruncher.paper_pipeline to avoid Docling crashes
  on hyperlinked PDFs.
"""
import os, json, glob, shutil, subprocess, tempfile, time, re
from pathlib import Path
from typing import Optional

from .base import BaseParser, ExtractionResult


def _strip_pdf_links(src_pdf: str, dst_pdf: str) -> tuple[str, Optional[str]]:
    """Remove annotations/hyperlinks that break Docling. Returns (cleaned_path, error_or_None)."""
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        return src_pdf, "PyPDF2 not installed — using original PDF"
    try:
        reader = PdfReader(src_pdf)
        writer = PdfWriter()
        for page in reader.pages:
            if "/Annots" in page:
                del page["/Annots"]
            writer.add_page(page)
        with open(dst_pdf, "wb") as f:
            writer.write(f)
        return dst_pdf, None
    except Exception as e:
        return src_pdf, f"strip_links_error: {e}"


def _safe_stem(pdf_path: str) -> str:
    return Path(pdf_path).stem


class DoclingParser(BaseParser):
    """Parse PDFs using the Docling CLI — produces Markdown + structured JSON."""

    @property
    def backend_name(self) -> str:
        return "docling"

    def __init__(self, timeout: int = 600, debug_dir: Optional[str] = None):
        self.timeout = timeout
        self.debug_dir = debug_dir  # where to save raw debug output if keep_debug=True

    def parse(self, pdf_path: str, keep_debug: bool = False) -> ExtractionResult:
        t0 = time.time()
        stem = _safe_stem(pdf_path)

        with tempfile.TemporaryDirectory(prefix="docling_") as tmpdir:
            # Strip PDF links to avoid Docling crashes
            cleaned_pdf, clean_err = _strip_pdf_links(pdf_path, os.path.join(tmpdir, "clean.pdf"))
            if clean_err:
                print(f"  [Docling] Warning: {clean_err}")

            # Run docling CLI with both md and json output
            out_dir = os.path.join(tmpdir, "out")
            os.makedirs(out_dir, exist_ok=True)
            cmd = [
                "docling", cleaned_pdf,
                "--to", "md",
                "--to", "json",
                "--output", out_dir,
                "--device", "auto",
                "--enrich-formula",
                "--image-export-mode", "placeholder",
            ]
            print(f"  [Docling] Running: {' '.join(cmd[:4])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)

            if result.returncode != 0:
                raise RuntimeError(f"Docling exit {result.returncode}: {result.stderr[:500]}")

            # Find markdown output
            md_files = glob.glob(os.path.join(out_dir, "**", "*.md"), recursive=True)
            if not md_files:
                raise RuntimeError(f"Docling produced no .md files (outdir: {out_dir})")
            md_file = md_files[-1]
            for mf in md_files:
                if stem[:20].lower() in Path(mf).stem.lower():
                    md_file = mf
                    break
            md_text = Path(md_file).read_text(errors="replace")
            if len(md_text) < 100:
                raise RuntimeError(f"Docling output too short ({len(md_text)} chars)")

            # Find JSON output (structured)
            json_files = glob.glob(os.path.join(out_dir, "**", "*.json"), recursive=True)
            raw_structured = {}
            if json_files:
                # Prefer the JSON file matching the stem
                json_file = json_files[-1]
                for jf in json_files:
                    if stem[:20].lower() in Path(jf).stem.lower():
                        json_file = jf
                        break
                try:
                    raw_structured = json.loads(Path(json_file).read_text(errors="replace"))
                except json.JSONDecodeError as e:
                    print(f"  [Docling] Warning: failed to parse JSON: {e}")

            # Save raw debug output if requested
            if keep_debug and self.debug_dir:
                dbg = os.path.join(self.debug_dir, stem)
                os.makedirs(dbg, exist_ok=True)
                shutil.copytree(out_dir, dbg, dirs_exist_ok=True)
                Path(os.path.join(dbg, "docling_stdout.txt")).write_text(result.stdout or "")
                Path(os.path.join(dbg, "docling_stderr.txt")).write_text(result.stderr or "")

        # Normalize structured output
        structured = self._normalize_structured(raw_structured, md_text)
        equations = self._extract_equation_items(raw_structured, structured)
        sections = structured.get("sections", [])
        tables = structured.get("tables", [])

        elapsed = time.time() - t0
        metadata = {
            "backend": "docling",
            "version": self._get_docling_version(),
            "timing_sec": round(elapsed, 2),
            "md_chars": len(md_text),
            "equations_found": len(equations),
            "sections_found": len(sections),
        }

        return ExtractionResult(
            markdown=md_text,
            structured_json=structured,
            equations=equations,
            sections=sections,
            tables=tables,
            metadata=metadata,
        )

    def _get_docling_version(self) -> str:
        try:
            r = subprocess.run(["docling", "--version"], capture_output=True, text=True, timeout=10)
            return (r.stdout or r.stderr or "").strip()
        except Exception:
            return "unknown"

    def _normalize_structured(self, raw_json: dict, md_text: str) -> dict:
        """Normalize Docling JSON into our standard structured format.
        Docling JSON has a 'texts' array with elements that have 'label', 'text', 'page', 'bbox'.
        We extract sections, equations, and tables from this.
        """
        if not raw_json:
            # Fallback: parse sections from markdown headings
            return self._fallback_from_markdown(md_text)

        texts = raw_json.get("texts", [])
        sections = []
        tables = []
        current_section_path = []

        for item in texts:
            label = item.get("label", "").lower()
            text = item.get("text", "")
            page = item.get("page", 1)
            bbox = item.get("bbox", None)

            if label in ("section_header", "title", "heading"):
                level = item.get("level", 1)
                # Build section path
                while len(current_section_path) >= level:
                    current_section_path.pop()
                current_section_path.append(text)
                sections.append({
                    "heading": text,
                    "level": level,
                    "section_path": " > ".join(current_section_path),
                    "page": page,
                    "content": "",
                })
            elif label == "table" or label == "table_caption":
                tables.append({
                    "text": text,
                    "page": page,
                    "bbox": bbox,
                    "caption": label == "table_caption",
                })
            elif sections and label in ("paragraph", "text", "list_item", "caption"):
                # Append content to last section
                sections[-1]["content"] += text + "\n"

        return {
            "sections": sections,
            "tables": tables,
            "raw_element_count": len(texts),
            "docling_json_keys": list(raw_json.keys()),
        }

    def _extract_equation_items(self, raw_json: dict, structured: dict) -> list[dict]:
        """Extract equation items from Docling structured output.
        Docling with --enrich-formula produces formula elements with LaTeX.
        """
        equations = []
        if not raw_json:
            return equations

        texts = raw_json.get("texts", [])
        current_section = ""
        prev_text = ""

        for i, item in enumerate(texts):
            label = item.get("label", "").lower()
            text = item.get("text", "")
            page = item.get("page", 1)
            bbox = item.get("bbox", None)

            if label in ("section_header", "title", "heading"):
                current_section = text
                continue

            # Docling labels equations as "formula" or contains $...$ patterns
            if label == "formula" or (text.strip().startswith("$$") and text.strip().endswith("$$")):
                # Preserve the parser payload byte-for-byte (apart from surrounding
                # JSON string representation); normalization happens downstream.
                latex_raw = text
                eq_number = None
                number_text = text.strip()
                if number_text.startswith("$$") and number_text.endswith("$$"): number_text = number_text[2:-2].strip()
                elif number_text.startswith("$") and number_text.endswith("$"): number_text = number_text[1:-1].strip()
                eq_num_match = re.search(r'\((\d+(?:\.\d+)*)\)\s*$', number_text)
                if eq_num_match: eq_number = eq_num_match.group(1)

                # Context: previous and next text items
                context_before = prev_text[-200:] if prev_text else ""
                next_text = ""
                if i + 1 < len(texts):
                    next_text = texts[i + 1].get("text", "")[:200]

                equations.append({
                    "latex_raw": latex_raw,
                    "latex_normalized": None,  # to be filled by equation extraction module
                    "equation_number": eq_number,
                    "section_path": current_section,
                    "page_number": page,
                    "bbox_json": json.dumps(bbox) if bbox else None,
                    "context_before": context_before,
                    "context_after": next_text,
                    "parser": "docling",
                    "confidence": None,
                })

            prev_text = text

        return equations

    def _fallback_from_markdown(self, md_text: str) -> dict:
        """When Docling JSON is not available, parse structure from markdown headings."""
        sections = []
        current_section_path = []
        current_content = []

        for line in md_text.split("\n"):
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                # Save previous section content
                if sections:
                    sections[-1]["content"] = "\n".join(current_content).strip()
                current_content = []
                level = len(heading_match.group(1))
                text = heading_match.group(2)
                while len(current_section_path) >= level:
                    current_section_path.pop()
                current_section_path.append(text)
                sections.append({
                    "heading": text,
                    "level": level,
                    "section_path": " > ".join(current_section_path),
                    "page": None,
                    "content": "",
                })
            else:
                current_content.append(line)

        if sections:
            sections[-1]["content"] = "\n".join(current_content).strip()

        return {"sections": sections, "tables": [], "raw_element_count": 0, "docling_json_keys": []}
