import sqlite3
import re
import argparse
from typing import Dict, List

DB_PATH = "/home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/consolidated.db"

# Mapping of a normalized parent tag name to a list of regex patterns or exact substrings
# to match and consolidate. The key becomes the new unified tag.
CONSOLIDATION_RULES = {
    "atomic force microscopy (afm)": [
        r"atomic force microscop",
        r"\bafm\b",
        r"noncontact atomic force microscopy",
        r"nc-afm"
    ],
    "scanning tunneling microscopy (stm)": [
        r"scanning tunneling microscop",
        r"\bstm\b"
    ],
    "density functional theory (dft)": [
        r"density functional theory",
        r"\bdft\b"
    ],
    "machine learning": [
        r"machine learning",
        r"deep learning",
        r"neural network",
        r"reinforcement learning"
    ],
    "molecular dynamics (md)": [
        r"molecular dynamics",
        r"\bmd simulations?\b"
    ]
}

def consolidate_tags(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 1. Get all tags
    cur.execute("SELECT id, name, category FROM tags")
    tags = [dict(r) for r in cur.fetchall()]
    
    changes_made = 0
    
    for unified_name, patterns in CONSOLIDATION_RULES.items():
        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Find all matching tags
        matching_tags = []
        for tag in tags:
            if tag["name"] == unified_name:
                continue
                
            for p in compiled_patterns:
                if p.search(tag["name"]):
                    matching_tags.append(tag)
                    break
                    
        if not matching_tags:
            continue
            
        print(f"Consolidating into '{unified_name}': {[t['name'] for t in matching_tags]}")
        
        # Ensure unified tag exists
        cur.execute("SELECT id FROM tags WHERE name = ?", (unified_name,))
        unified_row = cur.fetchone()
        if not unified_row:
            cur.execute("INSERT INTO tags (name, category) VALUES (?, ?)", (unified_name, "consolidated"))
            unified_id = cur.lastrowid
        else:
            unified_id = unified_row["id"]
            
        # Move article_tags to the unified tag
        for old_tag in matching_tags:
            old_id = old_tag["id"]
            
            # Find articles with the old tag
            cur.execute("SELECT article_id FROM article_tags WHERE tag_id = ?", (old_id,))
            articles = [r["article_id"] for r in cur.fetchall()]
            
            for article_id in articles:
                # Insert the unified tag for this article (IGNORE if it already has it)
                cur.execute("INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)", (article_id, unified_id))
                
            # Delete old mappings
            cur.execute("DELETE FROM article_tags WHERE tag_id = ?", (old_id,))
            
            # Delete old tag
            cur.execute("DELETE FROM tags WHERE id = ?", (old_id,))
            changes_made += 1
            
    conn.commit()
    conn.close()
    
    print(f"Tag consolidation complete. Merged/removed {changes_made} redundant tags.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolidate redundant tags in the database.")
    parser.add_argument("--db", default=DB_PATH, help="Path to consolidated.db")
    args = parser.parse_args()
    consolidate_tags(args.db)
