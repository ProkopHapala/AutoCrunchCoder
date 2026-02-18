#!/usr/bin/env python3
"""
repo_mapper.py — Consolidated code analysis & documentation tool.

Combines ctags, Python AST, git history, and optional LLM summarization
to produce a non-destructive "shadow" analysis of a repository.

All outputs go to a shadow directory; source repo is never modified.
"""

import os
import re
import ast
import json
import time
import glob
import subprocess
import fnmatch
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Set

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SymbolInfo:
    name: str
    kind: str              # "class", "function", "method", "member", "module"
    file_path: str         # relative to repo root
    line: int = 0
    end_line: int = 0
    scope: str = ""        # parent class/namespace
    signature: str = ""
    language: str = ""     # "python", "cpp", "h", etc.

@dataclass
class FileAnalysis:
    rel_path: str
    language: str = ""
    size_bytes: int = 0
    line_count: int = 0
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    symbols_count: int = 0
    skeleton: str = ""
    summary: str = ""
    summary_ok: bool = False
    git_last_touched: str = ""
    git_commits: int = 0
    git_first_date: str = ""
    errors: List[str] = field(default_factory=list)

@dataclass 
class RepoAnalysis:
    repo_root: str
    shadow_dir: str
    timestamp: str
    files: Dict[str, FileAnalysis] = field(default_factory=dict)
    symbols: Dict[str, SymbolInfo] = field(default_factory=dict)
    import_edges: List[tuple] = field(default_factory=list)   # (from_file, to_module)
    call_edges: List[tuple] = field(default_factory=list)     # (caller, callee)
    folder_stats: Dict[str, dict] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

LANG_MAP = {
    '.py': 'python', '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
    '.h': 'cpp_header', '.hpp': 'cpp_header', '.c': 'c',
    '.js': 'javascript', '.ts': 'typescript', '.jl': 'julia',
    '.f90': 'fortran', '.f': 'fortran', '.cl': 'opencl',
    '.cu': 'cuda', '.md': 'markdown', '.toml': 'toml',
    '.json': 'json', '.sh': 'shell',
}

DEFAULT_CODE_EXTS = {'.py', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.c', '.js', '.ts', '.jl', '.f90', '.cl', '.cu'}

DEFAULT_IGNORES = {
    '*/__pycache__/*', '*/.git/*', '*/node_modules/*', '*/.venv/*',
    '*/venvs/*', '*/.shadow/*', '*/build/*', '*.pyc', '*.so', '*.o',
    '*/.aider*', '*/Build-*/*',
}

def discover_files(repo_root, extensions=None, ignores=None, max_files=None):
    """Walk repo, return list of (rel_path, abs_path, lang) tuples."""
    if extensions is None: extensions = DEFAULT_CODE_EXTS
    if ignores is None: ignores = DEFAULT_IGNORES
    results = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        # prune ignored dirs
        dirnames[:] = [d for d in dirnames if not any(fnmatch.fnmatch(os.path.join(dirpath, d), p) for p in ignores)]
        for fname in sorted(filenames):
            full = os.path.join(dirpath, fname)
            if any(fnmatch.fnmatch(full, p) for p in ignores):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in extensions:
                continue
            rel = os.path.relpath(full, repo_root)
            lang = LANG_MAP.get(ext, 'unknown')
            results.append((rel, full, lang))
            if max_files and len(results) >= max_files:
                return results
    return results

# ---------------------------------------------------------------------------
# Python AST analysis (stdlib, no tree-sitter needed)
# ---------------------------------------------------------------------------

def analyze_python_file(abs_path, rel_path):
    """Parse a Python file with stdlib ast. Returns FileAnalysis + list of SymbolInfo."""
    fa = FileAnalysis(rel_path=rel_path, language='python')
    symbols = []
    try:
        content = Path(abs_path).read_text(errors='replace')
        fa.size_bytes = len(content.encode('utf-8', errors='replace'))
        fa.line_count = content.count('\n') + 1
        tree = ast.parse(content, filename=abs_path)
    except Exception as e:
        fa.errors.append(f"AST parse: {e}")
        return fa, symbols

    # Collect method names inside classes first, then add top-level functions
    method_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            fa.classes.append(node.name)
            symbols.append(SymbolInfo(name=node.name, kind='class', file_path=rel_path, line=node.lineno, language='python'))
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qname = f"{node.name}.{item.name}"
                    fa.functions.append(qname)
                    sig = _py_func_sig(item)
                    symbols.append(SymbolInfo(name=item.name, kind='method', file_path=rel_path, line=item.lineno, scope=node.name, signature=sig, language='python'))
                    method_nodes.add(id(item))
    # Top-level functions (only direct children of module)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and id(node) not in method_nodes:
            fa.functions.append(node.name)
            sig = _py_func_sig(node)
            symbols.append(SymbolInfo(name=node.name, kind='function', file_path=rel_path, line=node.lineno, signature=sig, language='python'))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                fa.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ''
            for alias in node.names:
                fa.imports.append(f"{mod}.{alias.name}")
    # Also catch imports inside if __name__ blocks etc.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and node not in ast.iter_child_nodes(tree):
            for alias in node.names:
                if alias.name not in fa.imports: fa.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node not in ast.iter_child_nodes(tree):
            mod = node.module or ''
            for alias in node.names:
                imp = f"{mod}.{alias.name}"
                if imp not in fa.imports: fa.imports.append(imp)

    fa.symbols_count = len(symbols)
    return fa, symbols

def _py_func_sig(node):
    """Extract a simple signature string from an ast.FunctionDef."""
    args = []
    for a in node.args.args:
        args.append(a.arg)
    return f"({', '.join(args)})"

# ---------------------------------------------------------------------------
# C/C++ analysis via ctags (subprocess)
# ---------------------------------------------------------------------------

def run_ctags_json(repo_root, output_file, languages='C++,C', exclude=None):
    """Run universal-ctags and produce JSON output. Returns True on success."""
    cmd = [
        'ctags', '-R',
        f'--languages={languages}',
        '--output-format=json',
        '--fields=+cniKSE',
        '--extras=+qrFS',
        '--excmd=number',
    ]
    if exclude:
        for ex in exclude:
            cmd.append(f'--exclude={ex}')
    cmd += ['-o', output_file, repo_root]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception as e:
        print(f"[ctags] Error: {e}")
        return False

def parse_ctags_json(json_file, repo_root):
    """Parse ctags JSON and return dict of {rel_path: FileAnalysis} and list of SymbolInfo."""
    files = {}
    symbols = []
    if not os.path.exists(json_file):
        return files, symbols
    with open(json_file, 'r') as f:
        for line in f:
            if not line.startswith('{"_type": "tag"'):
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            name = entry.get('name', '')
            if '__anon' in name:
                continue
            kind = entry.get('kind', '')
            path = entry.get('path', '')
            rel = os.path.relpath(path, repo_root) if os.path.isabs(path) else path
            il = entry.get('line', 0)
            scope = entry.get('scope', '')
            sig = entry.get('signature', '')
            ext = os.path.splitext(rel)[1].lower()
            lang = LANG_MAP.get(ext, 'cpp')

            if rel not in files:
                fa = FileAnalysis(rel_path=rel, language=lang)
                try:
                    fa.size_bytes = os.path.getsize(path)
                    fa.line_count = sum(1 for _ in open(path, errors='replace'))
                except:
                    pass
                files[rel] = fa

            si = SymbolInfo(name=name, kind=kind, file_path=rel, line=il, scope=scope, signature=sig, language=lang)
            symbols.append(si)

            if kind in ('class', 'struct'):
                files[rel].classes.append(name)
            elif kind == 'function':
                qname = f"{scope}::{name}" if scope else name
                files[rel].functions.append(qname)

    for rel, fa in files.items():
        fa.symbols_count = sum(1 for s in symbols if s.file_path == rel)
    return files, symbols

# ---------------------------------------------------------------------------
# Skeleton generation (pure text, no LLM)
# ---------------------------------------------------------------------------

def generate_skeleton(fa, symbols_list):
    """Generate a concise text skeleton for a file."""
    lines = [f"# {fa.rel_path}", f"Language: {fa.language} | Lines: {fa.line_count} | Symbols: {fa.symbols_count}", ""]
    file_syms = [s for s in symbols_list if s.file_path == fa.rel_path]
    classes = [s for s in file_syms if s.kind in ('class', 'struct')]
    funcs = [s for s in file_syms if s.kind == 'function']
    methods = [s for s in file_syms if s.kind == 'method']
    members = [s for s in file_syms if s.kind == 'member']
    if classes:
        lines.append("## Classes")
        for c in classes:
            lines.append(f"- **{c.name}** (line {c.line})")
            cls_methods = [m for m in methods if m.scope == c.name]
            cls_members = [m for m in members if m.scope == c.name]
            for m in cls_members:
                lines.append(f"  - `{m.name}` (member, line {m.line})")
            for m in cls_methods:
                lines.append(f"  - `{m.name}{m.signature}` (method, line {m.line})")
    if funcs:
        lines.append("## Functions")
        for f in funcs:
            lines.append(f"- `{f.name}{f.signature}` (line {f.line})")
    if fa.imports:
        lines.append("## Imports")
        for imp in fa.imports[:30]:
            lines.append(f"- {imp}")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Git metadata extraction
# ---------------------------------------------------------------------------

def git_file_stats(repo_root, rel_path):
    """Get git stats for a file. Returns (last_date, first_date, commit_count)."""
    full = os.path.join(repo_root, rel_path)
    stats = {"last": "", "first": "", "count": 0}
    try:
        r = subprocess.run(['git', 'log', '-1', '--format=%cd', '--date=short', rel_path],
                           capture_output=True, text=True, cwd=repo_root, timeout=10)
        stats["last"] = r.stdout.strip()
        r = subprocess.run(['git', 'log', '--diff-filter=A', '--format=%cd', '--date=short', '-1', rel_path],
                           capture_output=True, text=True, cwd=repo_root, timeout=10)
        stats["first"] = r.stdout.strip()
        r = subprocess.run(['git', 'rev-list', '--count', 'HEAD', '--', rel_path],
                           capture_output=True, text=True, cwd=repo_root, timeout=10)
        stats["count"] = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
    except Exception:
        pass
    return stats

# ---------------------------------------------------------------------------
# LLM summarization (OpenAI-compatible API)
# ---------------------------------------------------------------------------

SUMMARY_PROMPT_TEMPLATE = """Analyze this source code file and provide a concise summary:
- Purpose: what does this file/module do?
- Key classes/functions and their roles
- Dependencies and connections to other modules

Keep the summary under 200 words. Be specific about algorithms or domain concepts.

File: {rel_path}
Language: {language}

Code skeleton:
{skeleton}

First 100 lines of code:
```
{head}
```
"""

def summarize_file_llm(fa, skeleton, abs_path, client, model, max_head_chars=4000):
    """Summarize a file using an OpenAI-compatible LLM. Returns (summary_text, error_or_None)."""
    try:
        head = Path(abs_path).read_text(errors='replace')[:max_head_chars]
    except:
        head = "(could not read)"
    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        rel_path=fa.rel_path, language=fa.language,
        skeleton=skeleton[:2000], head=head
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=512,
        )
        return response.choices[0].message.content, None
    except Exception as e:
        return None, str(e)

def summarize_file_deepseek(fa, skeleton, abs_path, api_key, max_head_chars=4000):
    """Summarize using DeepSeek API directly via requests."""
    import requests
    try:
        head = Path(abs_path).read_text(errors='replace')[:max_head_chars]
    except:
        head = "(could not read)"
    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        rel_path=fa.rel_path, language=fa.language,
        skeleton=skeleton[:2000], head=head
    )
    try:
        r = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.2, "max_tokens": 512},
            timeout=60,
        )
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content'], None
        else:
            return None, f"DeepSeek HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return None, str(e)

# ---------------------------------------------------------------------------
# Rollup: folder summary, concept map, tech matrix
# ---------------------------------------------------------------------------

def compute_folder_stats(analysis):
    """Compute per-folder statistics."""
    stats = {}
    for rel, fa in analysis.files.items():
        folder = os.path.dirname(rel) or '.'
        if folder not in stats:
            stats[folder] = {'files': 0, 'lines': 0, 'symbols': 0, 'classes': 0, 'functions': 0, 'languages': set()}
        s = stats[folder]
        s['files'] += 1
        s['lines'] += fa.line_count
        s['symbols'] += fa.symbols_count
        s['classes'] += len(fa.classes)
        s['functions'] += len(fa.functions)
        s['languages'].add(fa.language)
    # convert sets to lists for JSON
    for k in stats:
        stats[k]['languages'] = sorted(stats[k]['languages'])
    return stats

def generate_tech_matrix(analysis):
    """Generate a technology matrix: folder x language counts."""
    matrix = {}
    for rel, fa in analysis.files.items():
        folder = os.path.dirname(rel) or '.'
        if folder not in matrix:
            matrix[folder] = {}
        lang = fa.language
        matrix[folder][lang] = matrix[folder].get(lang, 0) + 1
    return matrix

def tech_matrix_to_csv(matrix):
    """Convert tech matrix dict to CSV string."""
    all_langs = sorted({lang for row in matrix.values() for lang in row})
    lines = ["folder," + ",".join(all_langs)]
    for folder in sorted(matrix):
        counts = [str(matrix[folder].get(l, 0)) for l in all_langs]
        lines.append(f"{folder},{','.join(counts)}")
    return "\n".join(lines)

def generate_concept_map(analysis):
    """Generate a simple concept map markdown grouping files by folder."""
    lines = ["# Concept Map\n"]
    folders = {}
    for rel, fa in analysis.files.items():
        folder = os.path.dirname(rel) or '.'
        if folder not in folders:
            folders[folder] = []
        status = "summarized" if fa.summary_ok else "skeleton-only"
        git_info = f"last: {fa.git_last_touched}, commits: {fa.git_commits}" if fa.git_last_touched else "no git info"
        folders[folder].append(f"  - `{os.path.basename(rel)}` [{fa.language}] ({status}) — {git_info}")
    for folder in sorted(folders):
        lines.append(f"## {folder}/")
        lines.extend(folders[folder])
        lines.append("")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Graph edges
# ---------------------------------------------------------------------------

def build_import_edges(analysis):
    """Build file->module import edges from Python analysis."""
    edges = []
    for rel, fa in analysis.files.items():
        for imp in fa.imports:
            edges.append((rel, imp))
    return edges

# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(analysis):
    """Generate a markdown report."""
    lines = [f"# Repo Mapper Report", f"**Repo**: {analysis.repo_root}", f"**Timestamp**: {analysis.timestamp}", ""]

    # Summary stats
    nfiles = len(analysis.files)
    nsyms = len(analysis.symbols)
    nsum = sum(1 for f in analysis.files.values() if f.summary_ok)
    nerr = sum(len(f.errors) for f in analysis.files.values())
    lines.append("## Summary Statistics")
    lines.append(f"- Files analyzed: {nfiles}")
    lines.append(f"- Total symbols: {nsyms}")
    lines.append(f"- Files summarized (LLM): {nsum}/{nfiles}")
    lines.append(f"- Total errors: {nerr}")
    lines.append("")

    # File table
    lines.append("## Files")
    lines.append("| File | Lang | Lines | Symbols | Classes | Functions | Summary | Git Last | Commits | Errors |")
    lines.append("|------|------|-------|---------|---------|-----------|---------|----------|---------|--------|")
    for rel in sorted(analysis.files):
        fa = analysis.files[rel]
        summ = "OK" if fa.summary_ok else "-"
        errs = "; ".join(fa.errors[:2]) if fa.errors else "-"
        if len(errs) > 40: errs = errs[:37] + "..."
        lines.append(f"| {rel} | {fa.language} | {fa.line_count} | {fa.symbols_count} | {len(fa.classes)} | {len(fa.functions)} | {summ} | {fa.git_last_touched} | {fa.git_commits} | {errs} |")

    # Folder stats
    lines.append("\n## Folder Statistics")
    for folder, stats in sorted(analysis.folder_stats.items()):
        lines.append(f"- **{folder}/**: {stats['files']} files, {stats['lines']} lines, {stats['symbols']} symbols, langs: {stats['languages']}")

    # Errors
    if analysis.errors:
        lines.append("\n## Global Errors")
        for e in analysis.errors:
            lines.append(f"- {e}")

    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_repo_mapper(
    repo_root,
    shadow_dir=None,
    extensions=None,
    ignores=None,
    max_files=None,
    use_ctags=True,
    use_git=True,
    use_llm=False,
    llm_backend="lmstudio",    # "lmstudio", "deepseek", or "none"
    lmstudio_url="http://localhost:1234/v1",
    lmstudio_model="liquid/lfm2.5-1.2b",
    deepseek_key="",
    max_llm_files=10,
    verbose=True,
):
    """Run the full repo mapping pipeline. Returns RepoAnalysis."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if shadow_dir is None:
        shadow_dir = os.path.join(repo_root, ".shadow", timestamp)
    os.makedirs(shadow_dir, exist_ok=True)

    analysis = RepoAnalysis(repo_root=repo_root, shadow_dir=shadow_dir, timestamp=timestamp)

    if verbose: print(f"\n{'='*70}\n[RepoMapper] repo={repo_root} shadow={shadow_dir}\n{'='*70}")

    # --- Stage 1: Discover files ---
    if verbose: print("\n[Stage 1] Discovering files...")
    file_list = discover_files(repo_root, extensions=extensions, ignores=ignores, max_files=max_files)
    if verbose: print(f"  Found {len(file_list)} files")

    # --- Stage 2: Python AST analysis ---
    if verbose: print("\n[Stage 2] Python AST analysis...")
    py_count = 0
    for rel, absp, lang in file_list:
        if lang == 'python':
            fa, syms = analyze_python_file(absp, rel)
            analysis.files[rel] = fa
            for s in syms:
                analysis.symbols[f"{rel}::{s.name}"] = s
            py_count += 1
    if verbose: print(f"  Analyzed {py_count} Python files")

    # --- Stage 3: Ctags for C/C++ ---
    ctags_ok = False
    if use_ctags:
        if verbose: print("\n[Stage 3] Running ctags...")
        ctags_file = os.path.join(shadow_dir, "ctags_output.json")
        ctags_ok = run_ctags_json(repo_root, ctags_file, languages='C++,C', exclude=['Build-*', 'build', '__pycache__', '.git'])
        if ctags_ok:
            cpp_files, cpp_syms = parse_ctags_json(ctags_file, repo_root)
            for rel, fa in cpp_files.items():
                if rel not in analysis.files:
                    analysis.files[rel] = fa
                else:
                    # merge ctags data into existing
                    existing = analysis.files[rel]
                    existing.classes.extend(fa.classes)
                    existing.functions.extend(fa.functions)
                    existing.symbols_count += fa.symbols_count
            for s in cpp_syms:
                analysis.symbols[f"{s.file_path}::{s.scope}::{s.name}"] = s
            if verbose: print(f"  ctags found {len(cpp_files)} C/C++ files, {len(cpp_syms)} symbols")
        else:
            analysis.errors.append("ctags failed or not installed")
            if verbose: print("  [WARN] ctags failed")
    else:
        if verbose: print("\n[Stage 3] ctags SKIPPED")

    # Also add non-python, non-ctags files to analysis (e.g. .js, .jl, .md)
    for rel, absp, lang in file_list:
        if rel not in analysis.files:
            fa = FileAnalysis(rel_path=rel, language=lang)
            try:
                fa.size_bytes = os.path.getsize(absp)
                fa.line_count = sum(1 for _ in open(absp, errors='replace'))
            except:
                pass
            analysis.files[rel] = fa

    # --- Stage 4: Skeletons ---
    if verbose: print("\n[Stage 4] Generating skeletons...")
    skel_dir = os.path.join(shadow_dir, "skeletons")
    os.makedirs(skel_dir, exist_ok=True)
    all_syms = list(analysis.symbols.values())
    for rel, fa in analysis.files.items():
        skeleton = generate_skeleton(fa, all_syms)
        fa.skeleton = skeleton
        skel_path = os.path.join(skel_dir, rel + ".skeleton.md")
        os.makedirs(os.path.dirname(skel_path), exist_ok=True)
        Path(skel_path).write_text(skeleton)
    if verbose: print(f"  Generated {len(analysis.files)} skeletons")

    # --- Stage 5: Git metadata ---
    if use_git:
        if verbose: print("\n[Stage 5] Extracting git metadata...")
        git_count = 0
        for rel, fa in analysis.files.items():
            stats = git_file_stats(repo_root, rel)
            fa.git_last_touched = stats["last"]
            fa.git_first_date = stats["first"]
            fa.git_commits = stats["count"]
            git_count += 1
        if verbose: print(f"  Got git stats for {git_count} files")
    else:
        if verbose: print("\n[Stage 5] Git metadata SKIPPED")

    # --- Stage 6: LLM Summarization ---
    if use_llm and llm_backend != "none":
        if verbose: print(f"\n[Stage 6] LLM summarization (backend={llm_backend}, max={max_llm_files})...")
        llm_ok = 0
        llm_fail = 0
        sum_dir = os.path.join(shadow_dir, "summaries")
        os.makedirs(sum_dir, exist_ok=True)

        client = None
        if llm_backend == "lmstudio":
            try:
                from openai import OpenAI
                client = OpenAI(base_url=lmstudio_url, api_key="not-needed")
                # quick check
                client.models.list()
            except Exception as e:
                analysis.errors.append(f"LM Studio connection failed: {e}")
                client = None
                if verbose: print(f"  [WARN] LM Studio not available: {e}")

        # Sort files by size (smallest first) for faster feedback
        sorted_files = sorted(analysis.files.items(), key=lambda x: x[1].size_bytes)
        count = 0
        for rel, fa in sorted_files:
            if count >= max_llm_files:
                break
            if fa.language in ('markdown', 'json', 'toml', 'shell'):
                continue  # skip non-code files
            count += 1
            abs_path = os.path.join(repo_root, rel)
            summary = None
            err = None

            if llm_backend == "lmstudio" and client:
                summary, err = summarize_file_llm(fa, fa.skeleton, abs_path, client, lmstudio_model)
            elif llm_backend == "deepseek" and deepseek_key:
                summary, err = summarize_file_deepseek(fa, fa.skeleton, abs_path, deepseek_key)
            else:
                err = f"No LLM backend available (backend={llm_backend})"

            if summary:
                fa.summary = summary
                fa.summary_ok = True
                llm_ok += 1
                sum_path = os.path.join(sum_dir, rel + ".summary.md")
                os.makedirs(os.path.dirname(sum_path), exist_ok=True)
                Path(sum_path).write_text(f"# Summary: {rel}\n\n{summary}")
            else:
                fa.errors.append(f"LLM: {err}")
                llm_fail += 1
            if verbose: print(f"  [{count}/{max_llm_files}] {rel}: {'OK' if summary else 'FAIL'}")
        if verbose: print(f"  Summarized: {llm_ok} OK, {llm_fail} FAIL")
    else:
        if verbose: print("\n[Stage 6] LLM summarization SKIPPED")

    # --- Stage 7: Rollups ---
    if verbose: print("\n[Stage 7] Computing rollups...")
    analysis.folder_stats = compute_folder_stats(analysis)
    analysis.import_edges = build_import_edges(analysis)

    # Tech matrix CSV
    matrix = generate_tech_matrix(analysis)
    csv_text = tech_matrix_to_csv(matrix)
    rollup_dir = os.path.join(shadow_dir, "rollups")
    os.makedirs(rollup_dir, exist_ok=True)
    Path(os.path.join(rollup_dir, "tech_matrix.csv")).write_text(csv_text)

    # Concept map
    cmap = generate_concept_map(analysis)
    Path(os.path.join(rollup_dir, "concept_map.md")).write_text(cmap)

    # Import edges TSV
    graph_dir = os.path.join(shadow_dir, "graphs")
    os.makedirs(graph_dir, exist_ok=True)
    with open(os.path.join(graph_dir, "import_edges.tsv"), 'w') as f:
        f.write("from_file\tto_module\n")
        for src, dst in analysis.import_edges:
            f.write(f"{src}\t{dst}\n")

    # Symbols JSON
    syms_json = {k: asdict(v) for k, v in analysis.symbols.items()}
    Path(os.path.join(graph_dir, "symbols.json")).write_text(json.dumps(syms_json, indent=1, default=str))

    if verbose: print(f"  Folders: {len(analysis.folder_stats)}, Import edges: {len(analysis.import_edges)}")

    # --- Stage 8: Report ---
    if verbose: print("\n[Stage 8] Generating report...")
    report_md = generate_report(analysis)
    Path(os.path.join(shadow_dir, "report.md")).write_text(report_md)

    # Also save full analysis as JSON (without huge text fields)
    report_json = {
        "repo_root": analysis.repo_root,
        "shadow_dir": analysis.shadow_dir,
        "timestamp": analysis.timestamp,
        "file_count": len(analysis.files),
        "symbol_count": len(analysis.symbols),
        "import_edge_count": len(analysis.import_edges),
        "folder_stats": analysis.folder_stats,
        "errors": analysis.errors,
        "files": {rel: {"language": fa.language, "lines": fa.line_count, "symbols": fa.symbols_count,
                        "classes": fa.classes, "functions": fa.functions[:20],
                        "summary_ok": fa.summary_ok, "git_last": fa.git_last_touched,
                        "git_commits": fa.git_commits, "errors": fa.errors}
                  for rel, fa in analysis.files.items()},
    }
    Path(os.path.join(shadow_dir, "report.json")).write_text(json.dumps(report_json, indent=2, default=str))

    if verbose:
        print(f"\n{'='*70}")
        print(f"[DONE] Shadow outputs in: {shadow_dir}")
        print(f"  Files: {len(analysis.files)}, Symbols: {len(analysis.symbols)}")
        print(f"  Summaries: {sum(1 for f in analysis.files.values() if f.summary_ok)}/{len(analysis.files)}")
        print(f"  Errors: {len(analysis.errors)} global + {sum(len(f.errors) for f in analysis.files.values())} per-file")
        print(f"{'='*70}\n")

    return analysis
