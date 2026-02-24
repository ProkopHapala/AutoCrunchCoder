#!/usr/bin/env python3
"""paper_pipeline.py

Reusable implementation for `tests/test_paper_pipeline.py`.

Design goals:
- Minimal hard dependencies (stdlib-only at import time)
- Optional integrations (docling, LM Studio, bibtexparser, pdfminer, pdf2image)
  are imported lazily and fail-soft (return error string) so batch runs continue.
- No plotting; pure data-oriented helpers.
"""

import os
import re
import json
import glob
import time
import base64
import subprocess
from datetime import datetime
import tempfile
import shutil
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple


DEFAULT_LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
DEFAULT_VLM_MODEL = "allenai/olmocr-2-7b"
DEFAULT_TEXT_MODEL = "phi-4"
DEFAULT_EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"

DEFAULT_PDF_DIR = "/home/prokop/Desktop/PAPERs/Game_Physics"
DEFAULT_OUT_DIR = "/home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out"
DEFAULT_BIBTEX = "/home/prokop/Mendeley_Desktop_bibtex/INTERESTS.bib"


SUMMARY_PROMPT = """Please analyze the following research article markdown.

### Instructions:
1. **Title**: Extract the paper title.
2. **Keywords**: Classify into narrow specific domains (e.g. \"position based dynamics\", \"cloth simulation\", \"Gauss-Seidel\", \"vertex block descent\", NOT broad terms like \"physics\").
3. **Essence**: Main message in 2-3 sentences.
4. **Motivation**: Goals of the research.
5. **Key Results**: What was achieved (3-5 bullet points).
6. **Key Equations**: Rewrite the most important equations in LaTeX ($$...$$ blocks). Include equation names/numbers if available.
7. **Algorithms**: If the paper describes algorithms or computational steps, list them as numbered steps suitable for implementation.
8. **Methods & Abbreviations**: List computational methods, acronyms (e.g. PBD, XPBD, FEM, CG, etc.).
9. **Connections**: List 3-5 concepts/methods that connect this paper to other work (for knowledge graph edges).

Output as structured Markdown with those exact section headers.

---
Article text:
"""


@dataclass
class PaperResult:
    pdf_path: str
    stem: str
    docling_ok: bool = False
    vlm_ok: bool = False
    pdfminer_ok: bool = False
    summary_ok: bool = False
    chunks_count: int = 0
    equations_count: int = 0
    embedding_ok: bool = False
    graph_concepts: List[str] = field(default_factory=list)
    error_log: List[str] = field(default_factory=list)
    md_path: str = ""
    summary_path: str = ""
    backend_used: str = ""
    time_convert: float = 0.0
    time_summary: float = 0.0


def safe_stem(path: str) -> str:
    stem = Path(path).stem
    return re.sub(r"[^\w\-.]", "_", stem)[:120]


def check_lmstudio_with_url(base_url: str) -> List[str]:
    try:
        import requests
        r = requests.get(f"{base_url}/models", timeout=5)
        if r.status_code == 200:
            data = r.json()
            models = [m["id"] for m in data.get("data", [])]
            print(f"[INFO] LM Studio online at {base_url}, models: {models}")
            return models
        return []
    except Exception as e:
        print(f"[WARN] LM Studio not reachable at {base_url}: {e}")
        return []


def openai_client_with_url(base_url: str):
    from openai import OpenAI
    return OpenAI(base_url=base_url, api_key="not-needed")


def discover_pdfs(pdf_dir: str, limit: Optional[int] = None) -> List[str]:
    pdfs = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
    if limit:
        pdfs = pdfs[:limit]
    print(f"[Stage A] Found {len(pdfs)} PDFs in {pdf_dir}" + (f" (limited to {limit})" if limit else ""))
    return pdfs


def discover_pdfs_recursive(pdf_dir: str, max_papers: int = 10000, limit: Optional[int] = None) -> List[str]:
    pdfs = []
    for dirpath, dirnames, filenames in os.walk(pdf_dir):
        filenames.sort()
        for fn in filenames:
            if not fn.lower().endswith(".pdf"):
                continue
            pdfs.append(os.path.join(dirpath, fn))
            if len(pdfs) >= max_papers:
                break
        if len(pdfs) >= max_papers:
            break
    pdfs.sort()
    if limit:
        pdfs = pdfs[:limit]
    print(f"[Stage A] Found {len(pdfs)} PDFs in {pdf_dir} (recursive)" + (f" (limited to {limit})" if limit else ""))
    return pdfs


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _estimate_tokens_from_chars(nchars: int) -> int:
    # crude but stable: English-ish ~4 chars/token
    return max(1, nchars // 4)


def _load_json(path: str, default):
    try:
        if os.path.exists(path):
            return json.loads(Path(path).read_text())
    except Exception:
        pass
    return default


def _strip_pdf_links(src_pdf: str, dst_pdf: str) -> Tuple[str, Optional[str]]:
    """Remove all annotations (including hyperlinks) that break Docling. Keeps original PDF untouched; returns path to cleaned copy."""
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError as e:
        return src_pdf, f"PyPDF2 not installed: {e}"

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


def _save_json(path: str, obj) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, default=str))


def _save_json_atomic(path: str, obj) -> None:
    tmp = path + ".tmp"
    Path(tmp).write_text(json.dumps(obj, indent=2, default=str))
    os.replace(tmp, path)


def _find_summary_and_bib(run_dir: Path, stem: str) -> Tuple[str, str]:
    # Prefer shadow_tree for both summary and bib
    summary_path = ""
    bib_path = ""
    shadow_sum = list(run_dir.glob(f"shadow_tree/**/{stem}.summary.md"))
    if shadow_sum:
        summary_path = str(shadow_sum[0])
    else:
        sums = list((run_dir / "summaries").glob(f"{stem}.md"))
        if sums:
            summary_path = str(sums[0])
    shadow_bib = list(run_dir.glob(f"shadow_tree/**/{stem}.bib"))
    if shadow_bib:
        bib_path = str(shadow_bib[0])
    else:
        bibs = list((run_dir / "markdown").glob(f"{stem}.bib"))
        if bibs:
            bib_path = str(bibs[0])
    return summary_path, bib_path


def refresh_metadata(
    run_dir: str,
    pdf_root: str,
    mirror_root: str,
    registry_path: Optional[str] = None,
    report_path: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    run_dir_p = Path(run_dir)
    logs_dir = run_dir_p / "logs"
    proc_json = logs_dir / "processed.json"
    proc_live_json = logs_dir / "processed_live.json"
    proc_live_tsv = logs_dir / "processed_live.tsv"
    proc_live_bib_json = logs_dir / "bibtex_live.json"
    if not proc_json.exists():
        raise FileNotFoundError(f"processed.json not found: {proc_json}")

    processed_all = _load_json(str(proc_json), default=[])
    if not isinstance(processed_all, list):
        raise RuntimeError(f"processed.json has unexpected type: {type(processed_all)}")

    reg_path = Path(registry_path) if registry_path else None
    reg_data = json.loads(reg_path.read_text()) if reg_path and reg_path.exists() else None
    rep_path = Path(report_path) if report_path else (run_dir_p / "report.json")
    rep_data = json.loads(rep_path.read_text()) if rep_path.exists() else None

    if not db_path:
        db_path = os.path.join(run_dir, "papers.db")
    _db_init(db_path)

    updated = 0
    for item in processed_all:
        pdf_path = item.get("pdf_path", "")
        stem = item.get("stem", "") or safe_stem(pdf_path)
        item["stem"] = stem
        sum_path, bib_path = _find_summary_and_bib(run_dir_p, stem)
        if sum_path:
            item["summary_path"] = sum_path
            item["summary_ok"] = True
        if bib_path:
            item["bibtex_path"] = bib_path
            if item.get("bibtex_status") != "found":
                item["bibtex_status"] = "found"
        if sum_path or bib_path:
            updated += 1
        # push to DB (keep md_text short)
        md_path = item.get("md_path", "")
        md_text = ""
        if md_path and os.path.exists(md_path):
            md_text = Path(md_path).read_text(errors="replace")
        bib_fields = {}
        if bib_path and os.path.exists(bib_path):
            try:
                bib_fields = _bibtex_to_fields(Path(bib_path).read_text(errors="replace"))
                _merge_bib_fields_into_item(item, bib_fields)
            except Exception as e:
                item["bibtex_error"] = str(e)
        fts_payload = {
            "doi": item.get("doi", ""),
            "title": bib_fields.get("title", ""),
            "authors": bib_fields.get("author", ""),
            "year": bib_fields.get("year", ""),
            "journal": bib_fields.get("journal", bib_fields.get("booktitle", "")),
            "md_text": ("\n".join([
                bib_fields.get("keywords", ""),
                md_text,
            ])).strip()[:200000],
        }
        _db_upsert_paper(db_path, item, fts_payload=fts_payload)

        # registry update
        if reg_data is not None:
            rec = reg_data.get(pdf_path, {})
            if sum_path:
                rec["summary_path"] = sum_path
                rec["summary_ok"] = True
            if bib_path:
                rec["bibtex_path"] = bib_path
            reg_data[pdf_path] = rec

    # processed.json + live outputs
    _save_json_atomic(str(proc_json), processed_all)
    cols_live = [
        "pdf_path", "stem", "doi", "bibtex_status", "bibtex_path", "bibtex_title", "bibtex_year", "bibtex_journal",
        "shadow_md_path", "shadow_pdf_path", "md_path", "summary_ok", "summary_path", "timestamp",
    ]
    _write_tsv(str(proc_live_tsv), processed_all, cols_live)
    bib_index = {r.get("stem", ""): {
        "doi": r.get("doi", ""),
        "title": r.get("bibtex_title", ""),
        "authors": r.get("bibtex_authors", ""),
        "year": r.get("bibtex_year", ""),
        "journal": r.get("bibtex_journal", ""),
        "keywords": r.get("bibtex_keywords", ""),
        "bibtex_path": r.get("bibtex_path", ""),
        "bibtex_status": r.get("bibtex_status", ""),
    } for r in processed_all if r.get("stem")}
    _save_json_atomic(str(proc_live_json), processed_all)
    _save_json_atomic(str(proc_live_bib_json), bib_index)

    if reg_data is not None:
        _save_json_atomic(str(reg_path), reg_data)
    if rep_data is not None:
        # report is a list
        for r in rep_data:
            stem = Path(r.get("md_path", "")).stem or r.get("stem", "")
            sum_path, bib_path = _find_summary_and_bib(run_dir_p, stem)
            if sum_path:
                r["summary_path"] = sum_path
                r["summary_ok"] = True
            if bib_path:
                r["bibtex_path"] = bib_path
        _save_json_atomic(str(rep_path), rep_data)

    return {
        "run_dir": str(run_dir_p),
        "updated_items": updated,
        "processed_json": str(proc_json),
        "registry": str(reg_path) if reg_path else "",
        "report": str(rep_path) if rep_path and rep_path.exists() else "",
    }


def _write_tsv(path: str, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    with open(path, "w") as f:
        f.write("\t".join(columns) + "\n")
        for r in rows:
            f.write("\t".join(str(r.get(c, "")) for c in columns) + "\n")


def _sanitize_filename(s: str, max_len: int = 160) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^\w\-\.]+", "_", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_ .-")
    if not s:
        return "untitled"
    return s[:max_len]


def _extract_doi_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", text, re.IGNORECASE)
    return m.group(0) if m else None


def _crossref_bibtex_for_doi(doi: str, timeout_s: float = 10.0) -> Tuple[Optional[str], Optional[str]]:
    try:
        import requests
        # CrossRef supports BibTeX via its transform endpoint.
        # Using Accept negotiation on /works/<doi> is unreliable (often returns JSON).
        url = f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex"
        r = requests.get(url, timeout=timeout_s)
        if r.status_code != 200:
            return None, f"CrossRef HTTP {r.status_code}: {r.text[:200]}"
        bib = r.text
        bib_s = (bib or "").strip()
        if (not bib_s) or (len(bib_s) < 20):
            return None, "CrossRef returned empty BibTeX"
        if not bib_s.lstrip().startswith("@"):  # sanity check
            return None, f"CrossRef returned non-BibTeX content: {bib_s[:200]}"
        return bib, None
    except Exception as e:
        return None, f"CrossRef request failed: {e}"


def _crossref_search_doi_by_title(title: str, timeout_s: float = 10.0) -> Tuple[Optional[str], Optional[str]]:
    try:
        import requests
        url = "https://api.crossref.org/works"
        params = {"query.title": title, "rows": 1}
        r = requests.get(url, params=params, timeout=timeout_s)
        if r.status_code != 200:
            return None, f"CrossRef search HTTP {r.status_code}: {r.text[:200]}"
        items = r.json().get("message", {}).get("items", [])
        if not items:
            return None, "CrossRef search returned no items"
        doi = items[0].get("DOI")
        if not doi:
            return None, "CrossRef item has no DOI"
        return doi, None
    except Exception as e:
        return None, f"CrossRef search failed: {e}"


def _pdf2doi_lookup(pdf_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (doi, bibtex, err). bibtex may be None even if doi found."""
    try:
        import pdf2doi
        res = pdf2doi.pdf2doi(pdf_path)
        if not res:
            return None, None, "pdf2doi returned empty result"
        rec0 = res[0] if isinstance(res, list) else res
        doi = rec0.get("identifier") or rec0.get("doi")
        if not doi:
            return None, None, "pdf2doi did not find DOI"
        vi = rec0.get("validation_info")
        bib = None
        if isinstance(vi, str) and ("@" in vi):
            bib = vi
        return doi, bib, None
    except ImportError:
        return None, None, "pdf2doi not installed"
    except Exception as e:
        return None, None, f"pdf2doi failed: {e}"


def _bibtex_to_fields(bibtex_text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not bibtex_text:
        return out
    try:
        import bibtexparser
        bib = bibtexparser.loads(bibtex_text)
        if not bib.entries:
            return out
        e = bib.entries[0]
        for k in ("title", "author", "year", "journal", "booktitle", "keywords"):
            if k in e and e[k]:
                out[k] = str(e[k])
        return out
    except Exception as e:
        raise RuntimeError(f"BibTeX parse failed: {e}")


def _merge_bib_fields_into_item(item: Dict[str, Any], bib_fields: Dict[str, str]) -> None:
    if not bib_fields:
        return
    item["bibtex_title"] = bib_fields.get("title", "")
    item["bibtex_authors"] = bib_fields.get("author", "")
    item["bibtex_year"] = bib_fields.get("year", "")
    item["bibtex_journal"] = bib_fields.get("journal", bib_fields.get("booktitle", ""))
    item["bibtex_keywords"] = bib_fields.get("keywords", "")


def _bibtex_first_author_surname(author_field: str) -> str:
    if not author_field:
        return "Unknown"
    first = author_field.split(" and ")[0].strip()
    if "," in first:
        return first.split(",")[0].strip() or "Unknown"
    parts = [p for p in re.split(r"\s+", first) if p]
    return parts[-1] if parts else "Unknown"


def _propose_rename_from_bibtex(bibtex_text: str, template: str) -> Tuple[Optional[str], Dict[str, str]]:
    fields = _bibtex_to_fields(bibtex_text)
    author = fields.get("author", "")
    year = fields.get("year", "")
    journal = fields.get("journal", fields.get("booktitle", ""))
    title = fields.get("title", "")
    first_author = _bibtex_first_author_surname(author)
    short_title = "_".join([w for w in re.split(r"\s+", title.strip()) if w][:6])
    fmt = {
        "first_author": _sanitize_filename(first_author, 40),
        "journal": _sanitize_filename(journal, 60),
        "year": _sanitize_filename(year, 10),
        "title": _sanitize_filename(title, 80),
        "short_title": _sanitize_filename(short_title, 80),
    }
    try:
        base = template.format(**fmt)
    except Exception as e:
        raise RuntimeError(f"rename template format failed: {e}")
    base = _sanitize_filename(base, 160)
    if not base:
        return None, fields
    return base, fields


def _db_init(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS papers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_pdf_path TEXT UNIQUE,
            stem TEXT,
            doi TEXT,
            bibtex_ok INTEGER DEFAULT 0,
            bibtex_path TEXT,
            bibtex_error TEXT,
            bibtex_text TEXT,
            title TEXT,
            authors TEXT,
            year TEXT,
            journal TEXT,
            keywords TEXT,
            shadow_md_path TEXT,
            shadow_pdf_path TEXT,
            rename_target_md TEXT,
            rename_target_pdf TEXT,
            md_path TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS processing_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stem TEXT,
            operation TEXT,
            status TEXT,
            message TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    try:
        cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(stem, doi, title, authors, year, journal, md_text)")
    except Exception as e:
        print(f"[DB] FTS5 not available: {e}")

    # Schema migration for older DBs
    try:
        cur.execute("PRAGMA table_info(papers)")
        have = {r[1] for r in cur.fetchall()}
        want = {
            "bibtex_error": "TEXT",
            "bibtex_text": "TEXT",
            "title": "TEXT",
            "authors": "TEXT",
            "year": "TEXT",
            "journal": "TEXT",
            "keywords": "TEXT",
        }
        for col, ctype in want.items():
            if col not in have:
                cur.execute(f"ALTER TABLE papers ADD COLUMN {col} {ctype}")
    except Exception as e:
        print(f"[DB] Schema migration failed: {e}")
    conn.commit()
    conn.close()


def _db_log(db_path: str, stem: str, operation: str, status: str, message: str = "") -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO processing_log(stem, operation, status, message) VALUES(?,?,?,?)",
        (stem, operation, status, (message or "")[:500]),
    )
    conn.commit()
    conn.close()


def _db_upsert_paper(db_path: str, item: Dict[str, Any], fts_payload: Optional[Dict[str, str]] = None) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO papers(
            original_pdf_path, stem, doi, bibtex_ok, bibtex_path, bibtex_error, bibtex_text,
            title, authors, year, journal, keywords,
            shadow_md_path, shadow_pdf_path, rename_target_md, rename_target_pdf, md_path
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(original_pdf_path) DO UPDATE SET
            stem=excluded.stem,
            doi=excluded.doi,
            bibtex_ok=excluded.bibtex_ok,
            bibtex_path=excluded.bibtex_path,
            bibtex_error=excluded.bibtex_error,
            bibtex_text=excluded.bibtex_text,
            title=excluded.title,
            authors=excluded.authors,
            year=excluded.year,
            journal=excluded.journal,
            keywords=excluded.keywords,
            shadow_md_path=excluded.shadow_md_path,
            shadow_pdf_path=excluded.shadow_pdf_path,
            rename_target_md=excluded.rename_target_md,
            rename_target_pdf=excluded.rename_target_pdf,
            md_path=excluded.md_path
        """,
        (
            item.get("pdf_path", ""),
            item.get("stem", ""),
            item.get("doi", ""),
            int(bool(item.get("bibtex_status") == "found")),
            item.get("bibtex_path", ""),
            item.get("bibtex_error", ""),
            item.get("bibtex_text", ""),
            item.get("bibtex_title", ""),
            item.get("bibtex_authors", ""),
            item.get("bibtex_year", ""),
            item.get("bibtex_journal", ""),
            item.get("bibtex_keywords", ""),
            item.get("shadow_md_path", ""),
            item.get("shadow_pdf_path", ""),
            item.get("rename_target_md", ""),
            item.get("rename_target_pdf", ""),
            item.get("md_path", ""),
        ),
    )
    if fts_payload is not None:
        try:
            cur.execute("DELETE FROM papers_fts WHERE stem=?", (item.get("stem", ""),))
            cur.execute(
                "INSERT INTO papers_fts(stem, doi, title, authors, year, journal, md_text) VALUES(?,?,?,?,?,?,?)",
                (
                    item.get("stem", ""),
                    fts_payload.get("doi", ""),
                    fts_payload.get("title", ""),
                    fts_payload.get("authors", ""),
                    fts_payload.get("year", ""),
                    fts_payload.get("journal", ""),
                    fts_payload.get("md_text", ""),
                ),
            )
        except Exception as e:
            print(f"[DB] FTS insert failed for {item.get('stem','?')}: {e}")
    conn.commit()
    conn.close()


def postprocess_existing_run(
    run_dir: str,
    pdf_root: str,
    mirror_root: str,
    do_mirror: bool = True,
    do_bibtex: bool = True,
    do_rename_plan: bool = True,
    apply_rename: bool = False,
    rename_template: str = "{first_author}_{journal}_{year}_{short_title}",
    db_path: str = "",
    limit: Optional[int] = None,
    crossref_only: bool = False,
    do_summary: bool = False,
    lmstudio_url: str = DEFAULT_LMSTUDIO_BASE_URL,
    text_model: str = DEFAULT_TEXT_MODEL,
    do_refresh: bool = False,
) -> Dict[str, Any]:
    run_dir = os.path.abspath(run_dir)
    logs_dir = os.path.join(run_dir, "logs")
    proc_json = os.path.join(logs_dir, "processed.json")
    if not os.path.exists(proc_json):
        raise FileNotFoundError(f"processed.json not found: {proc_json}")

    processed_all = _load_json(proc_json, default=[])
    if not isinstance(processed_all, list):
        raise RuntimeError(f"processed.json has unexpected type: {type(processed_all)}")

    # Crash-safe streaming outputs
    stamp = _now_stamp()
    backup_path = proc_json + f".bak_{stamp}"
    shutil.copy2(proc_json, backup_path)
    proc_live_json = os.path.join(logs_dir, "processed_live.json")
    proc_live_tsv = os.path.join(logs_dir, "processed_live.tsv")
    proc_live_bib_json = os.path.join(logs_dir, "bibtex_live.json")

    processed = processed_all
    if limit is not None:
        processed = processed_all[:limit]

    if not db_path:
        db_path = os.path.join(run_dir, "papers.db")
    _db_init(db_path)

    has_text = False
    client = None
    if do_summary:
        lm_models = check_lmstudio_with_url(lmstudio_url)
        has_text = any(text_model in m for m in lm_models) if lm_models else False
        client = openai_client_with_url(lmstudio_url) if lm_models else None
        if not has_text:
            print(f"[WARN] Text model '{text_model}' not found in LM Studio, summarization disabled")

    os.makedirs(mirror_root, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    rename_rows: List[Dict[str, Any]] = []
    renamed_dir = os.path.join(run_dir, "renamed")
    if apply_rename:
        os.makedirs(renamed_dir, exist_ok=True)

    t0_all = time.time()
    n_mirror = 0
    n_bib = 0
    n_bib_ok = 0
    n_ren = 0

    for item in processed:
        pdf_path = item.get("pdf_path", "")
        stem = item.get("stem", "") or safe_stem(pdf_path)
        item["stem"] = stem

        md_path = item.get("md_path", "")
        if (not md_path) or (not os.path.exists(md_path)):
            md_guess = os.path.join(run_dir, "markdown", f"{stem}.md")
            if os.path.exists(md_guess):
                md_path = md_guess
                item["md_path"] = md_path

        try:
            rel = os.path.relpath(pdf_path, pdf_root)
        except Exception:
            rel = os.path.basename(pdf_path)
        rel_stem = Path(rel).with_suffix("").as_posix()

        shadow_md_path = ""
        if do_mirror:
            shadow_md_path = os.path.join(mirror_root, rel_stem + ".md")
            os.makedirs(os.path.dirname(shadow_md_path), exist_ok=True)
            if md_path and os.path.exists(md_path):
                shutil.copy2(md_path, shadow_md_path)
                n_mirror += 1
                item["shadow_md_path"] = shadow_md_path
                _db_log(db_path, stem, "mirror_md", "ok", shadow_md_path)
            else:
                item["shadow_md_path"] = ""
                _db_log(db_path, stem, "mirror_md", "fail", f"missing md_path: {md_path}")

            item["shadow_pdf_path"] = os.path.join(mirror_root, rel)

        doi = item.get("doi", "")
        bibtex_status = item.get("bibtex_status", "")
        bibtex_path = item.get("bibtex_path", "")

        if do_bibtex:
            n_bib += 1
            try:
                bibtex_text = None
                item.pop("bibtex_error", None)
                item.pop("bibtex_text", None)
                if not crossref_only:
                    doi2, bib2, err_pdf2doi = _pdf2doi_lookup(pdf_path)
                    if err_pdf2doi:
                        _db_log(db_path, stem, "doi_pdf2doi", "fail", err_pdf2doi)
                    if doi2:
                        doi = doi2
                    if bib2:
                        bibtex_text = bib2
                if (not bibtex_text) and doi:
                    bibtex_text, err2 = _crossref_bibtex_for_doi(doi)
                    if err2:
                        _db_log(db_path, stem, "bibtex_crossref", "fail", err2)
                        item["bibtex_error"] = err2

                if (not doi) and md_path and os.path.exists(md_path):
                    doi3 = _extract_doi_from_text(Path(md_path).read_text(errors="replace"))
                    if doi3:
                        doi = doi3
                        bibtex_text, err3 = _crossref_bibtex_for_doi(doi)
                        if err3:
                            _db_log(db_path, stem, "bibtex_crossref_from_md", "fail", err3)
                            item["bibtex_error"] = err3

                if (not doi) and md_path and os.path.exists(md_path):
                    txt = Path(md_path).read_text(errors="replace")
                    m_title = re.search(r"^title:\s*\"?(.*?)\"?\s*$", txt, re.MULTILINE)
                    if m_title:
                        doi4, err4 = _crossref_search_doi_by_title(m_title.group(1).strip())
                        if doi4:
                            doi = doi4
                            bibtex_text, err5 = _crossref_bibtex_for_doi(doi)
                            if err5:
                                _db_log(db_path, stem, "bibtex_crossref_title", "fail", err5)
                                item["bibtex_error"] = err5
                        elif err4:
                            _db_log(db_path, stem, "doi_crossref_title", "fail", err4)

                if bibtex_text:
                    bibtex_status = "found"
                    n_bib_ok += 1
                    if not bibtex_path:
                        bibtex_path = os.path.join(mirror_root, rel_stem + ".bib") if shadow_md_path else os.path.join(run_dir, "markdown", f"{stem}.bib")
                    os.makedirs(os.path.dirname(bibtex_path), exist_ok=True)
                    Path(bibtex_path).write_text(bibtex_text)
                    item["bibtex_path"] = bibtex_path
                    item["doi"] = doi
                    item["bibtex_status"] = bibtex_status
                    item["bibtex_text"] = bibtex_text
                    try:
                        bib_fields_now = _bibtex_to_fields(bibtex_text)
                        _merge_bib_fields_into_item(item, bib_fields_now)
                    except Exception as e:
                        item["bibtex_error"] = str(e)
                        _db_log(db_path, stem, "bibtex_parse", "error", str(e))
                    _db_log(db_path, stem, "bibtex", "ok", doi)
                else:
                    bibtex_status = "not_found" if not bibtex_status else bibtex_status
                    item["doi"] = doi
                    item["bibtex_status"] = bibtex_status
                    _db_log(db_path, stem, "bibtex", "fail", "not found")
            except Exception as e:
                item["doi"] = doi
                item["bibtex_status"] = "error"
                item["bibtex_error"] = str(e)
                _db_log(db_path, stem, "bibtex", "error", str(e))

        if do_rename_plan and (item.get("bibtex_status") == "found") and item.get("bibtex_path") and os.path.exists(item.get("bibtex_path")):
            try:
                bibtex_text2 = Path(item["bibtex_path"]).read_text(errors="replace")
                base, _ = _propose_rename_from_bibtex(bibtex_text2, rename_template)
                if base:
                    item["rename_target_pdf"] = base + ".pdf"
                    item["rename_target_md"] = base + ".md"
                    rename_rows.append({
                        "stem": stem,
                        "pdf_path": pdf_path,
                        "md_path": md_path,
                        "rename_pdf": item["rename_target_pdf"],
                        "rename_md": item["rename_target_md"],
                        "doi": item.get("doi", ""),
                    })
                    n_ren += 1

                    if apply_rename:
                        dst_pdf = os.path.join(renamed_dir, item["rename_target_pdf"])
                        dst_md = os.path.join(renamed_dir, item["rename_target_md"])
                        if os.path.exists(dst_pdf) or os.path.exists(dst_md):
                            raise RuntimeError(f"rename collision: {dst_pdf} or {dst_md} exists")
                        if os.path.exists(pdf_path):
                            shutil.copy2(pdf_path, dst_pdf)
                        if md_path and os.path.exists(md_path):
                            shutil.copy2(md_path, dst_md)
                        item["rename_applied"] = True
                        item["renamed_pdf_path"] = dst_pdf
                        item["renamed_md_path"] = dst_md
                else:
                    _db_log(db_path, stem, "rename_plan", "fail", "no base")
            except Exception as e:
                item["rename_plan_error"] = str(e)
                _db_log(db_path, stem, "rename_plan", "error", str(e))

        if do_summary and has_text and client and md_path and os.path.exists(md_path):
            try:
                md_text_for_sum = Path(md_path).read_text(errors="replace")
                t1 = time.time()
                summary, err = summarize_paper(md_text_for_sum, client, text_model)
                if summary:
                    item["summary_ok"] = True
                    sum_path = os.path.join(run_dir, "summaries", f"{stem}.md")
                    sum_header = "---\n"
                    sum_header += f'source: "{stem}"\n'
                    sum_header += f'source_pdf: "{pdf_path}"\n'
                    sum_header += "---\n\n"
                    Path(sum_path).write_text(sum_header + summary)
                    item["summary_path"] = sum_path
                    
                    graph_concepts = extract_graph_concepts(summary)
                    item["graph_concepts"] = len(graph_concepts)
                    _db_log(db_path, stem, "summarize", "ok", f"{len(summary)} chars, {len(graph_concepts)} concepts")
                    
                    if do_mirror:
                        shadow_sum = os.path.join(mirror_root, rel_stem + ".summary.md")
                        os.makedirs(os.path.dirname(shadow_sum), exist_ok=True)
                        shutil.copy2(sum_path, shadow_sum)
                else:
                    item["summary_ok"] = False
                    _db_log(db_path, stem, "summarize", "fail", str(err))
                item["time_summary_s"] = round(time.time() - t1, 4)
            except Exception as e:
                _db_log(db_path, stem, "summarize", "error", str(e))

        fts_payload = None
        try:
            md_text = ""
            if md_path and os.path.exists(md_path):
                md_text = Path(md_path).read_text(errors="replace")
            bib_fields = {}
            if item.get("bibtex_status") == "found" and item.get("bibtex_path") and os.path.exists(item.get("bibtex_path")):
                bib_fields = _bibtex_to_fields(Path(item["bibtex_path"]).read_text(errors="replace"))
                _merge_bib_fields_into_item(item, bib_fields)
            fts_payload = {
                "doi": item.get("doi", ""),
                "title": bib_fields.get("title", ""),
                "authors": bib_fields.get("author", ""),
                "year": bib_fields.get("year", ""),
                "journal": bib_fields.get("journal", bib_fields.get("booktitle", "")),
                "md_text": ("\n".join([
                    bib_fields.get("keywords", ""),
                    md_text,
                ])).strip()[:200000],
            }
        except Exception as e:
            _db_log(db_path, stem, "fts_payload", "error", str(e))
        _db_upsert_paper(db_path, item, fts_payload=fts_payload)
        item["postprocess_done"] = True

        # Stream progress to disk after each item (crash-safe)
        try:
            _save_json_atomic(proc_live_json, processed_all)
            cols_live = [
                "pdf_path", "stem", "doi", "bibtex_status", "bibtex_path", "bibtex_title", "bibtex_year", "bibtex_journal",
                "shadow_md_path", "shadow_pdf_path", "md_path", "summary_ok", "summary_path", "timestamp",
            ]
            _write_tsv(proc_live_tsv, processed_all, cols_live)
            bib_index = {r.get("stem", ""): {
                "doi": r.get("doi", ""),
                "title": r.get("bibtex_title", ""),
                "authors": r.get("bibtex_authors", ""),
                "year": r.get("bibtex_year", ""),
                "journal": r.get("bibtex_journal", ""),
                "keywords": r.get("bibtex_keywords", ""),
                "bibtex_path": r.get("bibtex_path", ""),
                "bibtex_status": r.get("bibtex_status", ""),
            } for r in processed_all if r.get("stem")}
            _save_json_atomic(proc_live_bib_json, bib_index)
        except Exception as e:
            _db_log(db_path, stem, "flush_live", "error", str(e))

        try:
            _save_json_atomic(proc_json, processed_all)
        except Exception as e:
            _db_log(db_path, stem, "flush_processed_json", "error", str(e))

    _save_json_atomic(proc_json, processed_all)

    rename_plan_tsv = os.path.join(logs_dir, "rename_plan.tsv")
    if rename_rows:
        _write_tsv(rename_plan_tsv, rename_rows, ["stem", "pdf_path", "md_path", "rename_pdf", "rename_md", "doi"])

    summary = {
        "run_dir": run_dir,
        "mirror_root": os.path.abspath(mirror_root),
        "db_path": os.path.abspath(db_path),
        "processed_json": proc_json,
        "processed_live_json": proc_live_json,
        "processed_live_tsv": proc_live_tsv,
        "bibtex_live_json": proc_live_bib_json,
        "processed_json_backup": backup_path,
        "rename_plan_tsv": rename_plan_tsv if rename_rows else "",
        "n_items": len(processed_all),
        "n_mirrored_md": n_mirror,
        "n_bibtex_attempt": n_bib,
        "n_bibtex_found": n_bib_ok,
        "n_rename_candidates": n_ren,
        "n_summaries": sum(1 for r in processed_all if r.get("summary_ok")),
        "apply_rename": bool(apply_rename),
        "renamed_dir": renamed_dir if apply_rename else "",
        "time_s": round(time.time() - t0_all, 3),
        "crossref_only": bool(crossref_only),
    }
    _save_json(os.path.join(logs_dir, "postprocess_summary.json"), summary)
    print(f"[Postprocess] Updated {proc_json} (backup {backup_path})")
    print(f"[Postprocess] DB: {db_path}")
    if rename_rows:
        print(f"[Postprocess] rename_plan.tsv: {rename_plan_tsv}")

    # Optional refresh pass to backfill registry/report and live files from existing outputs
    if do_refresh:
        reg_default = os.path.join(Path(run_dir).parent, "processed_registry.json")
        rep_default = os.path.join(run_dir, "report.json")
        try:
            refresh_metadata(
                run_dir=run_dir,
                pdf_root=pdf_root,
                mirror_root=mirror_root,
                registry_path=reg_default,
                report_path=rep_default,
                db_path=db_path,
            )
            print("[Refresh] completed")
        except Exception as e:
            print(f"[Refresh] failed: {e}")
    return summary


def load_bibtex_metadata(bib_path: str) -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(bib_path):
        print(f"[Stage B] BibTeX file not found: {bib_path}, skipping metadata")
        return {}
    try:
        import bibtexparser
        with open(bib_path) as f:
            bib = bibtexparser.load(f)
        meta = {}
        for entry in bib.entries:
            title = entry.get("title", "")
            file_field = entry.get("file", "")
            if file_field:
                m = re.search(r":?([^:]+\.pdf):?", file_field, re.IGNORECASE)
                if m:
                    key = Path(m.group(1)).stem.lower()
                    meta[key] = entry
            if title:
                key = re.sub(r"[^\w]", "_", title.lower())[:80]
                meta[key] = entry
        print(f"[Stage B] Loaded {len(bib.entries)} BibTeX entries, mapped {len(meta)} keys")
        return meta
    except Exception as e:
        print(f"[Stage B] BibTeX load error: {e}")
        return {}


def find_bib_entry(stem: str, bib_meta: Dict[str, Dict[str, Any]]):
    key = stem.lower()
    if key in bib_meta:
        return bib_meta[key]
    for k, v in bib_meta.items():
        if k[:30] in key or key[:30] in k:
            return v
    return None


def convert_docling(pdf_path: str, out_dir: str) -> Tuple[Optional[str], Optional[str]]:
    stem = safe_stem(pdf_path)
    docling_out = os.path.join(out_dir, "docling_raw", stem)
    shutil.rmtree(docling_out, ignore_errors=True)
    os.makedirs(docling_out, exist_ok=True)
    cleaned_pdf, clean_err = _strip_pdf_links(pdf_path, os.path.join(docling_out, "clean.pdf"))
    try:
        cmd = [
            "docling", cleaned_pdf,
            "--to", "md",
            "--output", docling_out,
            "--device", "auto",
            "--enrich-formula",
            "--image-export-mode", "placeholder",
        ]
        print(f"  [Docling] Running: {' '.join(cmd[:4])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        Path(os.path.join(docling_out, "docling_stdout.txt")).write_text(result.stdout or "")
        Path(os.path.join(docling_out, "docling_stderr.txt")).write_text(result.stderr or "")
        if result.returncode != 0:
            return None, f"Docling exit {result.returncode}: {result.stderr[:500]}"
        md_files = glob.glob(os.path.join(docling_out, "**", "*.md"), recursive=True)
        if not md_files:
            err_snip = (result.stderr or "")[:400]
            out_snip = (result.stdout or "")[:200]
            try:
                listing = os.listdir(docling_out)
            except Exception:
                listing = []
            return None, f"Docling produced no .md files (outdir: {docling_out}, contents={listing[:10]} | stderr: {err_snip} | stdout: {out_snip})"
        md_file = md_files[-1]
        for mf in md_files:
            if stem[:20].lower() in Path(mf).stem.lower():
                md_file = mf
                break
        md_text = Path(md_file).read_text(errors="replace")
        if len(md_text) < 100:
            return None, f"Docling output too short ({len(md_text)} chars)"
        return md_text, None
    except subprocess.TimeoutExpired:
        return None, "Docling timeout (600s)"
    except FileNotFoundError:
        return None, "Docling CLI not found (not installed?)"
    except Exception as e:
        return None, f"Docling error: {e}"


def convert_vlm(pdf_path: str, client, model: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        # LM Studio vision endpoint expects base64-encoded images, not PDFs.
        # We therefore rasterize a few first pages to PNG and send those.

        png_paths: List[str] = []

        # (1) Prefer pdf2image if available
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, first_page=1, last_page=5, dpi=150)
            import io
            for i, img in enumerate(images):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                # store as a pseudo-path marker by embedding content in memory later
                png_paths.append((i, buf.getvalue()))
        except ImportError:
            png_paths = []

        # (2) Fallback: pdftoppm (poppler-utils)
        if not png_paths:
            try:
                with tempfile.TemporaryDirectory() as td:
                    out_prefix = os.path.join(td, "page")
                    cmd = ["pdftoppm", "-f", "1", "-l", "5", "-r", "150", "-png", pdf_path, out_prefix]
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if r.returncode != 0:
                        return None, f"VLM rasterize failed (pdftoppm exit {r.returncode}): {r.stderr[:300]}"
                    paths = sorted(glob.glob(out_prefix + "-*.png"))
                    if not paths:
                        return None, "VLM rasterize failed: pdftoppm produced no PNGs"
                    for i, p in enumerate(paths):
                        png_paths.append((i, Path(p).read_bytes()))
            except FileNotFoundError:
                return None, "VLM rasterize failed: neither pdf2image nor pdftoppm is available"
            except Exception as e:
                return None, f"VLM rasterize failed: {e}"

        all_md = []
        for i, png_bytes in png_paths:
            img_b64 = base64.b64encode(png_bytes).decode()
            response = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Convert this page ({i+1}) of an academic paper to clean Markdown. Preserve all equations as LaTeX in $$ blocks. Include headings, tables, figure captions."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    ],
                }],
                temperature=0.1,
                max_tokens=4096,
            )
            page_md = response.choices[0].message.content
            all_md.append(f"<!-- Page {i+1} -->\n{page_md}")

        return "\n\n---\n\n".join(all_md), None
    except Exception as e:
        return None, f"VLM error: {e}"


def convert_pdfminer(pdf_path: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(pdf_path)
        if len(text) < 100:
            return None, f"pdfminer output too short ({len(text)} chars)"
        return text, None
    except ImportError:
        return None, "pdfminer not installed"
    except Exception as e:
        return None, f"pdfminer error: {e}"


def chunk_markdown(md_text: str) -> List[str]:
    chunks = re.split(r"\n(?=#{1,3}\s)", md_text)
    return [c.strip() for c in chunks if len(c.strip()) > 50]


def extract_equations(md_text: str) -> List[str]:
    display = re.findall(r"\$\$(.+?)\$\$", md_text, re.DOTALL)
    inline = re.findall(r"(?<!\$)\$([^\$\n]+?)\$(?!\$)", md_text)
    return display + inline


def summarize_paper(md_text: str, client, model: str, max_chars: int = 8000) -> Tuple[Optional[str], Optional[str]]:
    try:
        truncated = md_text[:max_chars]
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": SUMMARY_PROMPT + truncated}],
            temperature=0.2,
            max_tokens=4096,
        )
        return response.choices[0].message.content, None
    except Exception as e:
        return None, f"Summary error: {e}"


def embed_text(text: str, client, model: str) -> Tuple[Optional[List[float]], Optional[str]]:
    try:
        response = client.embeddings.create(model=model, input=text[:8000])
        return response.data[0].embedding, None
    except Exception as e:
        return None, f"Embedding error: {e}"


def extract_graph_concepts(summary_text: str) -> List[str]:
    concepts = []
    m = re.search(r"(?:##?\s*Connections|##?\s*Keywords)(.*?)(?=\n##|\Z)", summary_text, re.DOTALL | re.IGNORECASE)
    if m:
        lines = m.group(1).strip().split("\n")
        for line in lines:
            line = line.strip().lstrip("-*•").strip()
            if len(line) > 2:
                concepts.append(line)
    m2 = re.search(r"(?:##?\s*Keywords)(.*?)(?=\n##|\Z)", summary_text, re.DOTALL | re.IGNORECASE)
    if m2:
        kw_text = m2.group(1).strip()
        for kw in re.split(r"[,\n;]", kw_text):
            kw = kw.strip().lstrip("-*•").strip()
            if len(kw) > 2 and kw not in concepts:
                concepts.append(kw)
    return concepts[:15]


def generate_report(results: List[PaperResult], out_dir: str) -> str:
    report_lines = ["# Paper Pipeline Report\n"]
    report_lines.append("| # | Paper | Backend | Convert | Summary | Chunks | Equations | Graph | Errors |")
    report_lines.append("|---|-------|---------|---------|---------|--------|-----------|-------|--------|")
    for i, r in enumerate(results, 1):
        conv = "OK" if (r.docling_ok or r.vlm_ok or r.pdfminer_ok) else "FAIL"
        summ = "OK" if r.summary_ok else "FAIL"
        errs = "; ".join(r.error_log[:3]) if r.error_log else "-"
        if len(errs) > 60:
            errs = errs[:57] + "..."
        report_lines.append(f"| {i} | {r.stem[:40]} | {r.backend_used} | {conv} | {summ} | {r.chunks_count} | {r.equations_count} | {len(r.graph_concepts)} | {errs} |")

    report_lines.append("\n## Statistics")
    n = len(results)
    n_conv = sum(1 for r in results if r.docling_ok or r.vlm_ok or r.pdfminer_ok)
    n_summ = sum(1 for r in results if r.summary_ok)
    report_lines.append(f"- Total papers: {n}")
    report_lines.append(f"- Converted: {n_conv}/{n}")
    report_lines.append(f"- Summarized: {n_summ}/{n}")
    report_lines.append(f"- Total equations extracted: {sum(r.equations_count for r in results)}")
    report_lines.append(f"- Total graph concepts: {sum(len(r.graph_concepts) for r in results)}")

    report_lines.append("\n## Errors")
    for r in results:
        if r.error_log:
            report_lines.append(f"### {r.stem[:50]}")
            for e in r.error_log:
                report_lines.append(f"- {e}")

    report_md = "\n".join(report_lines)
    report_path = os.path.join(out_dir, "report.md")
    Path(report_path).write_text(report_md)
    print(f"\n[Report] Written to {report_path}")

    json_path = os.path.join(out_dir, "report.json")
    json_data = [asdict(r) for r in results]
    Path(json_path).write_text(json.dumps(json_data, indent=2, default=str))

    graph_path = os.path.join(out_dir, "graph_edges.tsv")
    with open(graph_path, "w") as f:
        f.write("paper\tconcept\n")
        for r in results:
            for c in r.graph_concepts:
                f.write(f"{r.stem}\t{c}\n")
    print(f"[Report] Graph edges written to {graph_path}")

    return report_md


@dataclass
class PaperPipelineConfig:
    pdf_dir: str = DEFAULT_PDF_DIR
    out_dir: str = DEFAULT_OUT_DIR
    limit: Optional[int] = 3
    max_papers: int = 10000
    recursive: bool = False
    shadow: bool = False
    resume: bool = True
    registry_path: str = ""  # if empty, defaults to <out_dir>/processed_registry.json
    backend: str = "auto"  # docling|vlm|pdfminer|auto
    force_vlm: bool = False
    vlm_model: str = DEFAULT_VLM_MODEL
    text_model: str = DEFAULT_TEXT_MODEL
    embed_model: str = DEFAULT_EMBED_MODEL
    bibtex_path: str = DEFAULT_BIBTEX
    use_bibtex: bool = True
    skip_summary: bool = False
    skip_embed: bool = False
    lmstudio_url: str = DEFAULT_LMSTUDIO_BASE_URL


def run_paper_pipeline(cfg: PaperPipelineConfig) -> List[PaperResult]:
    out_dir_root = cfg.out_dir
    os.makedirs(out_dir_root, exist_ok=True)

    run_stamp = _now_stamp()
    out_dir = os.path.join(out_dir_root, run_stamp) if cfg.shadow else out_dir_root
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "markdown"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "summaries"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "chunks"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "logs"), exist_ok=True)

    registry_path = cfg.registry_path if cfg.registry_path else os.path.join(out_dir_root, "processed_registry.json")
    registry = _load_json(registry_path, default={}) if cfg.resume else {}
    processed_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []

    lm_models = check_lmstudio_with_url(cfg.lmstudio_url)
    has_vlm = any(cfg.vlm_model in m for m in lm_models) if lm_models else False
    has_text = any(cfg.text_model in m for m in lm_models) if lm_models else False
    has_embed = any(cfg.embed_model in m for m in lm_models) if lm_models else False
    client = openai_client_with_url(cfg.lmstudio_url) if lm_models else None

    if not has_vlm:
        print(f"[WARN] VLM model '{cfg.vlm_model}' not found in LM Studio, VLM conversion disabled")
    if not has_text:
        print(f"[WARN] Text model '{cfg.text_model}' not found in LM Studio, summarization disabled")
    if not has_embed:
        print(f"[WARN] Embed model '{cfg.embed_model}' not found in LM Studio, embeddings disabled")

    if cfg.recursive:
        pdfs = discover_pdfs_recursive(cfg.pdf_dir, max_papers=cfg.max_papers, limit=cfg.limit)
    else:
        pdfs = discover_pdfs(cfg.pdf_dir, cfg.limit)
    if not pdfs:
        print("[ERROR] No PDFs found. Exiting.")
        return []

    bib_meta = load_bibtex_metadata(cfg.bibtex_path) if (cfg.use_bibtex and cfg.bibtex_path) else {}

    results: List[PaperResult] = []
    for pdf_path in pdfs:
        pdf_path_abs = os.path.abspath(pdf_path)
        if cfg.resume and (pdf_path_abs in registry):
            rec = registry.get(pdf_path_abs, {})
            md_prev = rec.get("md_path", "")
            ok_prev = bool(rec.get("convert_ok", False))
            if ok_prev and md_prev and os.path.exists(md_prev):
                skipped_rows.append({
                    "pdf_path": pdf_path_abs,
                    "reason": "already_processed",
                    "prev_md_path": md_prev,
                    "prev_timestamp": rec.get("timestamp", ""),
                })
                print(f"\n[SKIP] Already processed: {pdf_path_abs}")
                continue
            elif rec.get("convert_ok") is False:
                skipped_rows.append({
                    "pdf_path": pdf_path_abs,
                    "reason": "previous_failure",
                    "prev_md_path": rec.get("md_path", ""),
                    "prev_timestamp": rec.get("timestamp", ""),
                })
                print(f"\n[SKIP] Previously failed conversion: {pdf_path_abs}")
                continue

        stem = safe_stem(pdf_path)
        print(f"\n{'='*70}")
        print(f"[Processing] {Path(pdf_path).name}")
        print(f"{'='*70}")
        r = PaperResult(pdf_path=pdf_path, stem=stem)

        bib_entry = find_bib_entry(stem, bib_meta) if bib_meta else None
        if bib_entry:
            print(f"  [BibTeX] Found: {bib_entry.get('title', '?')[:60]}")

        md_text = None
        t0 = time.time()

        file_size = 0
        try:
            file_size = os.path.getsize(pdf_path)
        except Exception:
            file_size = 0

        backend = cfg.backend
        if cfg.force_vlm:
            backend = "vlm"

        if backend in ("docling", "auto"):
            md_text, err = convert_docling(pdf_path, out_dir)
            if md_text:
                r.docling_ok = True
                r.backend_used = "docling"
                print(f"  [Docling] OK ({len(md_text)} chars)")
            else:
                r.error_log.append(f"Docling: {err}")
                print(f"  [Docling] FAIL: {err}")

        if md_text is None and backend in ("vlm", "auto") and has_vlm and client:
            md_text, err = convert_vlm(pdf_path, client, cfg.vlm_model)
            if md_text:
                r.vlm_ok = True
                r.backend_used = "vlm"
                print(f"  [VLM] OK ({len(md_text)} chars)")
            else:
                r.error_log.append(f"VLM: {err}")
                print(f"  [VLM] FAIL: {err}")

        if md_text is None and (not cfg.force_vlm) and backend in ("pdfminer", "auto"):
            md_text, err = convert_pdfminer(pdf_path)
            if md_text:
                r.pdfminer_ok = True
                r.backend_used = "pdfminer"
                print(f"  [pdfminer] OK ({len(md_text)} chars)")
            else:
                r.error_log.append(f"pdfminer: {err}")
                print(f"  [pdfminer] FAIL: {err}")

        r.time_convert = time.time() - t0

        if md_text:
            header = "---\n"
            header += f'title: "{bib_entry.get("title", stem) if bib_entry else stem}"\n'
            if bib_entry:
                header += f'authors: "{bib_entry.get("author", "")}"\n'
                header += f'year: "{bib_entry.get("year", "")}"\n'
                header += f'doi: "{bib_entry.get("doi", "")}"\n'
            header += f'source_pdf: "{pdf_path}"\n'
            header += f'backend: "{r.backend_used}"\n'
            header += "---\n\n"

            full_md = header + md_text
            md_path = os.path.join(out_dir, "markdown", f"{stem}.md")
            Path(md_path).write_text(full_md)
            r.md_path = md_path
            print(f"  [Saved] {md_path}")

            chunks = chunk_markdown(md_text)
            r.chunks_count = len(chunks)
            chunk_dir = os.path.join(out_dir, "chunks", stem)
            os.makedirs(chunk_dir, exist_ok=True)
            for ci, chunk in enumerate(chunks):
                Path(os.path.join(chunk_dir, f"chunk_{ci:03d}.md")).write_text(chunk)

            equations = extract_equations(md_text)
            r.equations_count = len(equations)
            if equations:
                eq_path = os.path.join(out_dir, "chunks", stem, "equations.md")
                eq_text = "\n\n".join([f"$${eq}$$" for eq in equations[:50]])
                Path(eq_path).write_text(f"# Equations from {stem}\n\n{eq_text}")
            print(f"  [Chunks] {r.chunks_count} chunks, {r.equations_count} equations")

            t1 = time.time()
            if has_text and client and (not cfg.skip_summary):
                summary, err = summarize_paper(md_text, client, cfg.text_model)
                if summary:
                    r.summary_ok = True
                    sum_path = os.path.join(out_dir, "summaries", f"{stem}.md")
                    sum_header = "---\n"
                    sum_header += f'source: "{stem}"\n'
                    sum_header += f'source_pdf: "{pdf_path}"\n'
                    sum_header += "---\n\n"
                    Path(sum_path).write_text(sum_header + summary)
                    r.summary_path = sum_path
                    print(f"  [Summary] OK ({len(summary)} chars)")

                    r.graph_concepts = extract_graph_concepts(summary)
                    print(f"  [Graph] {len(r.graph_concepts)} concepts: {r.graph_concepts[:5]}")
                else:
                    r.error_log.append(f"Summary: {err}")
                    print(f"  [Summary] FAIL: {err}")
            else:
                if not cfg.skip_summary:
                    r.error_log.append("Summary: no text model available")
                print("  [Summary] SKIP")
            r.time_summary = time.time() - t1

            if has_embed and client and (not cfg.skip_embed):
                emb, err = embed_text(md_text[:2000], client, cfg.embed_model)
                if emb:
                    r.embedding_ok = True
                    print(f"  [Embed] OK (dim={len(emb)})")
                else:
                    r.error_log.append(f"Embed: {err}")
                    print(f"  [Embed] FAIL: {err}")
        else:
            r.error_log.append("All conversion backends failed")
            print("  [SKIP] No markdown generated, skipping downstream stages")

        md_chars = len(md_text) if md_text else 0
        md_tokens_est = _estimate_tokens_from_chars(md_chars) if md_chars else 0
        row = {
            "pdf_path": pdf_path_abs,
            "pdf_bytes": file_size,
            "stem": stem,
            "backend_used": r.backend_used,
            "convert_ok": bool(md_text),
            "md_path": r.md_path,
            "md_chars": md_chars,
            "md_tokens_est": md_tokens_est,
            "chunks": r.chunks_count,
            "equations": r.equations_count,
            "summary_ok": r.summary_ok,
            "summary_path": r.summary_path,
            "embed_ok": r.embedding_ok,
            "graph_concepts": len(r.graph_concepts),
            "time_convert_s": round(r.time_convert, 4),
            "time_summary_s": round(r.time_summary, 4),
            "errors": "; ".join(r.error_log[:5]) if r.error_log else "",
            "timestamp": run_stamp,
        }
        processed_rows.append(row)
        registry[pdf_path_abs] = {
            "timestamp": run_stamp,
            "backend_used": r.backend_used,
            "convert_ok": bool(md_text),
            "md_path": r.md_path,
            "summary_ok": r.summary_ok,
            "summary_path": r.summary_path,
            "embed_ok": r.embedding_ok,
            "errors": "; ".join(r.error_log[:5]) if r.error_log else "",
        }
        results.append(r)

    report = generate_report(results, out_dir)
    print(f"\n{'='*70}")
    print(report)
    _save_json(registry_path, registry)

    proc_tsv = os.path.join(out_dir, "logs", "processed.tsv")
    proc_json = os.path.join(out_dir, "logs", "processed.json")
    skip_tsv = os.path.join(out_dir, "logs", "skipped.tsv")
    skip_json = os.path.join(out_dir, "logs", "skipped.json")
    cols = [
        "pdf_path", "pdf_bytes", "stem", "backend_used", "convert_ok", "md_path", "md_chars", "md_tokens_est",
        "chunks", "equations", "summary_ok", "summary_path", "embed_ok", "graph_concepts",
        "time_convert_s", "time_summary_s", "errors", "timestamp",
    ]
    _write_tsv(proc_tsv, processed_rows, cols)
    _save_json(proc_json, processed_rows)
    _write_tsv(skip_tsv, skipped_rows, ["pdf_path", "reason", "prev_md_path", "prev_timestamp"])
    _save_json(skip_json, skipped_rows)
    print(f"[Logs] processed.tsv: {proc_tsv}")
    print(f"[Logs] processed.json: {proc_json}")
    print(f"[Logs] skipped.tsv:   {skip_tsv}")
    print(f"[Logs] skipped.json:  {skip_json}")
    print(f"[Registry] {registry_path}")
    return results
