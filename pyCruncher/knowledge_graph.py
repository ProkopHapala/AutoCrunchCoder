"""
Knowledge graph builder — tags scientific articles with structured metadata.

After the paper pipeline produces summaries, this module asks an LLM to
classify each article along four axes: scientific domains, mathematical
structures, numerical solvers, and data structures. The tags are stored in
SQLite alongside the paper database.

Non-obvious things:
- `ArticleMetadata` is a pydantic model — the LLM is asked to produce JSON
  matching this schema, which pydantic validates.
- The SQLite schema adds an `essence` column to the existing `papers` table
  (migration-safe: `ALTER TABLE ... ADD COLUMN` with try/except).
- Tags are deduplicated by name in the `tags` table; articles reference them
  via `article_tags` junction.
"""

import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
import pydantic
from openai import OpenAI
from pathlib import Path

class ArticleMetadata(pydantic.BaseModel):
    essence_summary: str = pydantic.Field(description="A concise 1-2 sentence summary of the core essence and contribution of the paper.")
    domains: List[str] = pydantic.Field(description="List of broad scientific domains (e.g., 'Fluid Dynamics', 'Quantum Chemistry', 'Game Physics'). Keep to 1-3.")
    math_classes: List[str] = pydantic.Field(description="Underlying mathematical equations or structures (e.g., 'Poisson Equation', 'N-Body Hamiltonian', 'Eigenvalue Problem').")
    solvers: List[str] = pydantic.Field(description="Algorithms or numerical solvers used (e.g., 'Conjugate Gradient', 'Monte Carlo', 'Runge-Kutta').")
    data_structures: List[str] = pydantic.Field(description="Key data structures or discretizations (e.g., 'Sparse Matrix', 'Octree', 'Finite Element', 'SPH').")

def init_kg_db(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            category TEXT -- 'domain', 'math_class', 'solver', 'data_structure'
        );
        CREATE TABLE IF NOT EXISTS article_tags (
            article_id TEXT, -- corresponds to stem
            tag_id INTEGER,
            FOREIGN KEY(tag_id) REFERENCES tags(id),
            UNIQUE(article_id, tag_id)
        );
    ''')
    
    # Check if 'essence' column exists in 'papers', add if not
    cur.execute("PRAGMA table_info(papers)")
    columns = [col[1] for col in cur.fetchall()]
    if 'essence' not in columns:
        try:
            cur.execute("ALTER TABLE papers ADD COLUMN essence TEXT")
        except Exception as e:
            print(f"[KG] Warning adding essence column: {e}")
            
    conn.commit()
    return conn

def extract_summary_sections(md_path: str) -> str:
    try:
        content = Path(md_path).read_text(encoding='utf-8')
    except Exception:
        return ""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    return content

def build_knowledge_graph(run_dir: str, db_path: str, lmstudio_url: str, model_name: str):
    rep_path = os.path.join(run_dir, "report.json")
    if not os.path.exists(rep_path):
        print(f"[KG] No report.json found in {run_dir}")
        return
    
    try:
        report = json.loads(Path(rep_path).read_text())
    except Exception as e:
        print(f"[KG] Error reading report.json: {e}")
        return

    conn = init_kg_db(db_path)
    cur = conn.cursor()
    
    client = OpenAI(base_url=lmstudio_url, api_key="lm-studio")
    schema = ArticleMetadata.model_json_schema()

    count = 0
    for item in report:
        stem = item.get("stem")
        summary_path = item.get("summary_path")
        if not summary_path or not os.path.exists(summary_path):
            continue
            
        cur.execute("SELECT COUNT(*) FROM article_tags WHERE article_id=?", (stem,))
        if cur.fetchone()[0] > 0:
            print(f"[KG] Skipping {stem} (already in graph)")
            continue
            
        print(f"[KG] Processing {stem}...")
        text_content = extract_summary_sections(summary_path)
        if not text_content:
            print(f"[KG]   -> No summary content")
            continue
            
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an expert computational scientist. Extract structured taxonomies from the given paper summary."},
                    {"role": "user", "content": text_content},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "ArticleMetadata",
                        "schema": schema,
                        "strict": True,
                    },
                },
            )
            content = resp.choices[0].message.content if resp.choices else ""
            metadata = ArticleMetadata.model_validate_json(content) if content else None
        except Exception as e:
            print(f"[KG] LLM Extraction failed for {stem}: {e}")
            continue
        if metadata is None:
            print(f"[KG] No metadata returned for {stem}")
            continue

        all_tags = []
        for d in metadata.domains: all_tags.append((d.strip(), 'domain'))
        for m in metadata.math_classes: all_tags.append((m.strip(), 'math_class'))
        for s in metadata.solvers: all_tags.append((s.strip(), 'solver'))
        for ds in metadata.data_structures: all_tags.append((ds.strip(), 'data_structure'))
        
        for tag_name, category in all_tags:
            if not tag_name: continue
            tag_name_lower = tag_name.lower()
            cur.execute("INSERT OR IGNORE INTO tags (name, category) VALUES (?, ?)", (tag_name_lower, category))
            cur.execute("SELECT id FROM tags WHERE name=?", (tag_name_lower,))
            row = cur.fetchone()
            if row:
                tag_id = row[0]
                cur.execute("INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)", (stem, tag_id))
            
        cur.execute("UPDATE papers SET essence=? WHERE stem=?", (metadata.essence_summary, stem))
        conn.commit()
        count += 1
        print(f"  -> Extracted {len(all_tags)} tags.")
        
    conn.close()
    print(f"[KG] Finished building Knowledge Graph. Processed {count} new summaries.")

