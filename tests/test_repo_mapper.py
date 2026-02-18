#!/usr/bin/env python3
"""
test_repo_mapper.py — CLI test script for the consolidated repo_mapper module.

Runs the full pipeline on a target repo (default: this AutoCrunchCoder repo)
and outputs all results to a shadow directory. Non-destructive.

Usage:
  source ~/venvs/ML/bin/activate
  python test_repo_mapper.py                              # defaults, no LLM
  python test_repo_mapper.py --use-llm --llm-backend lmstudio
  python test_repo_mapper.py --use-llm --llm-backend deepseek
  python test_repo_mapper.py --help
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add parent dir so we can import pyCruncher
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyCruncher.repo_mapper import (
    run_repo_mapper, discover_files, analyze_python_file,
    run_ctags_json, parse_ctags_json, generate_skeleton,
    git_file_stats, compute_folder_stats, generate_tech_matrix,
    tech_matrix_to_csv, generate_concept_map, generate_report,
    build_import_edges, RepoAnalysis, FileAnalysis, SymbolInfo,
)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
REPO_ROOT   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHADOW_BASE = os.path.join(REPO_ROOT, ".shadow")
DEEPSEEK_KEY_FILE = os.path.join(os.path.dirname(__file__), "deepseek.key")
LMSTUDIO_URL = "http://localhost:1234/v1"
LMSTUDIO_MODEL = "liquid/lfm2.5-1.2b"

def load_deepseek_key():
    if os.path.exists(DEEPSEEK_KEY_FILE):
        return Path(DEEPSEEK_KEY_FILE).read_text().strip()
    return ""

# ---------------------------------------------------------------------------
# Individual stage tests
# ---------------------------------------------------------------------------

def test_discovery(repo_root, max_files=None):
    """Test file discovery."""
    print("\n" + "="*60)
    print("[TEST] File Discovery")
    print("="*60)
    t0 = time.time()
    files = discover_files(repo_root, max_files=max_files)
    dt = time.time() - t0
    print(f"  Found {len(files)} files in {dt:.2f}s")
    # Show language breakdown
    lang_counts = {}
    for rel, absp, lang in files:
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
        print(f"    {lang}: {count}")
    return len(files) > 0, f"found {len(files)} files", dt

def test_python_ast(repo_root, max_files=5):
    """Test Python AST analysis."""
    print("\n" + "="*60)
    print("[TEST] Python AST Analysis")
    print("="*60)
    t0 = time.time()
    files = discover_files(repo_root, extensions={'.py'}, max_files=max_files)
    total_syms = 0
    total_classes = 0
    total_funcs = 0
    for rel, absp, lang in files:
        fa, syms = analyze_python_file(absp, rel)
        total_syms += len(syms)
        total_classes += len(fa.classes)
        total_funcs += len(fa.functions)
        print(f"  {rel}: {len(fa.classes)} classes, {len(fa.functions)} funcs, {len(fa.imports)} imports, {len(fa.errors)} errors")
    dt = time.time() - t0
    print(f"  Total: {total_syms} symbols, {total_classes} classes, {total_funcs} functions in {dt:.2f}s")
    return total_syms > 0, f"{total_syms} symbols from {len(files)} files", dt

def test_ctags(repo_root, shadow_dir):
    """Test ctags analysis."""
    print("\n" + "="*60)
    print("[TEST] Ctags C/C++ Analysis")
    print("="*60)
    t0 = time.time()
    ctags_file = os.path.join(shadow_dir, "test_ctags.json")
    ok = run_ctags_json(repo_root, ctags_file, exclude=['Build-*', 'build', '__pycache__', '.git', '.shadow'])
    if not ok:
        print("  [FAIL] ctags not available or failed")
        return False, "ctags not available", time.time() - t0
    cpp_files, cpp_syms = parse_ctags_json(ctags_file, repo_root)
    dt = time.time() - t0
    print(f"  Found {len(cpp_files)} C/C++ files, {len(cpp_syms)} symbols in {dt:.2f}s")
    for rel in sorted(cpp_files)[:5]:
        fa = cpp_files[rel]
        print(f"    {rel}: {len(fa.classes)} classes, {len(fa.functions)} funcs")
    return len(cpp_syms) > 0, f"{len(cpp_syms)} symbols from {len(cpp_files)} files", dt

def test_skeletons(repo_root, max_files=5):
    """Test skeleton generation."""
    print("\n" + "="*60)
    print("[TEST] Skeleton Generation")
    print("="*60)
    t0 = time.time()
    files = discover_files(repo_root, extensions={'.py'}, max_files=max_files)
    all_syms = []
    all_fas = []
    for rel, absp, lang in files:
        fa, syms = analyze_python_file(absp, rel)
        all_fas.append(fa)
        all_syms.extend(syms)
    skel_count = 0
    for fa in all_fas:
        skel = generate_skeleton(fa, all_syms)
        skel_count += 1
        lines = skel.count('\n')
        print(f"  {fa.rel_path}: skeleton {lines} lines")
    dt = time.time() - t0
    return skel_count > 0, f"{skel_count} skeletons", dt

def test_git(repo_root, max_files=5):
    """Test git metadata extraction."""
    print("\n" + "="*60)
    print("[TEST] Git Metadata")
    print("="*60)
    t0 = time.time()
    files = discover_files(repo_root, extensions={'.py'}, max_files=max_files)
    ok_count = 0
    for rel, absp, lang in files:
        stats = git_file_stats(repo_root, rel)
        has_data = bool(stats["last"])
        if has_data: ok_count += 1
        print(f"  {rel}: last={stats['last']}, first={stats['first']}, commits={stats['count']}")
    dt = time.time() - t0
    return ok_count > 0, f"git data for {ok_count}/{len(files)} files", dt

def test_llm_lmstudio(repo_root, shadow_dir, url=LMSTUDIO_URL, model=LMSTUDIO_MODEL):
    """Test LLM summarization via LM Studio."""
    print("\n" + "="*60)
    print(f"[TEST] LLM Summary (LM Studio: {url}, model: {model})")
    print("="*60)
    t0 = time.time()
    try:
        from openai import OpenAI
        client = OpenAI(base_url=url, api_key="not-needed")
        models = client.models.list()
        model_ids = [m.id for m in models.data]
        print(f"  Available models: {model_ids}")
    except Exception as e:
        print(f"  [FAIL] Cannot connect to LM Studio: {e}")
        return False, f"LM Studio unavailable: {e}", time.time() - t0

    # Pick one small Python file to summarize
    files = discover_files(repo_root, extensions={'.py'}, max_files=3)
    if not files:
        return False, "no Python files found", time.time() - t0
    
    rel, absp, lang = files[0]
    fa, syms = analyze_python_file(absp, rel)
    skel = generate_skeleton(fa, syms)
    
    from pyCruncher.repo_mapper import summarize_file_llm
    summary, err = summarize_file_llm(fa, skel, absp, client, model)
    dt = time.time() - t0
    if summary:
        print(f"  Summary for {rel} ({len(summary)} chars):")
        print(f"    {summary[:200]}...")
        return True, f"summary OK ({len(summary)} chars)", dt
    else:
        print(f"  [FAIL] {err}")
        return False, f"LLM failed: {err}", dt

def test_llm_deepseek(repo_root, shadow_dir):
    """Test LLM summarization via DeepSeek API."""
    print("\n" + "="*60)
    print("[TEST] LLM Summary (DeepSeek API)")
    print("="*60)
    t0 = time.time()
    key = load_deepseek_key()
    if not key:
        print("  [SKIP] No DeepSeek API key found")
        return False, "no API key", time.time() - t0

    files = discover_files(repo_root, extensions={'.py'}, max_files=3)
    if not files:
        return False, "no Python files found", time.time() - t0

    rel, absp, lang = files[0]
    fa, syms = analyze_python_file(absp, rel)
    skel = generate_skeleton(fa, syms)

    from pyCruncher.repo_mapper import summarize_file_deepseek
    summary, err = summarize_file_deepseek(fa, skel, absp, key)
    dt = time.time() - t0
    if summary:
        print(f"  Summary for {rel} ({len(summary)} chars):")
        print(f"    {summary[:200]}...")
        return True, f"summary OK ({len(summary)} chars)", dt
    else:
        print(f"  [FAIL] {err}")
        return False, f"DeepSeek failed: {err}", dt

def test_rollups(repo_root):
    """Test rollup generation (folder stats, tech matrix, concept map)."""
    print("\n" + "="*60)
    print("[TEST] Rollups (folder stats, tech matrix, concept map)")
    print("="*60)
    t0 = time.time()
    # Build a quick analysis
    analysis = RepoAnalysis(repo_root=repo_root, shadow_dir="", timestamp="")
    files = discover_files(repo_root, max_files=30)
    for rel, absp, lang in files:
        if lang == 'python':
            fa, syms = analyze_python_file(absp, rel)
        else:
            fa = FileAnalysis(rel_path=rel, language=lang)
            try:
                fa.size_bytes = os.path.getsize(absp)
                fa.line_count = sum(1 for _ in open(absp, errors='replace'))
            except: pass
        analysis.files[rel] = fa

    analysis.folder_stats = compute_folder_stats(analysis)
    matrix = generate_tech_matrix(analysis)
    csv = tech_matrix_to_csv(matrix)
    cmap = generate_concept_map(analysis)
    edges = build_import_edges(analysis)

    print(f"  Folders: {len(analysis.folder_stats)}")
    print(f"  Tech matrix rows: {len(matrix)}")
    print(f"  Concept map lines: {cmap.count(chr(10))}")
    print(f"  Import edges: {len(edges)}")
    dt = time.time() - t0
    return True, f"{len(analysis.folder_stats)} folders, {len(edges)} edges", dt

def test_full_pipeline(repo_root, shadow_dir, use_llm=False, llm_backend="lmstudio",
                       lmstudio_url=LMSTUDIO_URL, lmstudio_model=LMSTUDIO_MODEL,
                       max_files=None, max_llm_files=5):
    """Test the full pipeline end-to-end."""
    print("\n" + "="*60)
    print("[TEST] Full Pipeline")
    print("="*60)
    t0 = time.time()
    key = load_deepseek_key()
    analysis = run_repo_mapper(
        repo_root=repo_root,
        shadow_dir=shadow_dir,
        max_files=max_files,
        use_ctags=True,
        use_git=True,
        use_llm=use_llm,
        llm_backend=llm_backend,
        lmstudio_url=lmstudio_url,
        lmstudio_model=lmstudio_model,
        deepseek_key=key,
        max_llm_files=max_llm_files,
        verbose=True,
    )
    dt = time.time() - t0
    nfiles = len(analysis.files)
    nsyms = len(analysis.symbols)
    nsum = sum(1 for f in analysis.files.values() if f.summary_ok)
    ok = nfiles > 0
    return ok, f"{nfiles} files, {nsyms} symbols, {nsum} summaries, {dt:.1f}s", dt

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Test the consolidated repo_mapper module")
    parser.add_argument("--repo-root", default=REPO_ROOT, help="Repository root to analyze")
    parser.add_argument("--shadow-dir", default=None, help="Shadow output directory (auto-generated if not set)")
    parser.add_argument("--max-files", type=int, default=None, help="Limit number of files to analyze (0=all)")
    parser.add_argument("--max-llm-files", type=int, default=5, help="Max files to summarize with LLM")
    parser.add_argument("--use-llm", action="store_true", help="Enable LLM summarization")
    parser.add_argument("--llm-backend", choices=["lmstudio", "deepseek", "none"], default="lmstudio")
    parser.add_argument("--lmstudio-url", default=LMSTUDIO_URL, help="LM Studio API URL")
    parser.add_argument("--lmstudio-model", default=LMSTUDIO_MODEL, help="LM Studio model name")
    parser.add_argument("--skip-stages", nargs='*', default=[], help="Stages to skip: discovery ast ctags skeleton git llm_lm llm_ds rollups full")
    parser.add_argument("--only-full", action="store_true", help="Only run the full pipeline test")
    args = parser.parse_args()

    if args.max_files == 0: args.max_files = None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shadow_dir = args.shadow_dir or os.path.join(SHADOW_BASE, f"test_{timestamp}")
    os.makedirs(shadow_dir, exist_ok=True)

    print(f"[CONFIG] repo_root:  {args.repo_root}")
    print(f"[CONFIG] shadow_dir: {shadow_dir}")
    print(f"[CONFIG] max_files:  {args.max_files or 'all'}")
    print(f"[CONFIG] use_llm:    {args.use_llm}")
    print(f"[CONFIG] llm_backend: {args.llm_backend}")

    results = {}  # test_name -> (ok, detail, time)

    if args.only_full:
        results["full_pipeline"] = test_full_pipeline(
            args.repo_root, shadow_dir, use_llm=args.use_llm,
            llm_backend=args.llm_backend, lmstudio_url=args.lmstudio_url,
            lmstudio_model=args.lmstudio_model, max_files=args.max_files,
            max_llm_files=args.max_llm_files,
        )
    else:
        skip = set(args.skip_stages)

        if "discovery" not in skip:
            results["discovery"] = test_discovery(args.repo_root, max_files=args.max_files)

        if "ast" not in skip:
            results["python_ast"] = test_python_ast(args.repo_root, max_files=5)

        if "ctags" not in skip:
            results["ctags"] = test_ctags(args.repo_root, shadow_dir)

        if "skeleton" not in skip:
            results["skeletons"] = test_skeletons(args.repo_root, max_files=5)

        if "git" not in skip:
            results["git_metadata"] = test_git(args.repo_root, max_files=5)

        if "rollups" not in skip:
            results["rollups"] = test_rollups(args.repo_root)

        if "llm_lm" not in skip and args.use_llm and args.llm_backend == "lmstudio":
            results["llm_lmstudio"] = test_llm_lmstudio(args.repo_root, shadow_dir,
                                                          url=args.lmstudio_url, model=args.lmstudio_model)

        if "llm_ds" not in skip and args.use_llm and args.llm_backend == "deepseek":
            results["llm_deepseek"] = test_llm_deepseek(args.repo_root, shadow_dir)

        if "full" not in skip:
            results["full_pipeline"] = test_full_pipeline(
                args.repo_root, shadow_dir, use_llm=args.use_llm,
                llm_backend=args.llm_backend, lmstudio_url=args.lmstudio_url,
                lmstudio_model=args.lmstudio_model, max_files=args.max_files,
                max_llm_files=args.max_llm_files,
            )

    # --- Final summary table ---
    print("\n" + "="*70)
    print("FINAL RESULTS TABLE")
    print("="*70)
    print(f"{'Test':<20} {'Status':<8} {'Time':>7} {'Details'}")
    print("-"*70)
    for name, (ok, detail, dt) in results.items():
        status = "OK" if ok else "FAIL"
        print(f"{name:<20} {status:<8} {dt:>6.1f}s {detail}")
    print("-"*70)

    total_ok = sum(1 for ok, _, _ in results.values() if ok)
    total = len(results)
    print(f"\nPassed: {total_ok}/{total}")
    print(f"Shadow outputs: {shadow_dir}")

    # Write results to file
    report_path = os.path.join(shadow_dir, "test_results.md")
    with open(report_path, 'w') as f:
        f.write("# Repo Mapper Test Results\n\n")
        f.write(f"**Repo**: {args.repo_root}\n")
        f.write(f"**Timestamp**: {timestamp}\n")
        f.write(f"**Shadow**: {shadow_dir}\n\n")
        f.write("| Test | Status | Time | Details |\n")
        f.write("|------|--------|------|---------|\n")
        for name, (ok, detail, dt) in results.items():
            status = "OK" if ok else "FAIL"
            f.write(f"| {name} | {status} | {dt:.1f}s | {detail} |\n")
        f.write(f"\n**Passed: {total_ok}/{total}**\n")
    print(f"Results saved to: {report_path}")

if __name__ == "__main__":
    main()
