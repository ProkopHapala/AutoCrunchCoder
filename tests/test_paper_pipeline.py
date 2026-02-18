#!/usr/bin/env python3
"""Lightweight CLI wrapper for the paper processing pipeline.

The implementation lives in `pyCruncher.paper_pipeline` so it can be reused from
other scripts/modules.
"""

import argparse
import os
import sys

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from pyCruncher.paper_pipeline import (
    DEFAULT_BIBTEX,
    DEFAULT_EMBED_MODEL,
    DEFAULT_LMSTUDIO_BASE_URL,
    DEFAULT_OUT_DIR,
    DEFAULT_PDF_DIR,
    DEFAULT_TEXT_MODEL,
    DEFAULT_VLM_MODEL,
    PaperPipelineConfig,
    run_paper_pipeline,
)

def main():
    parser = argparse.ArgumentParser(description="Paper processing pipeline: PDF -> Markdown -> Summary -> Graph")
    parser.add_argument("--pdf-dir",      default=DEFAULT_PDF_DIR,    help="Directory with PDF files")
    parser.add_argument("--out-dir",      default=DEFAULT_OUT_DIR,    help="Output directory")
    parser.add_argument("--limit",        type=int, default=3,        help="Max PDFs to process (0=all)")
    parser.add_argument("--backend",      choices=["docling","vlm","pdfminer","auto"], default="auto", help="Conversion backend")
    parser.add_argument("--vlm-model",    default=DEFAULT_VLM_MODEL,  help="Vision model name in LM Studio")
    parser.add_argument("--text-model",   default=DEFAULT_TEXT_MODEL, help="Text model name in LM Studio")
    parser.add_argument("--embed-model",  default=DEFAULT_EMBED_MODEL,help="Embedding model name in LM Studio")
    parser.add_argument("--bibtex-path",  default=DEFAULT_BIBTEX,     help="Path to BibTeX file")
    parser.add_argument("--use-bibtex",   action="store_true", default=True, help="Use BibTeX metadata")
    parser.add_argument("--no-bibtex",    action="store_true",        help="Disable BibTeX")
    parser.add_argument("--skip-summary", action="store_true",        help="Skip summarization stage")
    parser.add_argument("--skip-embed",   action="store_true",        help="Skip embedding stage")
    parser.add_argument("--lmstudio-url", default=DEFAULT_LMSTUDIO_BASE_URL, help="LM Studio base URL")
    args = parser.parse_args()

    if args.no_bibtex:
        args.use_bibtex = False
    if args.limit == 0:
        args.limit = None

    cfg = PaperPipelineConfig(
        pdf_dir=args.pdf_dir,
        out_dir=args.out_dir,
        limit=None if args.limit == 0 else args.limit,
        backend=args.backend,
        vlm_model=args.vlm_model,
        text_model=args.text_model,
        embed_model=args.embed_model,
        bibtex_path=args.bibtex_path,
        use_bibtex=(args.use_bibtex and not args.no_bibtex),
        skip_summary=args.skip_summary,
        skip_embed=args.skip_embed,
        lmstudio_url=args.lmstudio_url,
    )

    run_paper_pipeline(cfg)

if __name__ == "__main__":
    main()
