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
    postprocess_existing_run,
    refresh_metadata,
    run_paper_pipeline,
)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from pyCruncher.knowledge_graph import build_knowledge_graph
    from pyCruncher.vault_generator import generate_vault
except ImportError:
    build_knowledge_graph = None
    generate_vault = None


'''
## Run it like this:

source ~/venvs/ML/bin/activate
cd /home/prokop/git/AutoCrunchCoder/tests

source ~/venvs/ML/bin/activate
cd ~/git/AutoCrunchCoder/tests

python test_paper_pipeline.py --pdf-dir /home/prokop/Desktop/PAPERs --recursive --limit 10000 --backend docling --shadow --skip-summary --skip-embed

# Sumary exriting files using local LLM from LMstudio

python test_paper_pipeline.py  --postprocess-only --run-dir ./paper_pipeline_out/20260218_191049  --pdf-root /home/prokop/Desktop/PAPERs  --crossref-only --summarize-md --lmstudio-url http://10.26.201.142:1234/v1 --text-model phi-4 --limit 0


#Run overnight (do everything) with reset
python test_paper_pipeline.py --all-in-one --pdf-dir /home/prokop/Desktop/PAPERs/PAPERS_new --recursive --limit 0 --backend docling --out-dir /home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out --shadow --lmstudio-url http://10.26.201.142:1234/v1 --text-model phi-4 --embed-model text-embedding-nomic-embed-text-v1.5 --rename-plan --reset

# process new files in folder (keeping the old ones)
python test_paper_pipeline.py --all-in-one --pdf-dir /home/prokop/Desktop/PAPERs/PAPERS_new --recursive --limit 0 --backend docling --out-dir /home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out --shadow --lmstudio-url http://10.26.201.142:1234/v1 --text-model phi-4 --embed-model text-embedding-nomic-embed-text-v1.5 --rename-plan


'''

def main():
    parser = argparse.ArgumentParser(description="Paper processing pipeline: PDF -> Markdown -> Summary -> Graph")
    parser.add_argument("--postprocess-only", action="store_true", help="Postprocess an existing run dir (shadow tree, BibTeX/DOI, rename plan, SQLite DB)")
    parser.add_argument("--run-dir", default="", help="Existing run folder to postprocess (e.g. .../paper_pipeline_out/<stamp>)")
    parser.add_argument("--pdf-root", default="", help="Original PDF root directory (for shadow tree relative paths)")
    parser.add_argument("--mirror-root", default="", help="Shadow tree output folder (default: <run-dir>/shadow_tree)")
    parser.add_argument("--no-mirror", action="store_true", help="Disable shadow tree copying")
    parser.add_argument("--no-bibtex-pass", action="store_true", help="Disable DOI/BibTeX enrichment")
    parser.add_argument("--crossref-only", action="store_true", help="Skip pdf2doi lookup (including google searching) and only use existing DOI / DOI-from-markdown + CrossRef BibTeX")
    parser.add_argument("--summarize-md", action="store_true", help="Generate summaries for markdown files during postprocess")
    parser.add_argument("--refresh-only", action="store_true", help="Refresh metadata (summary/bib paths) from existing outputs and exit")
    parser.add_argument("--refresh-after", action="store_true", help="Run refresh after postprocess")
    parser.add_argument("--build-kg", action="store_true", help="Build Knowledge Graph (extract tags via LLM) for existing run")
    parser.add_argument("--build-vault", action="store_true", help="Build Markdown Vault from existing Knowledge Graph DB")
    parser.add_argument("--all-in-one", action="store_true", help="Run full pipeline sequentially: Docling, summaries, BibTeX/DOI, DB, KG, vault in one go")
    parser.add_argument("--reset", action="store_true", help="Clear the registry before starting (for testing from scratch)")
    parser.add_argument("--rename-plan", action="store_true", help="Generate rename plan (requires BibTeX)")
    parser.add_argument("--apply-rename", action="store_true", help="Apply rename plan by copying into <run-dir>/renamed (non-destructive)")
    parser.add_argument("--rename-template", default="{first_author}_{journal}_{year}_{short_title}", help="Rename base template (format vars: first_author,journal,year,title,short_title)")
    parser.add_argument("--db-path", default="", help="SQLite DB path (default: <run-dir>/papers.db)")
    parser.add_argument("--pdf-dir",      default=DEFAULT_PDF_DIR,    help="Directory with PDF files")
    parser.add_argument("--out-dir",      default=DEFAULT_OUT_DIR,    help="Output directory")
    parser.add_argument("--limit",        type=int, default=3,        help="Max PDFs to process (0=all)")
    parser.add_argument("--max-papers",   type=int, default=10000,    help="Hard cap on discovered PDFs (recursive mode), default 10000")
    parser.add_argument("--recursive",    action="store_true",        help="Discover PDFs recursively under --pdf-dir")
    parser.add_argument("--shadow",       action="store_true",        help="Write outputs into timestamped subfolder under --out-dir")
    parser.add_argument("--no-resume",    action="store_true",        help="Do not use processed registry; reprocess everything")
    parser.add_argument("--registry",     default="",                 help="Path to processed registry JSON (default: <out-dir>/processed_registry.json)")
    parser.add_argument("--clear-registry", action="store_true",     help="Delete the processed registry file before running (testing)" )
    parser.add_argument("--backend",      choices=["docling","vlm","pdfminer","auto"], default="auto", help="Conversion backend")
    parser.add_argument("--force-vlm",    action="store_true",        help="Force using LM Studio vision (VLM) OCR backend; skip docling/pdfminer")
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

    # Optional registry cleanup for testing
    registry_path = args.registry if args.registry else os.path.join(args.out_dir, "processed_registry.json")
    if args.clear_registry and os.path.exists(registry_path):
        try:
            os.remove(registry_path)
            print(f"[Registry] Cleared {registry_path}")
        except Exception as e:
            print(f"[Registry] Failed to clear {registry_path}: {e}")

    if args.postprocess_only:
        if not args.run_dir:
            raise RuntimeError("--postprocess-only requires --run-dir")
        if not args.pdf_root:
            raise RuntimeError("--postprocess-only requires --pdf-root (original PDF root for relpaths)")
        mirror_root = args.mirror_root if args.mirror_root else os.path.join(args.run_dir, "shadow_tree")
        postprocess_existing_run(
            run_dir=args.run_dir,
            pdf_root=args.pdf_root,
            mirror_root=mirror_root,
            do_mirror=(not args.no_mirror),
            do_bibtex=(not args.no_bibtex_pass),
            do_rename_plan=bool(args.rename_plan),
            apply_rename=bool(args.apply_rename),
            rename_template=args.rename_template,
            db_path=args.db_path,
            limit=args.limit,
            crossref_only=bool(args.crossref_only),
            do_summary=bool(args.summarize_md),
            lmstudio_url=args.lmstudio_url,
            text_model=args.text_model,
            do_refresh=bool(args.refresh_after),
        )
        if not args.refresh_after:
            return

    if args.refresh_only:
        if not args.run_dir:
            raise RuntimeError("--refresh-only requires --run-dir")
        if not args.pdf_root:
            raise RuntimeError("--refresh-only requires --pdf-root")
        if not (args.build_kg or args.build_vault):
            return

    if args.build_kg:
        if not args.run_dir:
            raise RuntimeError("--build-kg requires --run-dir")
        if not build_knowledge_graph:
            raise RuntimeError("Missing knowledge_graph module dependencies.")
        db_path = args.db_path if args.db_path else os.path.join(args.run_dir, "papers.db")
        build_knowledge_graph(
            run_dir=args.run_dir,
            db_path=db_path,
            lmstudio_url=args.lmstudio_url,
            model_name=args.text_model
        )
        if not args.build_vault:
            return
            
    if args.build_vault:
        if not args.run_dir:
            raise RuntimeError("--build-vault requires --run-dir")
        if not generate_vault:
            raise RuntimeError("Missing vault_generator module dependencies.")
        db_path = args.db_path if args.db_path else os.path.join(args.run_dir, "papers.db")
        vault_dir = os.path.join(args.run_dir, "vault")
        generate_vault(db_path=db_path, vault_dir=vault_dir)
        mirror_root = args.mirror_root if args.mirror_root else os.path.join(args.run_dir, "shadow_tree")
        refresh_metadata(
            run_dir=args.run_dir,
            pdf_root=args.pdf_root,
            mirror_root=mirror_root,
            registry_path=args.registry if args.registry else os.path.join(args.out_dir, "processed_registry.json"),
            report_path=os.path.join(args.run_dir, "report.json"),
            db_path=args.db_path,
        )
        return

    if args.all_in_one:
        # Optional reset of registry
        registry_path = args.registry if args.registry else os.path.join(args.out_dir, "processed_registry.json")
        if args.reset and os.path.exists(registry_path):
            os.remove(registry_path)
            print(f"[Reset] Removed registry: {registry_path}")

        # Run primary pipeline (Docling + summaries + embeds if enabled)
        cfg = PaperPipelineConfig(
            pdf_dir=args.pdf_dir,
            out_dir=args.out_dir,
            limit=None if args.limit == 0 else args.limit,
            max_papers=args.max_papers,
            recursive=args.recursive,
            shadow=args.shadow,
            resume=(not args.no_resume),
            backend=args.backend,
            force_vlm=args.force_vlm,
            vlm_model=args.vlm_model,
            text_model=args.text_model,
            embed_model=args.embed_model,
            bibtex_path=args.bibtex_path,
            use_bibtex=(args.use_bibtex and not args.no_bibtex_pass),
            skip_summary=args.skip_summary,
            skip_embed=args.skip_embed,
            lmstudio_url=args.lmstudio_url,
        )
        run_paper_pipeline(cfg)

        # Derive run_dir when shadow is enabled (latest timestamped folder under out_dir)
        if args.shadow:
            import glob
            candidates = []
            for p in glob.glob(os.path.join(args.out_dir, "*")):
                if not os.path.isdir(p):
                    continue
                base = os.path.basename(p)
                if base.startswith("20") and "_" in base:  # timestamped run
                    candidates.append((os.path.getmtime(p), p))
            if not candidates:
                raise RuntimeError("No run directory found after pipeline run (shadow mode).")
            candidates.sort()
            run_dir = candidates[-1][1]
        else:
            run_dir = args.out_dir

        # Postprocess: mirror, BibTeX/DOI, rename plan, summaries-from-md (for safety), refresh
        postprocess_existing_run(
            run_dir=run_dir,
            pdf_root=args.pdf_dir,
            mirror_root=os.path.join(run_dir, "shadow_tree"),
            do_mirror=(not args.no_mirror),
            do_bibtex=(not args.no_bibtex_pass),
            do_rename_plan=bool(args.rename_plan),
            apply_rename=bool(args.apply_rename),
            rename_template=args.rename_template,
            db_path=args.db_path if args.db_path else os.path.join(run_dir, "papers.db"),
            limit=None if args.limit == 0 else args.limit,
            crossref_only=bool(args.crossref_only),
            do_summary=bool(args.summarize_md),
            lmstudio_url=args.lmstudio_url,
            text_model=args.text_model,
            do_refresh=True,
        )

        # Build Knowledge Graph and Vault if modules available
        db_path_final = args.db_path if args.db_path else os.path.join(run_dir, "papers.db")
        if build_knowledge_graph:
            build_knowledge_graph(
                run_dir=run_dir,
                db_path=db_path_final,
                lmstudio_url=args.lmstudio_url,
                model_name=args.text_model,
            )
        if generate_vault:
            generate_vault(
                db_path=db_path_final,
                vault_dir=os.path.join(run_dir, "vault"),
            )
        return

    cfg = PaperPipelineConfig(
        pdf_dir=args.pdf_dir,
        out_dir=args.out_dir,
        limit=None if args.limit == 0 else args.limit,
        max_papers=args.max_papers,
        recursive=args.recursive,
        shadow=args.shadow,
        resume=(not args.no_resume),
        registry_path=registry_path if args.registry else "",
        backend=args.backend,
        force_vlm=args.force_vlm,
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
