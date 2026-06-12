import os
import sqlite3
import glob
from pathlib import Path
from typing import Dict, Any

def repair_pdf_path(path: str) -> str:
    if not path:
        return path
    if os.path.exists(path):
        return path
    
    # Repair logic: if it was in PAPERs/ but now moved to PAPERs/PAPERS_old/
    # (Note: make sure not to replace PAPERS_new if it's already there)
    if path.startswith("/home/prokop/Desktop/PAPERs/") and not path.startswith("/home/prokop/Desktop/PAPERs/PAPERS_old/") and not path.startswith("/home/prokop/Desktop/PAPERs/PAPERS_new/"):
        alt_path = path.replace("/home/prokop/Desktop/PAPERs/", "/home/prokop/Desktop/PAPERs/PAPERS_old/")
        if os.path.exists(alt_path):
            return alt_path
            
    return path

def consolidate(base_dir: str, out_db_path: str):
    db_files = sorted(glob.glob(os.path.join(base_dir, "20*", "papers.db")))
    print(f"Found {len(db_files)} database files to consolidate.")
    
    merged_papers = {}
    merged_tags = {}      # name.lower() -> dict
    merged_article_tags = set() # (stem, tag_name_lower)
    
    for db_path in db_files:
        run_name = os.path.basename(os.path.dirname(db_path))
        print(f"Processing {run_name}...")
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # 1. Load papers
            cur.execute("SELECT * FROM papers")
            for row in cur.fetchall():
                p = dict(row)
                stem = p["stem"]
                
                # Path repair
                p["original_pdf_path"] = repair_pdf_path(p.get("original_pdf_path", ""))
                p["shadow_pdf_path"] = repair_pdf_path(p.get("shadow_pdf_path", ""))
                p["run_name"] = run_name # Keep track of provenance
                
                # Conflict resolution: prefer newer run (since db_files is sorted lexicographically by timestamp)
                # We can just overwrite. Or check timestamp. 
                if stem not in merged_papers:
                    merged_papers[stem] = p
                else:
                    # overwrite because we process older to newer (sorted by run folder name)
                    merged_papers[stem] = p
            
            # 2. Load tags
            cur.execute("SELECT * FROM tags")
            tag_id_to_name = {}
            for row in cur.fetchall():
                t = dict(row)
                name = t["name"].lower()
                tag_id_to_name[t["id"]] = name
                if name not in merged_tags:
                    merged_tags[name] = t
                else:
                    # Prefer newer category if it was updated
                    if t.get("category"):
                        merged_tags[name]["category"] = t["category"]
            
            # 3. Load article_tags
            cur.execute("SELECT * FROM article_tags")
            for row in cur.fetchall():
                article_id = row["article_id"]
                tag_id = row["tag_id"]
                tag_name = tag_id_to_name.get(tag_id)
                if tag_name:
                    merged_article_tags.add((article_id, tag_name))
                    
            conn.close()
        except Exception as e:
            print(f"Error processing {db_path}: {e}")

    # Write to consolidated DB
    if os.path.exists(out_db_path):
        os.remove(out_db_path)
        
    print(f"\nWriting consolidated DB to {out_db_path}...")
    out_conn = sqlite3.connect(out_db_path)
    out_cur = out_conn.cursor()
    
    out_cur.executescript('''
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_pdf_path TEXT,
            stem TEXT UNIQUE,
            doi TEXT,
            bibtex_ok INTEGER,
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
            timestamp TEXT,
            essence TEXT,
            run_name TEXT
        );
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            category TEXT
        );
        CREATE TABLE IF NOT EXISTS article_tags (
            article_id TEXT,
            tag_id INTEGER,
            FOREIGN KEY(tag_id) REFERENCES tags(id),
            UNIQUE(article_id, tag_id)
        );
    ''')
    
    # Insert papers
    paper_cols = ["original_pdf_path", "stem", "doi", "bibtex_ok", "bibtex_path", "bibtex_error", 
                  "bibtex_text", "title", "authors", "year", "journal", "keywords", "shadow_md_path", 
                  "shadow_pdf_path", "rename_target_md", "rename_target_pdf", "md_path", "timestamp", "essence", "run_name"]
    
    for stem, p in merged_papers.items():
        vals = tuple(p.get(c) for c in paper_cols)
        placeholders = ",".join(["?"] * len(paper_cols))
        out_cur.execute(f"INSERT INTO papers ({','.join(paper_cols)}) VALUES ({placeholders})", vals)
        
    # Insert tags
    tag_name_to_new_id = {}
    for name, t in merged_tags.items():
        out_cur.execute("INSERT INTO tags (name, category) VALUES (?, ?)", (name, t.get("category")))
        tag_name_to_new_id[name] = out_cur.lastrowid
        
    # Insert article_tags
    for article_id, tag_name in merged_article_tags:
        # Only add tag if paper actually exists in our merged papers
        if article_id in merged_papers:
            tag_id = tag_name_to_new_id[tag_name]
            out_cur.execute("INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)", (article_id, tag_id))
            
    out_conn.commit()
    out_conn.close()
    
    print(f"Done! Merged {len(merged_papers)} papers and {len(merged_tags)} tags.")

if __name__ == "__main__":
    base_dir = "/home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out"
    out_db = os.path.join(base_dir, "consolidated.db")
    consolidate(base_dir, out_db)
