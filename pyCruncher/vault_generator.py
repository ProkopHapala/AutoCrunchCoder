"""
Generate Obsidian-style knowledge vault pages from the paper database.

Uses Jinja2 templates to produce one Markdown note per topic, listing
associated papers with their essence summaries, authors, and file links.
The output is designed to be opened in Obsidian or any Markdown viewer
that supports `file://` links.

Non-obvious things:
- Links use `file://` URFs so clicking them in Obsidian opens the PDF or
  markdown directly from the shadow directory.
- The template handles missing fields gracefully (e.g. papers without
  BibTeX or without a year).
"""

import os
import sqlite3
from pathlib import Path
from jinja2 import Template

TOPIC_TEMPLATE = Template("""# Topic: {{ topic_name | title }}
**Category:** {{ category }}

## Associated Papers
{% for paper in papers %}
### {{ paper.title or paper.stem }}{% if paper.year %} ({{ paper.year }}){% endif %}
- **Essence:** {{ paper.essence or 'N/A' }}
- **Authors:** {{ paper.authors or 'N/A' }}
- **Links:** {% if paper.md_path %}[[Markdown]](file://{{ paper.md_path }}){% endif %}{% if paper.shadow_pdf_path %} | [[PDF (shadow)]](file://{{ paper.shadow_pdf_path }}){% elif paper.original_pdf_path %} | [[PDF]](file://{{ paper.original_pdf_path }}){% endif %}
{% if paper.bibtex_path %}- **BibTeX:** [[.bib]](file://{{ paper.bibtex_path }}){% endif %}

{% endfor %}
""")

MASTER_TEMPLATE = Template("""# Master Library Index

{% for category, tags in categories.items() %}
## {{ category | title }}
{% for tag in tags %}
- [{{ tag.name | title }}](Topic_{{ tag.name | replace(' ', '_') | replace('/', '_') }}.md) ({{ tag.count }} papers)
{% endfor %}
{% endfor %}
""")

def generate_vault(db_path: str, vault_dir: str):
    if not os.path.exists(db_path):
        print(f"[Vault] DB not found at {db_path}")
        return
        
    os.makedirs(vault_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute('''
        SELECT t.id, t.name, t.category, COUNT(at.article_id) as cnt
        FROM tags t
        JOIN article_tags at ON t.id = at.tag_id
        GROUP BY t.id
        HAVING cnt > 0
        ORDER BY t.category, cnt DESC
    ''')
    tags = cur.fetchall()
    
    categories = {}
    for t in tags:
        cat = t['category'] or 'uncategorized'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({'name': t['name'], 'count': t['cnt']})
        
        cur.execute('''
            SELECT p.stem, p.title, p.year, p.authors, p.essence, p.md_path, p.shadow_pdf_path, p.original_pdf_path, p.bibtex_path
            FROM papers p
            JOIN article_tags at ON p.stem = at.article_id
            WHERE at.tag_id = ?
            ORDER BY p.year DESC
        ''', (t['id'],))
        papers = cur.fetchall()
        
        md_content = TOPIC_TEMPLATE.render(
            topic_name=t['name'],
            category=cat,
            papers=papers
        )
        safe_name = str(t['name']).replace(' ', '_').replace('/', '_')
        Path(os.path.join(vault_dir, f"Topic_{safe_name}.md")).write_text(md_content, encoding='utf-8')
        
    master_md = MASTER_TEMPLATE.render(categories=categories)
    Path(os.path.join(vault_dir, "Master_Index.md")).write_text(master_md, encoding='utf-8')
    
    conn.close()
    print(f"[Vault] Generated vault in {vault_dir} with {len(tags)} topic files and a Master Index.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        generate_vault(sys.argv[1], sys.argv[2])
