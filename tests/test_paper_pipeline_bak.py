#!/usr/bin/env python3
"""
Consolidated paper processing pipeline for converting scientific PDFs to markdown,
summarizing them, extracting equations, and building a lightweight knowledge graph.

Goals:
  1) Accurate PDF -> Markdown with faithful equations (Docling or VLM OCR)
  2) Summarization: insights, takeaways, equations, algorithms for coding
  3) Navigable knowledge graph: topic/equation relations across papers

Usage:
  source ~/venvs/ML/bin/activate
  python test_paper_pipeline.py --pdf-dir /path/to/pdfs --limit 3
  python test_paper_pipeline.py --help
"""

import os
import sys
import re
import json
import glob
import time
import base64
import argparse
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
LMSTUDIO_BASE_URL   = "http://localhost:1234/v1"
VLM_MODEL           = "allenai/olmocr-2-7b"
TEXT_MODEL           = "mistralai/devstral-small-2-2512"
EMBED_MODEL          = "text-embedding-nomic-embed-text-v1.5"
DEFAULT_PDF_DIR      = "/home/prokop/Desktop/PAPERs/Game_Physics"
DEFAULT_OUT_DIR      = "/home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out"
DEFAULT_BIBTEX       = "/home/prokop/Mendeley_Desktop_bibtex/INTERESTS.bib"

# ---------------------------------------------------------------------------
# Summarization prompt (reused from existing repo prompts)
# ---------------------------------------------------------------------------
SUMMARY_PROMPT = """Please analyze the following research article markdown.

### Instructions:
1. **Title**: Extract the paper title.
2. **Keywords**: Classify into narrow specific domains (e.g. "position based dynamics", "cloth simulation", "Gauss-Seidel", "vertex block descent", NOT broad terms like "physics").
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

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class PaperResult:
    pdf_path: str
    stem: str
    # Stage results
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_stem(path):
    """Make a filesystem-safe stem from a PDF path."""
    stem = Path(path).stem
    stem = re.sub(r'[^\w\-.]', '_', stem)[:120]
    return stem

def check_lmstudio_with_url(base_url):
    """Check if LM Studio server is reachable, return list of model ids."""
    try:
        import requests
        r = requests.get(f"{base_url}/models", timeout=5)
        if r.status_code == 200:
            data = r.json()
            models = [m['id'] for m in data.get('data', [])]
            print(f"[INFO] LM Studio online at {base_url}, models: {models}")
            return models
        return []
    except Exception as e:
        print(f"[WARN] LM Studio not reachable at {base_url}: {e}")
        return []

def openai_client_with_url(base_url):
    """Create an OpenAI client pointing at LM Studio."""
    from openai import OpenAI
    return OpenAI(base_url=base_url, api_key="not-needed")

# ---------------------------------------------------------------------------
# Stage A: Discover PDFs
# ---------------------------------------------------------------------------
def discover_pdfs(pdf_dir, limit=None):
    pdfs = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
    if limit:
        pdfs = pdfs[:limit]
    print(f"[Stage A] Found {len(pdfs)} PDFs in {pdf_dir}" + (f" (limited to {limit})" if limit else ""))
    return pdfs

# ---------------------------------------------------------------------------
# Stage B: BibTeX metadata (optional)
# ---------------------------------------------------------------------------
def load_bibtex_metadata(bib_path):
    """Load BibTeX and return a dict mapping lowercase filename stems to entry dicts."""
    if not os.path.exists(bib_path):
        print(f"[Stage B] BibTeX file not found: {bib_path}, skipping metadata")
        return {}
    try:
        import bibtexparser
        with open(bib_path) as f:
            bib = bibtexparser.load(f)
        meta = {}
        for entry in bib.entries:
            title = entry.get('title', '')
            # Try to map by file field
            file_field = entry.get('file', '')
            if file_field:
                # Mendeley format: :/path/to/file.pdf:pdf
                m = re.search(r':?([^:]+\.pdf):?', file_field, re.IGNORECASE)
                if m:
                    key = Path(m.group(1)).stem.lower()
                    meta[key] = entry
            # Also map by title words (fuzzy)
            if title:
                key = re.sub(r'[^\w]', '_', title.lower())[:80]
                meta[key] = entry
        print(f"[Stage B] Loaded {len(bib.entries)} BibTeX entries, mapped {len(meta)} keys")
        return meta
    except Exception as e:
        print(f"[Stage B] BibTeX load error: {e}")
        return {}

def find_bib_entry(stem, bib_meta):
    """Try to find a matching BibTeX entry for a PDF stem."""
    key = stem.lower()
    if key in bib_meta:
        return bib_meta[key]
    # Fuzzy: check if any key is a substring
    for k, v in bib_meta.items():
        if k[:30] in key or key[:30] in k:
            return v
    return None

# ---------------------------------------------------------------------------
# Stage C: PDF -> Markdown conversion
# ---------------------------------------------------------------------------

def convert_docling(pdf_path, out_dir):
    """Convert PDF to Markdown using Docling CLI. Returns (md_text, success)."""
    stem = safe_stem(pdf_path)
    docling_out = os.path.join(out_dir, "docling_raw")
    os.makedirs(docling_out, exist_ok=True)
    try:
        cmd = [
            "docling", pdf_path,
            "--to", "md",
            "--output", docling_out,
            "--device", "auto",
            "--enrich-formula",
            "--image-export-mode", "placeholder",
        ]
        print(f"  [Docling] Running: {' '.join(cmd[:4])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return None, f"Docling exit {result.returncode}: {result.stderr[:500]}"
        # Find output .md file
        md_files = glob.glob(os.path.join(docling_out, "**", "*.md"), recursive=True)
        if not md_files:
            return None, "Docling produced no .md files"
        # Pick the newest or matching
        md_file = md_files[-1]
        for mf in md_files:
            if stem[:20].lower() in Path(mf).stem.lower():
                md_file = mf
                break
        md_text = Path(md_file).read_text(errors='replace')
        if len(md_text) < 100:
            return None, f"Docling output too short ({len(md_text)} chars)"
        return md_text, None
    except subprocess.TimeoutExpired:
        return None, "Docling timeout (300s)"
    except FileNotFoundError:
        return None, "Docling CLI not found (not installed?)"
    except Exception as e:
        return None, f"Docling error: {e}"

def convert_vlm(pdf_path, client, model=VLM_MODEL):
    """Convert PDF page(s) to Markdown using a vision LLM via LM Studio."""
    try:
        # Convert first few pages to images using pdf2image if available
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, first_page=1, last_page=5, dpi=150)
        except ImportError:
            # Fallback: send PDF as base64 directly (some VLMs support this)
            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()
            response = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Convert this academic paper page to clean Markdown. Preserve all equations as LaTeX in $$ blocks. Include headings, tables, figure captions."},
                        {"type": "image_url", "image_url": {"url": f"data:application/pdf;base64,{pdf_b64}"}}
                    ]
                }],
                temperature=0.1,
                max_tokens=4096,
            )
            return response.choices[0].message.content, None
        except Exception:
            # If pdf2image also fails, try raw base64
            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()
            response = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Convert this academic paper page to clean Markdown. Preserve all equations as LaTeX in $$ blocks."},
                        {"type": "image_url", "image_url": {"url": f"data:application/pdf;base64,{pdf_b64}"}}
                    ]
                }],
                temperature=0.1,
                max_tokens=4096,
            )
            return response.choices[0].message.content, None

        # Process each page image
        import io
        all_md = []
        for i, img in enumerate(images):
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            response = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Convert this page ({i+1}) of an academic paper to clean Markdown. Preserve all equations as LaTeX in $$ blocks. Include headings, tables, figure captions."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                    ]
                }],
                temperature=0.1,
                max_tokens=4096,
            )
            page_md = response.choices[0].message.content
            all_md.append(f"<!-- Page {i+1} -->\n{page_md}")
        return "\n\n---\n\n".join(all_md), None
    except Exception as e:
        return None, f"VLM error: {e}"

def convert_pdfminer(pdf_path):
    """Fallback: extract raw text with pdfminer."""
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

# ---------------------------------------------------------------------------
# Stage D: Chunking
# ---------------------------------------------------------------------------
def chunk_markdown(md_text):
    """Split markdown by headings (## or #). Returns list of chunk strings."""
    chunks = re.split(r'\n(?=#{1,3}\s)', md_text)
    chunks = [c.strip() for c in chunks if len(c.strip()) > 50]
    return chunks

def extract_equations(md_text):
    """Extract LaTeX equations from markdown ($$...$$ and $...$)."""
    display = re.findall(r'\$\$(.+?)\$\$', md_text, re.DOTALL)
    inline  = re.findall(r'(?<!\$)\$([^\$\n]+?)\$(?!\$)', md_text)
    return display + inline

# ---------------------------------------------------------------------------
# Stage E: Summarization via LM Studio text model
# ---------------------------------------------------------------------------
def summarize_paper(md_text, client, model=TEXT_MODEL, max_chars=8000):
    """Send markdown to a text LLM for structured summary. Truncates to fit small context windows."""
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

# ---------------------------------------------------------------------------
# Stage F: Embeddings (optional)
# ---------------------------------------------------------------------------
def embed_text(text, client, model=EMBED_MODEL):
    """Get embedding vector for a text string."""
    try:
        response = client.embeddings.create(model=model, input=text[:8000])
        return response.data[0].embedding, None
    except Exception as e:
        return None, f"Embedding error: {e}"

# ---------------------------------------------------------------------------
# Stage G: Knowledge graph edges
# ---------------------------------------------------------------------------
def extract_graph_concepts(summary_text):
    """Extract concept tags from the summary for graph building."""
    concepts = []
    # Look for the Connections section
    m = re.search(r'(?:##?\s*Connections|##?\s*Keywords)(.*?)(?=\n##|\Z)', summary_text, re.DOTALL | re.IGNORECASE)
    if m:
        lines = m.group(1).strip().split('\n')
        for line in lines:
            line = line.strip().lstrip('-*•').strip()
            if len(line) > 2:
                concepts.append(line)
    # Also extract keywords section
    m2 = re.search(r'(?:##?\s*Keywords)(.*?)(?=\n##|\Z)', summary_text, re.DOTALL | re.IGNORECASE)
    if m2:
        kw_text = m2.group(1).strip()
        for kw in re.split(r'[,\n;]', kw_text):
            kw = kw.strip().lstrip('-*•').strip()
            if len(kw) > 2 and kw not in concepts:
                concepts.append(kw)
    return concepts[:15]

# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_report(results: List[PaperResult], out_dir: str):
    """Generate markdown report table and JSON."""
    report_lines = ["# Paper Pipeline Report\n"]
    report_lines.append(f"| # | Paper | Backend | Convert | Summary | Chunks | Equations | Graph | Errors |")
    report_lines.append(f"|---|-------|---------|---------|---------|--------|-----------|-------|--------|")
    for i, r in enumerate(results, 1):
        conv = "OK" if (r.docling_ok or r.vlm_ok or r.pdfminer_ok) else "FAIL"
        summ = "OK" if r.summary_ok else "FAIL"
        errs = "; ".join(r.error_log[:3]) if r.error_log else "-"
        if len(errs) > 60: errs = errs[:57] + "..."
        report_lines.append(f"| {i} | {r.stem[:40]} | {r.backend_used} | {conv} | {summ} | {r.chunks_count} | {r.equations_count} | {len(r.graph_concepts)} | {errs} |")
    
    report_lines.append(f"\n## Statistics")
    n = len(results)
    n_conv = sum(1 for r in results if r.docling_ok or r.vlm_ok or r.pdfminer_ok)
    n_summ = sum(1 for r in results if r.summary_ok)
    report_lines.append(f"- Total papers: {n}")
    report_lines.append(f"- Converted: {n_conv}/{n}")
    report_lines.append(f"- Summarized: {n_summ}/{n}")
    report_lines.append(f"- Total equations extracted: {sum(r.equations_count for r in results)}")
    report_lines.append(f"- Total graph concepts: {sum(len(r.graph_concepts) for r in results)}")

    # Errors section
    report_lines.append(f"\n## Errors")
    for r in results:
        if r.error_log:
            report_lines.append(f"### {r.stem[:50]}")
            for e in r.error_log:
                report_lines.append(f"- {e}")

    report_md = "\n".join(report_lines)
    report_path = os.path.join(out_dir, "report.md")
    Path(report_path).write_text(report_md)
    print(f"\n[Report] Written to {report_path}")

    # Also save JSON
    json_path = os.path.join(out_dir, "report.json")
    json_data = [asdict(r) for r in results]
    Path(json_path).write_text(json.dumps(json_data, indent=2, default=str))

    # Graph edges TSV
    graph_path = os.path.join(out_dir, "graph_edges.tsv")
    with open(graph_path, 'w') as f:
        f.write("paper\tconcept\n")
        for r in results:
            for c in r.graph_concepts:
                f.write(f"{r.stem}\t{c}\n")
    print(f"[Report] Graph edges written to {graph_path}")

    return report_md

# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run_pipeline(args):
    vlm_model   = args.vlm_model
    text_model  = args.text_model
    embed_model = args.embed_model
    lmstudio_url = args.lmstudio_url

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "markdown"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "summaries"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "chunks"), exist_ok=True)

    # Check LM Studio
    lm_models = check_lmstudio_with_url(lmstudio_url)
    has_vlm   = any(vlm_model in m for m in lm_models)   if lm_models else False
    has_text  = any(text_model in m for m in lm_models)   if lm_models else False
    has_embed = any(embed_model in m for m in lm_models)  if lm_models else False
    client = openai_client_with_url(lmstudio_url) if lm_models else None

    if not has_vlm:   print(f"[WARN] VLM model '{vlm_model}' not found in LM Studio, VLM conversion disabled")
    if not has_text:  print(f"[WARN] Text model '{text_model}' not found in LM Studio, summarization disabled")
    if not has_embed: print(f"[WARN] Embed model '{embed_model}' not found in LM Studio, embeddings disabled")

    # Stage A: Discover
    pdfs = discover_pdfs(args.pdf_dir, args.limit)
    if not pdfs:
        print("[ERROR] No PDFs found. Exiting.")
        return

    # Stage B: BibTeX
    bib_meta = {}
    if args.use_bibtex and args.bibtex_path:
        bib_meta = load_bibtex_metadata(args.bibtex_path)

    results = []

    for pdf_path in pdfs:
        stem = safe_stem(pdf_path)
        print(f"\n{'='*70}")
        print(f"[Processing] {Path(pdf_path).name}")
        print(f"{'='*70}")
        r = PaperResult(pdf_path=pdf_path, stem=stem)

        # Lookup BibTeX metadata
        bib_entry = find_bib_entry(stem, bib_meta) if bib_meta else None
        if bib_entry:
            print(f"  [BibTeX] Found: {bib_entry.get('title', '?')[:60]}")

        # --- Stage C: Conversion ---
        md_text = None
        t0 = time.time()

        # Try Docling first (unless --backend forces something)
        if args.backend in ("docling", "auto"):
            md_text, err = convert_docling(pdf_path, out_dir)
            if md_text:
                r.docling_ok = True
                r.backend_used = "docling"
                print(f"  [Docling] OK ({len(md_text)} chars)")
            else:
                r.error_log.append(f"Docling: {err}")
                print(f"  [Docling] FAIL: {err}")

        # Try VLM if docling failed or backend is vlm
        if md_text is None and args.backend in ("vlm", "auto") and has_vlm and client:
            md_text, err = convert_vlm(pdf_path, client, vlm_model)
            if md_text:
                r.vlm_ok = True
                r.backend_used = "vlm"
                print(f"  [VLM] OK ({len(md_text)} chars)")
            else:
                r.error_log.append(f"VLM: {err}")
                print(f"  [VLM] FAIL: {err}")

        # Try pdfminer as last resort
        if md_text is None and args.backend in ("pdfminer", "auto"):
            md_text, err = convert_pdfminer(pdf_path)
            if md_text:
                r.pdfminer_ok = True
                r.backend_used = "pdfminer"
                print(f"  [pdfminer] OK ({len(md_text)} chars)")
            else:
                r.error_log.append(f"pdfminer: {err}")
                print(f"  [pdfminer] FAIL: {err}")

        r.time_convert = time.time() - t0

        # Save markdown
        if md_text:
            # Prepend YAML header with metadata
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

            # --- Stage D: Chunking ---
            chunks = chunk_markdown(md_text)
            r.chunks_count = len(chunks)
            chunk_dir = os.path.join(out_dir, "chunks", stem)
            os.makedirs(chunk_dir, exist_ok=True)
            for ci, chunk in enumerate(chunks):
                Path(os.path.join(chunk_dir, f"chunk_{ci:03d}.md")).write_text(chunk)

            # Extract equations
            equations = extract_equations(md_text)
            r.equations_count = len(equations)
            if equations:
                eq_path = os.path.join(out_dir, "chunks", stem, "equations.md")
                eq_text = "\n\n".join([f"$${eq}$$" for eq in equations[:50]])
                Path(eq_path).write_text(f"# Equations from {stem}\n\n{eq_text}")
            print(f"  [Chunks] {r.chunks_count} chunks, {r.equations_count} equations")

            # --- Stage E: Summarization ---
            t1 = time.time()
            if has_text and client and not args.skip_summary:
                summary, err = summarize_paper(md_text, client, text_model)
                if summary:
                    r.summary_ok = True
                    sum_path = os.path.join(out_dir, "summaries", f"{stem}.md")
                    # Add YAML header
                    sum_header = "---\n"
                    sum_header += f'source: "{stem}"\n'
                    sum_header += f'source_pdf: "{pdf_path}"\n'
                    sum_header += "---\n\n"
                    Path(sum_path).write_text(sum_header + summary)
                    r.summary_path = sum_path
                    print(f"  [Summary] OK ({len(summary)} chars)")

                    # --- Stage G: Graph concepts ---
                    r.graph_concepts = extract_graph_concepts(summary)
                    print(f"  [Graph] {len(r.graph_concepts)} concepts: {r.graph_concepts[:5]}")
                else:
                    r.error_log.append(f"Summary: {err}")
                    print(f"  [Summary] FAIL: {err}")
            else:
                r.error_log.append("Summary: no text model available")
                print(f"  [Summary] SKIP (no text model)")
            r.time_summary = time.time() - t1

            # --- Stage F: Embeddings (optional, quick test) ---
            if has_embed and client and not args.skip_embed:
                # Embed the first 2000 chars as a test
                emb, err = embed_text(md_text[:2000], client, embed_model)
                if emb:
                    r.embedding_ok = True
                    print(f"  [Embed] OK (dim={len(emb)})")
                else:
                    r.error_log.append(f"Embed: {err}")
                    print(f"  [Embed] FAIL: {err}")
        else:
            r.error_log.append("All conversion backends failed")
            print(f"  [SKIP] No markdown generated, skipping downstream stages")

        results.append(r)

    # --- Report ---
    report = generate_report(results, out_dir)
    print(f"\n{'='*70}")
    print(report)

def main():
    parser = argparse.ArgumentParser(description="Paper processing pipeline: PDF -> Markdown -> Summary -> Graph")
    parser.add_argument("--pdf-dir",      default=DEFAULT_PDF_DIR,    help="Directory with PDF files")
    parser.add_argument("--out-dir",      default=DEFAULT_OUT_DIR,    help="Output directory")
    parser.add_argument("--limit",        type=int, default=3,        help="Max PDFs to process (0=all)")
    parser.add_argument("--backend",      choices=["docling","vlm","pdfminer","auto"], default="auto", help="Conversion backend")
    parser.add_argument("--vlm-model",    default=VLM_MODEL,          help="Vision model name in LM Studio")
    parser.add_argument("--text-model",   default=TEXT_MODEL,         help="Text model name in LM Studio")
    parser.add_argument("--embed-model",  default=EMBED_MODEL,        help="Embedding model name in LM Studio")
    parser.add_argument("--bibtex-path",  default=DEFAULT_BIBTEX,     help="Path to BibTeX file")
    parser.add_argument("--use-bibtex",   action="store_true", default=True, help="Use BibTeX metadata")
    parser.add_argument("--no-bibtex",    action="store_true",        help="Disable BibTeX")
    parser.add_argument("--skip-summary", action="store_true",        help="Skip summarization stage")
    parser.add_argument("--skip-embed",   action="store_true",        help="Skip embedding stage")
    parser.add_argument("--lmstudio-url", default=LMSTUDIO_BASE_URL,  help="LM Studio base URL")
    args = parser.parse_args()

    if args.no_bibtex:
        args.use_bibtex = False
    if args.limit == 0:
        args.limit = None

    run_pipeline(args)

if __name__ == "__main__":
    main()
