https://chatgpt.com/share/6a5df267-d580-83eb-b257-c682e0e42fa2

# USER

I want to make local paper database, can you help me with defining the desing, I do not know so much about available toools I have no experience with databases, RAG, MCP and these things, I'm chemist and physics, I understan numerical math but not so much this. Read my desing goals and specifications, and brainsotrm how you can help me and improve the desing, respect my specific goals, but find better tool to achive it, extract the esence of what I want. 

I give you tentative desing document (quite long and detailed) and link to repo where we started to implement it together with some othr AI related tools

https://github.com/ProkopHapala/AutoCrunchCoder
https://deepwiki.com/ProkopHapala/AutoCrunchCoder

---

# Chat GPT 5.6 sol hi

## My overall diagnosis

Your design is **fundamentally good**, and it already identifies the right goal:

> not merely a paper database, but a local scientific knowledge base that converts papers into reliable, machine-usable knowledge for both you and coding agents. 

The most important realization is that **database, RAG, embeddings, tags, and MCP are not the product**. They are interchangeable supporting mechanisms.

The actual product is:

> **A local scientific-paper compiler and retrieval system.**

It should:

1. Discover and identify papers without disturbing your folders.
2. Compile PDFs into structured scientific representations.
3. Preserve provenance back to exact pages, sections, equations, and figures.
4. Search and assemble a compact, trustworthy context package.
5. Deliver that package to a human or coding agent.

That is more precise than “second brain” and much more precise than “RAG database.”

# 1. What is already strong in your design

Several decisions should be retained almost unchanged.

### Non-destructive ownership

Paperdb must not own or reorganize the PDFs. It indexes them and maintains derived information separately. That is exactly right for your manually curated library. 

### SQLite rather than a large database server

For a few thousand papers, SQLite is not merely adequate; it is probably the best choice:

* one inspectable file;
* trivial backup;
* no daemon;
* excellent transactions;
* built-in FTS5 keyword search;
* usable directly from Python, CLI, GUI, and MCP.

SQLite FTS5 already provides BM25 ranking, highlighted matches, and relevant snippets, so the first useful system does not require a vector database. ([sqlite.org][1])

### CLI and MCP as the primary interfaces

This is also correct. GUI-first development would consume much effort without improving the scientific core. Your actual workflow is:

```text
scientific problem
    ↓
find papers and relevant sections
    ↓
assemble equations, algorithms, assumptions, and evidence
    ↓
give this context to an LLM coding or writing agent
```

MCP is appropriate because it standardizes functions and resources exposed to agents; tools can also return resource links rather than dumping everything into a single response. ([Model Context Protocol][2])

### Reusing pyCruncher.Agent

Your repository already has the multi-provider abstraction, while the current paper pipeline still contains hardcoded LM Studio defaults and paths. Moving the paper system behind `pyCruncher.Agent` is the right consolidation.

### Reusing existing processing

You have hundreds of useful Docling conversions, summaries, tags, BibTeX records, and embeddings. These should become imported historical artifacts, not be thrown away and regenerated.

# 2. The main conceptual problem: “paper” currently means too many things

The most important schema improvement is to separate four entities that your current design partially conflates.

## A. Scientific work

The intellectual object:

* journal article;
* arXiv preprint;
* conference paper;
* book chapter.

Example:

```text
"Extended Position Based Dynamics"
```

Identifiers may include DOI, arXiv ID, PMID, Semantic Scholar ID, or a manually generated identity.

## B. Document version

A particular scientific version of that work:

* arXiv v1;
* arXiv v3;
* accepted manuscript;
* final journal version;
* supporting information.

The arXiv and final journal versions may contain different equations, numbering, appendices, or corrected algorithms.

## C. File

A particular byte sequence:

```text
SHA-256 = a39b...
```

Two identical copies in Mendeley and `PAPERs_new` are one file with two locations.

## D. File location

A pathname where a copy currently exists:

```text
/home/prokop/Desktop/PAPERs/...
/home/prokop/Mendeley Desktop/...
```

A file can move without changing its identity.

Your proposed `UNIQUE(content_hash)` in `papers` treats an exact PDF file as the paper itself.  That works for duplicates, but fails for:

* arXiv versus journal versions;
* revised PDFs;
* publisher PDFs with different front matter;
* supplementary documents;
* the same paper downloaded from two sources with slightly different bytes.

The current implementation has the opposite weakness: it uses `original_pdf_path` as the unique database key and uses the filename stem in tag relations and FTS maintenance.  The knowledge-graph tables likewise use `stem` as `article_id`.

Neither path nor stem should be an identity.

## Better core model

```sql
works
    id
    title
    year
    journal
    canonical_doi
    ...

work_identifiers
    work_id
    scheme          -- doi, arxiv, pmid, isbn, manual
    value

documents
    id
    work_id
    version_kind    -- arxiv, accepted, publisher, supplement
    version_label
    publication_date

files
    id
    document_id
    sha256
    size_bytes
    page_count

file_locations
    file_id
    path
    first_seen_at
    last_seen_at
    is_preferred
    exists_now
```

This structure solves deduplication and versioning cleanly.

For your scale, compute the **full SHA-256**. Hashing only the first 10 kB, as proposed in the notes, is a useful quick fingerprint but not a reliable content identity. A full hash of a few thousand PDFs is inexpensive and only needs to be recalculated when size or modification time changes.

Also, “most recently seen path” should not automatically become the primary path. Use either:

* an explicit preferred path;
* folder priority rules;
* or simply retain all valid locations.

# 3. Derived information should be versioned artifacts, not columns and booleans

Your proposed `paper_state` table has flags such as:

```text
summary_done
equations_extracted
embeddings_done
```

This initially looks simple, but becomes ambiguous very quickly:

* Which parser produced the markdown?
* Which version of Docling?
* Was formula enrichment enabled?
* Which summary prompt?
* Which model?
* Is the old result still valid after the PDF changed?
* Are there two summaries, one local and one Gemini?
* Was an extraction successful but low quality?

The `summaries` table already moves in the correct direction by storing model and prompt versions. The same idea should be generalized to **all processing outputs**.

## Artifact model

```sql
artifacts
    id
    document_id
    source_file_id
    kind                 -- markdown, parser_json, summary, equations,
                         -- algorithms, chunks, embeddings, topic_review
    producer             -- docling, mineru, llm, legacy_pdfminer
    producer_version
    config_json
    config_hash
    model_name
    prompt_version
    status               -- pending, running, ok, partial, failed, superseded
    quality_score
    output_path
    created_at
    error_message
```

An artifact is reproducible if its identity depends on:

```text
artifact_key =
hash(
    source_file_sha256,
    operation,
    producer,
    producer_version,
    configuration,
    model,
    prompt_version
)
```

This gives you automatic incremental processing:

* if an equivalent artifact already exists, skip it;
* if the prompt changes, generate a new summary;
* if Docling changes, preserve both conversions;
* if a file changes, its dependent artifacts become stale;
* migration outputs can be retained as `legacy_docling`, `legacy_pdfminer`, etc.

Then `paperdb status` does not ask whether a Boolean is true. It asks:

> Is there a current successful artifact of the requested kind for this document?

This is substantially more robust.

# 4. Keep both human-readable files and machine provenance

You correctly rejected a purely hash-named cache because you want to browse Markdown manually. But filenames based only on paper title or PDF stem will collide.

A useful compromise is:

```text
~/paperdb/
├── papers.db
├── papers/
│   ├── Macklin_2016_XPBD--p0042/
│   │   ├── paper.md
│   │   ├── summary.md
│   │   ├── equations.md
│   │   ├── algorithms.md
│   │   └── metadata.yaml
│   └── ...
├── artifacts/
│   ├── a8/7c/a87c.../
│   │   ├── docling.json
│   │   ├── extraction.log
│   │   └── parser_config.json
├── topic_reviews/
├── exports/
└── logs/
```

The `papers/` directory is human-facing.

The `artifacts/` directory is internal, immutable, and provenance-focused.

The short stable suffix such as `--p0042` prevents collisions even when titles or citekeys match.

Do not mirror the complete original folder tree into the Markdown tree. That reproduces the organizational fragmentation you are trying to overcome. Original folder organization remains visible through database metadata and search filters.

# 5. Treat PDF extraction as compilation, not one conversion function

You should not choose one global PDF parser and assume it is correct for every paper.

A better analogy is a compiler pipeline:

```text
PDF
 ↓
layout and source representation
 ↓
scientific blocks
 ↓
normalized Markdown
 ↓
equations / figures / algorithms / references
 ↓
search units and summaries
```

## Recommended parser strategy

### Primary parser: Docling

Docling already gives you:

* a structured document model;
* Markdown and lossless structured serialization;
* layout and reading-order information;
* tables;
* optional formula understanding that emits LaTeX.

Formula enrichment is an explicit additional stage and is disabled by default because it adds processing cost. ([Docling Project][3])

For paperdb, save both:

```text
docling.json       # canonical structured parser output
paper.md           # convenient human/LLM rendering
```

Markdown alone throws away useful structure.

### Supplemental parser: GROBID

Use GROBID primarily for:

* bibliographic header extraction;
* author/affiliation structure;
* references;
* citation callouts;
* section hierarchy;
* citation graph construction.

GROBID is designed to restructure scholarly PDFs into TEI XML and is especially strong at bibliographic and logical scholarly structure. Equations and chemical formulas are among the harder PDF elements, so I would not use GROBID as the authoritative LaTeX extractor. ([grobid.readthedocs.io][4])

### Selective fallback: MinerU or Marker

For papers where Docling fails equation/layout quality, run another backend only on the problematic document or pages.

MinerU currently provides Markdown, JSON, formula-to-LaTeX conversion, layout visualizations, and local CPU/GPU operation. ([GitHub][5])

Marker also exposes page/block JSON with explicit equation and inline-math blocks, but its code is GPL and its model weights have additional usage conditions. That is not necessarily a problem for your personal research system, but it should be treated as an optional backend rather than quietly becoming a core dependency. ([GitHub][6])

## Do not decide parser quality by reputation

Build a small benchmark of perhaps:

* 10 ordinary born-digital chemistry papers;
* 10 equation-heavy physics/numerical-method papers;
* 5 older or scanned papers;
* 5 papers with complex tables, pseudocode, or two-column equations.

Measure:

* reading order;
* heading hierarchy;
* missing text;
* equation detection;
* equation-symbol correctness;
* equation numbering;
* table structure;
* source-page localization.

A recent document-RAG evaluation found that hierarchical splitting and metadata quality could matter more than the parser choice, and that a naïve knowledge graph underperformed simpler retrieval. Its corpus was not scientific papers, so this is not direct evidence for your domain, but it strongly supports building your own representative evaluation rather than chasing fashionable architecture. ([arXiv][7])

# 6. Equation extraction needs source fidelity, not merely LaTeX text

Your equation table is a good start, but I would extend it substantially:

```sql
equations
    id
    document_id
    artifact_id
    latex_raw
    latex_normalized
    equation_number
    section_id
    page_number
    bbox_json
    context_before
    context_after
    parser
    confidence
    verification_status
```

The distinction between `latex_raw` and `latex_normalized` is important:

* `latex_raw`: what the parser actually extracted;
* `latex_normalized`: optional cleanup by an LLM or symbolic parser.

Never overwrite the raw extraction.

Also store the equation image crop or enough bounding-box information to regenerate it. Then a GUI or CLI can show:

```text
PDF crop  ↔  extracted LaTeX
```

A visual render comparison can flag suspicious equations:

1. crop the equation from the PDF;
2. render the extracted LaTeX;
3. compare them visually;
4. send low-confidence cases to manual or VLM review.

It will not prove mathematical equivalence, but it is excellent for detecting missing superscripts, indices, delimiters, and symbols.

For coding-agent use, variable definitions should not be attached blindly to an isolated equation. Store them as separate evidence-bearing records:

```text
symbol: λ
meaning: compliance parameter
source: page 4, paragraph after Eq. (7)
```

# 7. “Algorithm extraction” should become method cards

Most scientific papers do not contain complete executable pseudocode. An LLM often reconstructs an algorithm by combining equations, prose, figure captions, and assumptions.

Therefore distinguish:

```text
source_algorithm
    actual algorithm block or numbered procedure in paper

reconstructed_method
    LLM interpretation assembled from multiple source passages
```

A useful method card would contain:

```text
Name
Purpose
Physical/mathematical assumptions
State variables
Inputs
Outputs
Core equations
Initialization
Iteration/update steps
Boundary conditions
Convergence or stopping criterion
Complexity
Parallelization opportunities
Known approximations
Source passages
Extraction type: verbatim | parsed | reconstructed
Confidence
```

This is much more valuable for your scientific coding workflow than a generic `steps_json`.

Crucially, every reconstructed field should refer back to one or more source units. That lets a coding agent distinguish:

> “The paper explicitly says this”

from:

> “The extraction model inferred this implementation sequence.”

# 8. The central output should be a **context pack**

Your current design emphasizes:

```bash
paperdb get <paper> --format all
```

But giving an agent several complete papers is often wasteful and can reduce answer quality.

The core operation should instead be:

```bash
paperdb context \
    "stable GPU broad-phase collision using uniform grids without atomics" \
    --budget 24000 \
    --include equations,algorithms,assumptions \
    --out context.md
```

The output would contain:

```text
Query and constraints

Paper 1
  bibliographic identity
  why it was selected
  relevant sections
  equations
  method card
  source locations

Paper 2
  ...

Comparison matrix
  method
  complexity
  memory structure
  synchronization
  limitations

Bibliography
```

This directly implements your real goal: quickly gather context from multiple papers for an LLM coding or writing agent. 

## Retrieval should be hierarchical

Do not search all chunks as an undifferentiated bag.

Use two levels:

```text
1. Select relevant papers
   metadata + title + summary + tags + full-text FTS

2. Select relevant units inside those papers
   sections + paragraphs + equations + algorithms
```

This avoids returning twelve neighboring chunks from one paper while missing other important methods.

# 9. RAG explained without the jargon

For this system, RAG is simply:

```text
search
+ select trustworthy excerpts
+ provide them to an LLM
```

It does **not** necessarily mean:

* LangChain;
* LlamaIndex;
* Chroma;
* a knowledge graph;
* a conversational chatbot;
* a special database.

## Phase 1: FTS5

Start with exact and lexical search.

This is particularly important in your domain because terms such as:

```text
XPBD
SIBFA
DFTB3
HLLC
M06-2X
Ewald
Slater–Koster
```

are often better matched lexically than semantically.

## Phase 2: optional vector retrieval

Embeddings help when the query and paper use different language:

```text
"atom-local rotational degrees of freedom"
```

versus:

```text
"oriented interaction sites attached to rigid particles"
```

At your scale, I would avoid a separate Chroma or Qdrant service initially. A small SQLite extension such as `sqlite-vec` can keep embeddings in the same database. However, it remains pre-v1 and explicitly warns that interfaces can change, so pin the version and hide it behind your own `VectorIndex` interface. ([GitHub][8])

A robust hybrid score can be implemented later with reciprocal-rank fusion:

[
S(d)=
\frac{w_{\mathrm{FTS}}}{k+r_{\mathrm{FTS}}(d)}
+
\frac{w_{\mathrm{vec}}}{k+r_{\mathrm{vec}}(d)}
]

No large RAG framework is required.

# 10. Your “knowledge graph” is currently a taxonomy

The existing `knowledge_graph.py` extracts four lists:

* domains;
* math classes;
* solvers;
* data structures.

That is useful, but it is not yet really a graph; it is typed tagging. The implementation itself stores tags and an article-tag junction table.

I would rename this subsystem internally to:

```text
taxonomy
```

A genuine scientific graph would later contain relations such as:

```text
paper USES solver
paper EXTENDS method
paper COMPARES_WITH paper
equation DEFINES variable
algorithm USES equation
method APPROXIMATES physical_model
paper CITES paper
```

Do not build this now. Typed tags are enough for the first version.

## Preserve raw tag assertions

The current cleanup script deletes old tags after moving their associations to a merged tag.  That loses useful provenance.

Use:

```sql
canonical_tags
tag_aliases
tag_assertions
```

where an assertion records:

```text
paper_id
raw_tag
canonical_tag_id
category
source              -- llm, user, mendeley, imported
model
prompt_version
confidence
created_at
```

Thus:

```text
"DFT"
"density-functional theory"
"density functional theory (dft)"
```

can all resolve to one canonical concept without destroying their original forms.

# 11. Improve the MCP design around tasks, not database tables

The current MCP prototype searches two tag categories and extracts sections from summary Markdown by looking for headings.  It demonstrates the connection but is too fragile for the final system.

A better read-only MCP surface would be:

```text
search_papers(query, filters, limit)
inspect_paper(paper_id)
retrieve_context(query, token_budget, filters)
get_source_unit(unit_id)
get_equation(equation_id)
get_method_card(method_id)
compare_methods(query, constraints)
trace_provenance(object_id)
list_collections()
database_status()
```

Resources:

```text
paperdb://work/{id}
paperdb://document/{id}/markdown
paperdb://document/{id}/summary
paperdb://equation/{id}
paperdb://method/{id}
paperdb://context/{id}
```

Tools should normally return compact structured results plus resource links, rather than several hundred kilobytes of Markdown.

Keep mutating tools separate:

```text
ingest_pdf
reprocess_document
merge_tags
set_preferred_location
```

An MCP server used by coding agents should start read-only by default. Accidental database mutation by an autonomous agent is otherwise too easy.

# 12. Topic reviews should be evidence-bearing derived artifacts

Your topic overview idea is excellent, but avoid implementing it as:

```text
retrieve 20 papers
→ concatenate summaries
→ one giant LLM prompt
```

Instead:

```text
topic query
  ↓
candidate papers
  ↓
per-paper method cards
  ↓
comparison table
  ↓
evidence-backed synthesis
  ↓
saved topic-review artifact
```

A topic review should retain:

* original query;
* filters;
* retrieval version;
* selected papers;
* selected source units;
* model and prompt;
* comparison matrix;
* generated narrative.

Then you can regenerate or audit it.

For example, a review of GPU collision methods might explicitly compare:

```text
spatial structure
construction cost
pair enumeration
memory layout
atomics
synchronization
worst-case occupancy
overflow strategy
GPU architecture
```

That is much more useful for your work than a conventional prose review.

# 13. Migration should import everything as competing artifacts

Do not immediately “pick the best markdown” and discard the alternatives.

For each legacy output, import:

```text
artifact kind: markdown
producer: legacy_pdfminer | legacy_docling | legacy_pipeline
source path
estimated quality
original timestamp
```

Then select an active artifact according to a policy:

```text
manual override
> successful Docling with formulas
> successful Docling without formulas
> VLM extraction
> pdfminer
```

Migration flow:

1. Inventory all databases, PDFs, Markdown, summaries, and logs.
2. Compute full file hashes.
3. Match exact copies by hash.
4. Match works by normalized DOI.
5. Match remaining candidates by title, authors, year, and filename.
6. Import every historical output as an artifact.
7. Produce a conflict report.
8. Select active artifacts without deleting alternatives.
9. Copy data to the new location and verify checksums.
10. Remove repo data only after a separate explicit cleanup operation.

This is safer than making the migration script itself responsible for irreversible judgment.

# 14. A few concrete corrections to the proposed SQL

There is a technical issue in the proposed FTS declaration:

```sql
CREATE VIRTUAL TABLE papers_fts USING fts5(
    ... md_text,
    content='papers',
    content_rowid='id'
);
```

The external content table `papers` does not contain an `md_text` column. 

More importantly, paper-level full text is the wrong granularity.

Use an ordinary searchable-unit table:

```sql
search_units(
    id,
    document_id,
    unit_type,
    section_path,
    page_from,
    page_to,
    content
)
```

and:

```sql
CREATE VIRTUAL TABLE search_units_fts USING fts5(
    content,
    section_path,
    content='search_units',
    content_rowid='id'
);
```

Metadata can have a separate FTS table or be included in controlled synthetic units.

Also:

* normalize DOI before uniqueness checks;
* store authors relationally only if you truly need author-level queries;
* use integer years rather than text;
* enable foreign keys explicitly with `PRAGMA foreign_keys=ON`;
* use WAL mode;
* use numbered SQL migrations rather than schema creation scattered across modules;
* avoid writing one SQLite connection per individual operation;
* execute one paper’s state changes in a transaction.

# 15. Recommended module structure

Your proposed package split is close, but I would simplify the conceptual boundaries:

```text
paperdb/
├── api.py                 # stable public PaperDB facade
├── config.py
├── paths.py
├── db/
│   ├── connection.py
│   ├── schema.sql
│   ├── migrations/
│   ├── repository.py
│   └── models.py
├── identity/
│   ├── hashing.py
│   ├── matching.py
│   └── metadata.py
├── ingest/
│   ├── scanner.py
│   ├── pipeline.py
│   ├── jobs.py
│   └── migration.py
├── extract/
│   ├── base.py
│   ├── docling_backend.py
│   ├── grobid_backend.py
│   ├── mineru_backend.py
│   ├── equations.py
│   └── methods.py
├── artifacts/
│   ├── store.py
│   └── provenance.py
├── search/
│   ├── fts.py
│   ├── vectors.py
│   ├── hybrid.py
│   └── context.py
├── synthesis/
│   ├── summaries.py
│   ├── method_cards.py
│   └── topic_reviews.py
├── taxonomy/
│   ├── extraction.py
│   └── aliases.py
├── cli.py
└── mcp.py
```

The main architectural rule should be:

```text
CLI ─┐
MCP ─┼─> PaperDB API ─> repository/services
GUI ─┘
```

CLI, MCP, and GUI must not contain their own SQL queries or parsing logic.

# 16. Revised implementation order

I would change your sequence slightly.

## Phase 0 — benchmark and inventory

Before migration or new extraction:

* build the representative PDF benchmark;
* inventory all legacy artifacts;
* define identity matching rules.

## Phase 1 — stable foundation

1. Add proper `pyproject.toml` and package entry point.
2. Implement paths/configuration.
3. Implement schema migrations.
4. Implement `works/documents/files/file_locations`.
5. Implement artifacts and processing log.
6. Implement scan with full hashes and dry-run reporting.

Package distribution is still listed as unimplemented in the repository checklist, so this really is foundational rather than cosmetic.

## Phase 2 — migration and useful search

1. Import `consolidated.db`.
2. Import all existing artifacts with provenance.
3. Build searchable units.
4. Implement FTS5 search.
5. Implement `status`, `search`, `inspect`, `get`, and `context`.
6. Test on your actual research questions.

At this point the system is already useful without new LLM work.

## Phase 3 — reliable new ingestion

1. Docling structured output.
2. Formula enrichment.
3. GROBID metadata/reference extraction.
4. BibTeX matching.
5. Incremental job execution.
6. Error and quality reports.

## Phase 4 — scientific extraction

1. Equation objects with source coordinates.
2. Equation visual QA.
3. Source algorithms.
4. Reconstructed method cards with evidence links.
5. Versioned summaries.

## Phase 5 — agent access

1. Read-only MCP.
2. Context-pack resources.
3. Coding-agent integration tests.
4. Later, controlled ingest/reprocess tools.

## Phase 6 — optional intelligence

1. Embeddings and hybrid search.
2. Topic reviews.
3. Citation graph.
4. Tag consolidation.
5. GUI improvements.

# 17. What I would deliberately avoid

I would **not** initially adopt:

* LangChain as the central architecture;
* LlamaIndex as the central architecture;
* Neo4j or another graph database;
* PostgreSQL;
* a persistent web service;
* multiple vector-database servers;
* automatic filesystem watching;
* autonomous LLM mutation of metadata;
* an elaborate ontology before seeing the real tag distribution.

These could all be added later behind narrow interfaces. At your present scale, they mostly increase dependency complexity and make debugging harder.

Zotero is a plausible future integration because its desktop client exposes a local API and its API supports library metadata and full-text content. But it is not necessary for the first implementation, and your existing Mendeley BibTeX import is a perfectly reasonable bridge. ([zotero.org][9])

# 18. Condensed revised vision

I would rewrite the project goal approximately as follows:

> **Paperdb is a local, non-destructive scientific-paper compiler and retrieval service. It indexes existing PDF libraries in place; produces versioned, provenance-preserving representations of papers; extracts source-grounded equations and computational methods; and assembles compact evidence-bearing context packages for researchers and LLM coding agents. SQLite is the persistent catalogue, generated Markdown is the human-readable view, and CLI/Python/MCP are interchangeable access interfaces. Full-text search is the default retrieval mechanism, while embeddings and knowledge graphs are optional enhancements rather than architectural dependencies.**

That captures the essence of what you are trying to build more precisely than “local paper database.”

The GitHub repository confirms that a large fraction of the extraction machinery already exists; the next work is primarily **refactoring around identity, artifacts, provenance, and retrieval**, not restarting the project.

I could inspect the GitHub repository directly. The DeepWiki page itself did not resolve through my browser interface, so I did not rely on it.

The most useful next deliverable is a **PaperDB design v2 document** containing the revised schema, artifact lifecycle, context-pack format, MCP contract, migration algorithm, and a small executable implementation plan mapped onto the existing repository files.

[1]: https://www.sqlite.org/fts5.html?utm_source=chatgpt.com "SQLite FTS5 Extension"
[2]: https://modelcontextprotocol.io/specification/2025-06-18/server/tools?utm_source=chatgpt.com "Tools - Model Context Protocol"
[3]: https://docling-project.github.io/docling/usage/supported_formats/?utm_source=chatgpt.com "Supported formats - Docling"
[4]: https://grobid.readthedocs.io/en/latest/?utm_source=chatgpt.com "GROBID Documentation"
[5]: https://github.com/opendatalab/mineru?utm_source=chatgpt.com "GitHub - opendatalab/MinerU: Transforms complex documents like PDFs and Office docs into LLM-ready markdown/JSON for your Agentic workflows. · GitHub"
[6]: https://github.com/datalab-to/marker/blob/master/README.md?utm_source=chatgpt.com "marker/README.md at master · datalab-to/marker · GitHub"
[7]: https://arxiv.org/abs/2604.04948?utm_source=chatgpt.com "From PDF to RAG-Ready: Evaluating Document Conversion Frameworks for Domain-Specific Question Answering"
[8]: https://github.com/asg017/sqlite-vec?utm_source=chatgpt.com "GitHub - asg017/sqlite-vec: A vector search SQLite extension that runs anywhere! · GitHub"
[9]: https://www.zotero.org/support/dev/web_api/v3/fulltext_content?utm_source=chatgpt.com "Zotero Web API Full-Text Content Requests | Zotero Documentation"


---

# USER

I like your review but I do not agreee 100%

1) you recomand to use artifacts  + hash together with human readable names
```
artifacts/
│   ├── a8/7c/a87c.../
``` 
I  do not like making artifact which are not easly human radble, it is difficulet to navigate and debug. I would rather say that DOI is perfect identifier (unique) for papers and even Authro_yaer-jornal_title (part of title) is unique enoguh, if it is still not engou we can add short number at the end - I prefer such sematic unique ID rahter than random hash. I would not worry about uniques. If we have multiple files related to that paper we can lit them in database direcly, no need to make separate folder for them. So in the end I do not see clear need for hash. I do not want to make too many files, I would prefer it lean. We have a lot of data in database, so why to have milion of separate .md or .json files on disk, I would rather agregate it to few files per article. Maybe we can have one .md one .json and one .bib file for each paper?

2) Ad MCP - key is sematic search, so we can find easily papers relevnt for certain topic make the review, find equations and algorithms, methods relevant for solving certain scientific problem ...
RAG can be usefull for sematic search, but we will focus on that later, fist step should be sematic seach by tags, and other bibliographic info

---

# Chat GPT 5.6 sol hi

I agree with both corrections. My previous proposal leaned too much toward a generic provenance-heavy document-processing system. Your application is smaller, personal, scientifically specialized, and should remain **transparent and manually inspectable**.

The design should optimize for:

1. Human readability and debugging.
2. Easy use by coding agents.
3. Minimal duplication and filesystem clutter.
4. Sufficient provenance—not maximal archival purity.
5. Semantic scientific discovery as the central function.

That is also consistent with your original requirement that the generated Markdown remain human-browsable rather than hidden in hash-named cache directories. 

# 1. Semantic paper identity, not hash-based identity

I agree that a hash should **not** be the visible paper identity or directory name.

There are actually three separate concepts:

* **Paper identity:** DOI or semantic citekey.
* **Database identity:** small integer primary key.
* **File checksum:** optional internal mechanism for detecting identical or moved files.

The first two are essential. The third is merely useful infrastructure.

## Recommended identifiers

Every paper should have:

```text
id          = 427                         # internal SQLite integer
paper_key   = Macklin_2016_XPBD           # human-readable stable key
doi         = 10.1145/2994258.2994272     # canonical external identifier
```

The filename can then be:

```text
Macklin_2016_XPBD.md
Macklin_2016_XPBD.json
Macklin_2016_XPBD.bib
```

If a collision occurs:

```text
Macklin_2016_XPBD_2.md
```

or, preferably, use the stable database ID:

```text
Macklin_2016_XPBD__p0427.md
```

That suffix is not pretty, but it remains comprehensible and deterministic. It is better than adding random hexadecimal characters.

## DOI versus `paper_key`

DOI is the best canonical identifier whenever one exists, but it is not always suitable as a filename because:

* some papers have no DOI;
* arXiv manuscripts may precede DOI assignment;
* theses, reports, old proceedings, and software papers may lack one;
* DOI strings contain `/` and punctuation;
* supporting information may share the parent DOI.

I would therefore use:

```text
papers.id          internal relational identity
papers.paper_key   human-readable unique identity
papers.doi         canonical scholarly identity when available
```

The DOI should be unique after normalization:

```text
https://doi.org/10.1103/PhysRevB.40.3979
doi:10.1103/PhysRevB.40.3979
10.1103/physrevb.40.3979
```

should all normalize to:

```text
10.1103/physrevb.40.3979
```

## The limited role of hashes

I would still retain a full or partial checksum in `paper_files`, but only invisibly:

```sql
CREATE TABLE paper_files(
    id INTEGER PRIMARY KEY,
    paper_id INTEGER REFERENCES papers(id),
    path TEXT UNIQUE,
    file_role TEXT,          -- publisher, arxiv, supplement, manuscript
    version_label TEXT,
    file_size INTEGER,
    modified_time REAL,
    sha256 TEXT,             -- optional internal checksum
    is_preferred INTEGER DEFAULT 0,
    last_seen TEXT
);
```

The checksum helps answer:

* Is the PDF in Mendeley exactly the same as the one in `PAPERS_new`?
* Was a file moved or merely renamed?
* Is this a revised publisher PDF with different bytes?
* Have we already processed exactly this input?

But it should never appear in normal filenames, CLI output, or navigation. It is analogous to a checksum in a simulation result: useful for integrity, not a human-facing label.

It can also be computed lazily:

```text
first compare path, size and modification time
only compute SHA-256 for new, changed or ambiguous files
```

So I retract the idea that hashes should organize the output directory.

# 2. A lean filesystem: one Markdown, one JSON, one BibTeX

Your proposed three-file bundle per paper is a good design.

I would use:

```text
~/paperdb/
├── papers.db
├── papers/
│   ├── 1989/
│   │   ├── Parrinello_1989_PhysRevB_CarParrinello__p0123.md
│   │   ├── Parrinello_1989_PhysRevB_CarParrinello__p0123.json
│   │   └── Parrinello_1989_PhysRevB_CarParrinello__p0123.bib
│   ├── 2016/
│   │   ├── Macklin_2016_XPBD__p0427.md
│   │   ├── Macklin_2016_XPBD__p0427.json
│   │   └── Macklin_2016_XPBD__p0427.bib
│   └── ...
├── reviews/
├── legacy/
└── logs/
```

Grouping by year prevents one directory from eventually containing ten thousand files, while remaining immediately understandable. Journal or first-author grouping would also be reasonable, but year is the simplest neutral hierarchy.

I would **not** create one directory per paper unless extracted figures or equation images later make that necessary.

## The Markdown file

The Markdown should be the primary human-readable representation:

```markdown
---
paper_id: 427
paper_key: Macklin_2016_XPBD
doi: 10.1145/2994258.2994272
title: XPBD: Position-Based Simulation of Compliant Constrained Dynamics
authors:
  - Miles Macklin
  - Matthias Müller
year: 2016
source_pdf: /home/prokop/Desktop/PAPERs/...
conversion_backend: docling
conversion_version: ...
---

# Generated scientific summary

> This section was generated from the paper and is not source text.

## Essence

...

## Methods

...

## Key equations

...

## Algorithms

...

---

# Extracted source text

## Introduction

...
```

This gives you one file that is directly useful for:

* manual reading;
* `grep`;
* IDE navigation;
* passing to an LLM;
* basic FTS indexing.

The generated and source-derived parts must be visibly separated, so nobody mistakes an LLM reconstruction for verbatim paper content.

## The JSON file

The JSON should contain only information that benefits from structure:

```json
{
  "paper_id": 427,
  "paper_key": "Macklin_2016_XPBD",
  "identifiers": {
    "doi": "10.1145/2994258.2994272"
  },
  "source_files": [
    {
      "path": "/home/prokop/Desktop/PAPERs/...",
      "role": "publisher",
      "preferred": true
    },
    {
      "path": "/home/prokop/Mendeley Desktop/...",
      "role": "duplicate"
    }
  ],
  "conversion": {
    "backend": "docling",
    "backend_version": "...",
    "created_at": "...",
    "status": "ok"
  },
  "tags": {
    "domain": ["game physics", "computational mechanics"],
    "solver": ["gauss-seidel", "position based dynamics"],
    "math_class": ["constrained dynamics"],
    "data_structure": []
  },
  "equations": [
    {
      "number": "7",
      "latex": "...",
      "section": "3.1 Compliance",
      "page": 4,
      "context": "...",
      "variables": {
        "lambda": "constraint multiplier",
        "alpha": "compliance"
      }
    }
  ],
  "methods": [
    {
      "name": "XPBD constraint update",
      "type": "reconstructed",
      "steps": ["...", "..."],
      "source_pages": [4, 5],
      "confidence": 0.9
    }
  ]
}
```

The JSON should **not duplicate the complete Markdown source text**. That would unnecessarily double the storage and make synchronization harder.

## The BibTeX file

The `.bib` file remains useful because it is:

* portable;
* directly usable by LaTeX;
* easy to inspect;
* compatible with Mendeley and Zotero;
* easy for agents to quote.

So:

```text
one current `.md`
one current `.json`
one current `.bib`
```

is a very reasonable rule.

# 3. What belongs in SQLite versus these files?

I would make SQLite the **searchable index and operational state**, not a second complete copy of every representation.

## SQLite should contain

* bibliographic metadata;
* semantic tags;
* aliases and tag relationships;
* source PDF paths;
* processing state;
* Markdown/JSON/BibTeX paths;
* summaries or essence fields useful for search;
* equations and methods if direct SQL/MCP querying is needed;
* FTS searchable text;
* processing history and errors.

## Files should contain

* current complete human-readable Markdown;
* current structured machine representation;
* BibTeX;
* optionally large parser-specific data that you explicitly want to inspect.

There will necessarily be some small duplication—for example title and DOI in the DB and JSON—but that is acceptable and useful.

The full paper Markdown should not be replicated into numerous chunk files. Chunks can exist logically as rows in the database:

```sql
CREATE TABLE search_units(
    id INTEGER PRIMARY KEY,
    paper_id INTEGER REFERENCES papers(id),
    unit_type TEXT,          -- summary, section, paragraph, equation, method
    section TEXT,
    page_from INTEGER,
    page_to INTEGER,
    content TEXT
);
```

This is much leaner than:

```text
chunks/
    paper1_chunk001.md
    paper1_chunk002.md
    ...
```

For several thousand papers, SQLite is an excellent place for tens or hundreds of thousands of small searchable text units.

# 4. Versioning without creating thousands of artifact files

My previous artifact proposal was overengineered for your present use case.

You mainly need:

* current active output;
* knowledge of how it was generated;
* ability to detect that it is obsolete;
* perhaps a limited history for summaries and expensive LLM work.

A lean design is:

```sql
CREATE TABLE processing_runs(
    id INTEGER PRIMARY KEY,
    paper_id INTEGER REFERENCES papers(id),
    operation TEXT,          -- convert, summarize, tag, equations, methods
    backend TEXT,
    backend_version TEXT,
    model_name TEXT,
    prompt_version TEXT,
    configuration_json TEXT,
    status TEXT,
    started_at TEXT,
    finished_at TEXT,
    message TEXT
);
```

The current `.md` and `.json` are updated atomically:

```text
write temporary file
validate it
rename temporary file over active file
record successful run in SQLite
```

Previous summaries can remain in a `summaries` table because they are relatively small and expensive to regenerate.

Previous complete Markdown conversions do not necessarily need permanent preservation. In most cases:

* keep the current best conversion;
* retain the old legacy source in `legacy/` during migration;
* regenerate from the unchanged PDF when needed.

An optional configuration could support:

```toml
keep_summary_history = true
keep_conversion_history = false
keep_failed_debug_outputs = true
```

This is sufficient provenance without building an archival content-addressed store.

# 5. Simplify the paper model

I also agree that my earlier distinction between:

```text
work
document version
file
file location
```

is conceptually clean but probably excessive as the first implementation.

For now, use:

```text
paper
    one intellectual publication

paper_files
    all PDFs and supplementary files associated with it
```

Possible source files:

```text
publisher PDF
arXiv PDF
accepted manuscript
supporting information
duplicate local copies
```

If version differences later become scientifically important, add a `paper_versions` table then. There is no need to encode every theoretical distinction immediately.

A practical core schema would therefore begin with:

```sql
CREATE TABLE papers(
    id INTEGER PRIMARY KEY,
    paper_key TEXT NOT NULL UNIQUE,
    doi TEXT UNIQUE,
    arxiv_id TEXT,
    title TEXT,
    authors_text TEXT,
    year INTEGER,
    journal TEXT,
    abstract TEXT,
    keywords TEXT,
    essence TEXT,
    markdown_path TEXT,
    json_path TEXT,
    bibtex_path TEXT,
    preferred_file_id INTEGER,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE paper_files(
    id INTEGER PRIMARY KEY,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    path TEXT NOT NULL UNIQUE,
    file_role TEXT,
    version_label TEXT,
    file_size INTEGER,
    modified_time REAL,
    sha256 TEXT,
    exists_now INTEGER DEFAULT 1,
    is_preferred INTEGER DEFAULT 0,
    last_seen TEXT
);
```

This is understandable even without database expertise.

# 6. Semantic search should be the central interface

I agree strongly with your second point.

The main value of MCP is not:

> “Given paper ID 427, return Equation 7.”

That is useful but secondary.

The main value is:

> “Given a scientific problem, find relevant papers, methods, algorithms, and equations, and assemble a useful overview.”

That is exactly the primary workflow described in your design. 

## First-stage semantic search should not require embeddings

The first useful semantic retrieval system can be:

```text
typed tags
+ tag aliases
+ bibliographic metadata
+ title/abstract/summary text
+ ordinary full-text search
```

No vector database is initially required.

Strictly speaking, tag-based search is semantic because the tags represent interpreted scientific meaning:

```text
"XPBD" → solver
"constrained dynamics" → mathematical class
"game physics" → domain
"GPU" → implementation platform
"uniform grid" → data structure
```

RAG only describes the later step where retrieved information is placed into an LLM context. The retrieval itself can be entirely tag- and FTS-based.

# 7. Improve the tag taxonomy for your actual questions

The current four categories are a good beginning:

* domain;
* math class;
* solver;
* data structure.

But to answer the kinds of questions you commonly ask, I would extend them modestly:

```text
domain
physical_system
phenomenon
model_or_theory
method
solver
data_structure
discretization
task
implementation
software
material_or_molecule
user
```

For example, a paper about GPU collision detection could have:

```text
domain:
    game physics
    particle simulation

task:
    broad-phase collision detection
    neighbor search

method:
    spatial hashing

data_structure:
    uniform grid
    hash table

implementation:
    GPU
    CUDA
    atomic operations

solver:
    parallel prefix sum
    radix sort
```

A quantum-chemistry paper could have:

```text
domain:
    quantum chemistry

physical_system:
    molecular adsorbate
    ionic surface

model_or_theory:
    density functional theory
    tight binding

task:
    electronic structure
    geometry optimization

solver:
    self-consistent field
    diagonalization

software:
    DFTB+
```

This tag structure is much more useful than a vague flat list of “keywords.”

It need not be perfect. Your original decision—generate provisional detailed tags and consolidate them after observing the real data—is sound.

# 8. Natural-language query → structured tag query

The LLM should not directly decide which papers are relevant and then invent a response.

It should first translate the user request into a transparent search specification.

For example:

```text
Find methods for fast GPU collision detection between particles using
uniform grids, preferably without atomics.
```

could become:

```json
{
  "required": [
    ["task", "collision detection"],
    ["implementation", "GPU"]
  ],
  "preferred": [
    ["data_structure", "uniform grid"],
    ["method", "spatial hashing"],
    ["implementation", "atomic-free"]
  ],
  "excluded": [],
  "text_terms": [
    "broad phase",
    "neighbor search",
    "without atomics",
    "prefix sum",
    "sorting"
  ]
}
```

Then SQLite performs the actual search.

This separation is valuable:

```text
LLM interprets scientific intent
SQLite executes deterministic retrieval
MCP reports why each paper matched
```

The LLM is good at recognizing that:

```text
particle contact search
neighbor finding
broad-phase collision detection
short-range pair enumeration
```

are related concepts.

The database is good at consistently finding and ranking records.

# 9. Search ranking without embeddings

A simple first ranking could combine:

[
S(p)=
w_r N_{\mathrm{required}}
+w_o N_{\mathrm{optional}}
+w_t S_{\mathrm{title}}
+w_a S_{\mathrm{abstract}}
+w_s S_{\mathrm{summary}}
+w_u S_{\mathrm{user\ tags}}
]

For example:

```text
required tag match       +10
preferred tag match       +4
user-assigned tag         +6
title match               +5
abstract/summary match    +2
full-text match           +1
```

The exact numbers are not important initially. What matters is that `paperdb search --explain` can say:

```text
Macklin 2016, XPBD
Score: 28

Matched:
  solver: position based dynamics
  math_class: constrained dynamics
  title: XPBD
  summary: compliant constraints
```

This is much easier to debug than opaque vector similarity.

## Tag aliases

Aliases should support:

```text
PBD
position-based dynamics
position based dynamics
position-based simulation
```

without deleting the original tag text.

```sql
CREATE TABLE tags(
    id INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    category TEXT NOT NULL,
    UNIQUE(canonical_name, category)
);

CREATE TABLE tag_aliases(
    tag_id INTEGER REFERENCES tags(id),
    alias TEXT UNIQUE
);

CREATE TABLE paper_tags(
    paper_id INTEGER REFERENCES papers(id),
    tag_id INTEGER REFERENCES tags(id),
    source TEXT,            -- llm, user, bibtex, imported
    confidence REAL,
    raw_name TEXT,
    PRIMARY KEY(paper_id, tag_id, source)
);
```

# 10. Full-text search still belongs in phase one

Although tags should drive semantic paper selection, I would not postpone FTS5. It is cheap to implement and solves an important limitation of tags.

A query such as:

```text
avoid atomic operations
```

may not have been extracted as a formal tag, but it may appear in:

* the abstract;
* a method summary;
* an algorithm card;
* conclusions;
* limitations.

Therefore phase one should be:

```text
metadata + typed tags + tag aliases + FTS5
```

not only tags.

Embeddings come later for conceptual queries where neither tags nor exact language align.

# 11. MCP should expose scientific tasks

I would redesign the MCP interface around scientific questions rather than database mechanics.

## Discovery tools

```text
search_papers(
    query,
    required_tags=None,
    preferred_tags=None,
    excluded_tags=None,
    year_range=None,
    limit=20
)
```

Returns papers plus explicit reasons for matching.

```text
find_methods(
    problem,
    constraints=None,
    limit=20
)
```

Examples:

```text
problem:
    short-range interaction search on GPU

constraints:
    avoid atomics
    memory compact
    suitable for highly nonuniform density
```

```text
find_equations(
    concept,
    variables=None,
    tags=None,
    limit=30
)
```

Examples:

```text
constraint compliance update
Dyson orbital tunneling matrix element
Ewald summation for two-dimensional periodicity
```

## Inspection tools

```text
get_paper(paper_id_or_key_or_doi)
get_paper_markdown(paper_id)
get_paper_methods(paper_id)
get_paper_equations(paper_id)
get_related_papers(paper_id)
explain_paper_match(paper_id, query)
```

## Synthesis tools

```text
compare_methods(
    problem,
    comparison_axes,
    constraints=None,
    max_papers=20
)
```

```text
build_topic_review(
    topic,
    focus=None,
    constraints=None,
    max_papers=30
)
```

The important point is that:

```text
build_topic_review("spatial partitioning for GPU particle collisions")
```

should internally call:

1. interpret query into tags and search terms;
2. find candidate papers;
3. diversify the result set;
4. retrieve methods and equations;
5. construct per-paper evidence cards;
6. compare them;
7. synthesize the overview.

# 12. Two-stage retrieval remains useful

Even before embeddings, I recommend two distinct search stages.

## Stage A: select papers

Use:

* tags;
* title;
* authors;
* journal;
* year;
* abstract;
* essence;
* user collections.

## Stage B: search within selected papers

Use:

* section text;
* equations;
* method cards;
* algorithms;
* limitations;
* implementation notes.

This prevents the system from returning twenty paragraph matches from one highly verbose paper while missing five other relevant methods.

For a topic review:

```text
Find 20 diverse relevant papers
    ↓
For each paper, retrieve 3–8 relevant evidence units
    ↓
Compare those units
```

This is already a useful RAG pipeline without vectors.

# 13. Suggested first implementation milestone

I would now define the first practical version as follows.

## Data model

Implement only:

```text
papers
paper_files
tags
tag_aliases
paper_tags
search_units
summaries
equations
methods
processing_runs
```

No generic artifacts table and no content-addressed folders.

## Filesystem

```text
papers.db
papers/<year>/<paper_key>.md
papers/<year>/<paper_key>.json
papers/<year>/<paper_key>.bib
legacy/
reviews/
logs/
```

## CLI

```bash
paperdb scan
paperdb migrate
paperdb status

paperdb search "GPU collision uniform grid" --explain
paperdb search --tag solver:xpbd --tag domain:game_physics
paperdb inspect Macklin_2016_XPBD
paperdb get Macklin_2016_XPBD --markdown
paperdb methods "constraint dynamics"
paperdb equations "compliance parameter"
paperdb review "GPU particle collision methods"
```

## MCP

Implement first:

```text
search_papers
find_methods
find_equations
get_paper
get_paper_context
compare_methods
build_topic_review
list_tags
```

## Retrieval

Use:

```text
typed tag matching
tag aliases
SQLite FTS5
bibliographic filters
```

No embeddings initially.

# Revised central design principle

I would summarize the corrected architecture this way:

> A paper is represented by one semantic database record, one human-readable Markdown file, one structured JSON sidecar, and one BibTeX file. DOI is the preferred scholarly identifier, while a readable citekey is the local identifier. All source PDFs remain in their existing locations and are associated with the paper through database records. Checksums may be stored internally for duplicate and move detection but never organize the user-facing files. Scientific discovery is driven first by typed tags, aliases, bibliographic metadata, and full-text search. MCP exposes high-level scientific operations—finding papers, methods, equations, comparisons, and topic reviews—rather than merely exposing database rows. Vector embeddings are a later enhancement, not a prerequisite.

I think this version is closer to the essence of what you want: **a lean, inspectable scientific knowledge system, not a generic enterprise document store.**


---

# USER

there is updated document, can you review it? Any additional comments or do you agree? We should wrap it up

this sis what my coding LLM wrote about it, do you agree?

## My assessment: what's worth adopting

**Strongly recommend** (clear improvements over our current design):
- Semantic `paper_key` instead of hash-based identity (#1)
- Lean 3-file filesystem (#2) 
- `processing_runs` instead of boolean flags (#4)
- FTS at search-unit granularity (#6)
- Two-stage retrieval (#7)
- Search ranking with `--explain` (#8)
- Method cards with source/reconstruction distinction (#10)
- Equation `latex_raw` vs `latex_normalized` + source coordinates (#11)
- MCP around scientific tasks (#13)
- Context pack as central output (#14)
- Topic reviews as evidence-bearing pipeline (#15)
- Tag assertions preserve raw names (#17)
- SQLite best practices (#19)
- Architecture: CLI/MCP/GUI → API → services (#20)

**Recommend with adaptation** (good idea but may need simplification):
- Extended tag categories (#16) — useful but don't over-engineer, start with a few more categories
- NL query → structured tag query (#9) — powerful but adds complexity, could be phase 2
- Import as competing artifacts (#18) — good principle but our user wants lean, not archival

**Probably skip for now** (over-engineering for our scale):
- GROBID as separate backend (#12) — Docling is working, add GROBID later if needed
- Phase 0 benchmark (#21) — we already have 393 processed papers as de facto benchmark
- Full 4-table identity split (Work/Document/File/Location) — user already rejected this

---

# Chat GPT 5.6 sol hi

## Overall verdict

Yes. I now agree with the architecture almost completely. The revised document has a clear central concept:

> **Paperdb compiles papers into a searchable scientific representation and assembles evidence-bearing context for humans and coding agents.**

That is much stronger than framing it as a generic database or RAG application. The combination of semantic paper identity, three human-readable files, SQLite, typed tags, FTS5, two-stage retrieval, context packs, and scientific-task-oriented MCP is coherent and appropriately lean. 

I would consider the conceptual design **finished**, after correcting several internal inconsistencies described below.

# Assessment of the coding LLM’s review

## Strongly recommend

I agree with every item in its “strongly recommend” category.

In particular, these are the architectural pillars:

* semantic `paper_key`;
* one `.md`, `.json`, and `.bib` per paper;
* `processing_runs`;
* `search_units` plus FTS5;
* two-stage retrieval;
* explainable ranking;
* source-grounded equations and method cards;
* context packs;
* scientific MCP tools;
* one common `PaperDB` API used by CLI, MCP, and GUI.

The document now expresses these consistently and clearly. 

## Recommend with adaptation

I also agree with all three, with the following interpretation.

### Extended tag categories

Keep the database capable of storing all proposed categories, but do not force the first extraction prompt to fill all thirteen.

I would initially emphasize perhaps:

```text
domain
physical_system
model_or_theory
task
method
solver
data_structure
implementation
software
```

The remaining categories can be populated when genuinely applicable. Empty categories are harmless; noisy invented tags are not.

### Natural language → structured query

Definitely phase 2. The initial search can already be excellent using:

```text
query terms + explicit tags + aliases + bibliographic filters + FTS5
```

Later, an LLM can translate a complex request into `required`, `preferred`, and `excluded` concepts. The document already places this appropriately in the future outlook, although it still appears earlier as if it were part of phase 1. That wording should be made consistent. 

### Competing legacy artifacts

Keep the **principle**, not a large artifact framework.

During migration:

* leave all old outputs under `legacy/`;
* represent each candidate conversion by a `processing_runs` row;
* record its source/output path;
* select one active conversion;
* generate only one current three-file bundle.

That is lean and non-destructive. The current migration section already mostly describes this approach. 

## Probably skip for now

I agree about:

* GROBID;
* the four-level Work/Document/File/Location model;
* any formal comparative parser project before implementation.

I disagree only slightly about the benchmark.

The existing 393 processed papers are a **test corpus**, but not automatically a benchmark, because there are no trusted expected outputs. You do not need a large “Phase 0 benchmark,” but you should retain a small regression set:

```text
5–10 representative papers
10–20 manually checked equations
several difficult two-column pages
one scanned/old paper
one algorithm-heavy paper
```

This is not research into which parser is best. It is simply protection against future regressions. For example, after changing Docling options, you should be able to determine whether equation extraction became better or worse.

# Final corrections before freezing the document

## 1. Define the source of truth

The design currently stores much of the same information in SQLite, Markdown, and JSON. That is acceptable, but it must say which representation wins when they disagree.

I recommend:

> **SQLite is authoritative for structured metadata, tags, equations, methods, processing state, and paths. The Markdown file is the current human-readable extracted representation. The JSON and BibTeX files are synchronized materialized views generated from the current database state and Markdown. All mutations go through the PaperDB API.**

Without this rule, manual edits or interrupted processing will eventually cause drift.

You can still permit manual JSON/Markdown edits later through an explicit `paperdb import-edits` operation, but do not silently treat all three as independent authorities.

## 2. Fix `processing_runs`: include the input identity and output path

The current table records `config_hash`, but not which PDF version was processed. 

This is insufficient:

```text
same paper
same Docling configuration
new or corrected PDF
```

would appear equivalent to the previous run.

Add:

```sql
source_file_id INTEGER REFERENCES paper_files(id),
input_sha256 TEXT,
output_path TEXT,
supersedes_run_id INTEGER REFERENCES processing_runs(id)
```

The effective processing key should be based on:

```text
operation
+ input PDF hash
+ backend/version
+ configuration
+ model
+ prompt version
```

When a new run succeeds, the prior current run for that operation becomes `superseded`.

This also gives the “competing legacy artifacts” a concrete representation: each imported legacy conversion points to its existing output file.

## 3. Resolve the `docling.json` contradiction

The data layout explicitly says there is exactly one JSON file per paper. 

But the implementation order later says:

> Save both `docling.json` and `paper.md`. 

Choose one of these:

### Preferred lean version

The single paper JSON contains the useful normalized Docling structure, metadata, equations, methods, and provenance.

```text
Macklin_2016_XPBD__p0427.json
```

Do not produce a separate `docling.json`.

### Debug option

Raw Docling output is written only when explicitly requested:

```bash
paperdb ingest ... --keep-parser-debug
```

and goes under `legacy/` or `logs/debug/`, not into the ordinary paper collection.

## 4. Fix preferred-PDF representation

The schema currently has both:

```sql
papers.preferred_file_id
paper_files.is_preferred
```

and the supposed foreign key on `preferred_file_id` is only described in a comment, not declared as a real reference. 

Use only one mechanism.

The simplest is to remove `papers.preferred_file_id` and retain:

```sql
paper_files.is_preferred
```

with:

```sql
CREATE UNIQUE INDEX one_preferred_file_per_paper
ON paper_files(paper_id)
WHERE is_preferred = 1;
```

That guarantees at most one preferred file per paper.

Also add ordinary indices:

```sql
CREATE INDEX idx_paper_files_paper ON paper_files(paper_id);
CREATE INDEX idx_paper_files_sha256 ON paper_files(sha256);
```

## 5. FTS5 needs explicit synchronization

The external-content FTS declaration is conceptually correct, but it does not automatically remain synchronized merely because `content='search_units'` is specified. 

Either:

* create insert/update/delete triggers for `search_units_fts`; or
* explicitly rebuild/update FTS through `repository.py`.

I prefer triggers because they prevent accidental inconsistency.

Also add:

```sql
run_id INTEGER REFERENCES processing_runs(id),
source_type TEXT,
source_id INTEGER
```

to `search_units`, so a search result can point back to a specific section, equation, method, or summary.

Only units belonging to the current successful run should be indexed. The simplest implementation is:

```text
new conversion succeeds
→ transactionally delete current search units for paper
→ insert replacement units
→ FTS triggers update index
```

There is no need to preserve old search units once their source conversion is superseded.

## 6. Tag aliases should not be globally unique

The present schema uses:

```sql
alias TEXT NOT NULL UNIQUE
```

for all tags. 

That is too restrictive because abbreviations can be ambiguous:

```text
MD = molecular dynamics
MD = Markdown
SCF = self-consistent field
SCF = another domain-specific acronym
```

Use:

```sql
CREATE TABLE tag_aliases(
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    UNIQUE(tag_id, normalized_alias)
);
```

An alias lookup may legitimately return multiple candidates. Its category and query context resolve the ambiguity.

Also add `run_id` to LLM-generated `paper_tags`; otherwise repeated tagging by two models both appear simply as source `"llm"` and cannot be distinguished.

## 7. Simplify the method table

The method-card concept is excellent, but the current schema has many separate JSON columns.  This makes schema evolution unnecessarily cumbersome.

I recommend:

```sql
CREATE TABLE methods(
    id INTEGER PRIMARY KEY,
    paper_id INTEGER NOT NULL REFERENCES papers(id),
    run_id INTEGER REFERENCES processing_runs(id),
    name TEXT,
    method_type TEXT,
    purpose TEXT,
    complexity TEXT,
    confidence REAL,
    card_json TEXT,
    source_passages_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

`card_json` contains:

```text
assumptions
state_variables
inputs
outputs
initialization
steps
boundary_conditions
convergence
parallelization
limitations
```

Keep common searchable fields as columns; keep evolving structured details in one JSON object.

Do not put equation foreign keys inside JSON. Use a small junction table:

```sql
CREATE TABLE method_equations(
    method_id INTEGER REFERENCES methods(id),
    equation_id INTEGER REFERENCES equations(id),
    role TEXT,
    PRIMARY KEY(method_id, equation_id, role)
);
```

This preserves referential integrity without making the schema heavy.

## 8. Decide whether context packs are ephemeral or stored

The MCP resources include:

```text
paperdb://context/{id}
```

but there is no `context_packs` table. 

Because context packs are the central output, I would store them:

```sql
CREATE TABLE context_packs(
    id INTEGER PRIMARY KEY,
    query TEXT NOT NULL,
    filters_json TEXT,
    selected_units_json TEXT,
    content TEXT,
    output_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

This allows:

* reproducing what an agent received;
* comparing two retrieval runs;
* opening a saved MCP resource;
* citing exactly which evidence units were included.

A context pack may remain ephemeral unless `--out`, `--save`, or MCP resource persistence is requested.

# One change to implementation order

The current plan delays both MCP and context packs until Phase 4, after advanced equation and method extraction. 

I would implement a **minimal context pack and read-only MCP earlier**, immediately after FTS/tag search:

```text
Phase 1:
    migration
    current Markdown bundles
    search_units
    FTS and tags
    basic context pack
    basic read-only MCP search/retrieval
```

The first context pack can contain:

* relevant papers;
* summary;
* relevant extracted sections;
* match explanations;
* bibliography.

Later phases enrich it with structured equations, method cards, and comparison matrices.

This validates the central use case early instead of waiting until nearly the whole system is implemented.

Also, generate the active Markdown/JSON/BibTeX bundles **before** building `search_units`, so the search index is always derived from the canonical active representation.

# Two small packaging corrections

The tree currently places `pyproject.toml` inside the `paperdb/` package, while the installation command assumes:

```bash
pip install -e .
```

from the AutoCrunchCoder root. 

Therefore `pyproject.toml` should be at the **AutoCrunchCoder repository root**, unless you deliberately make `paperdb/` an independently installable subproject and run `pip install -e ./paperdb`.

Also avoid defining:

```toml
all = ["paperdb[docling,gui,mcp,vector]"]
```

as a self-referential extra. List the actual dependencies in `all`, or simply omit the `all` extra initially.

# Final position

I agree with the coding LLM’s assessment, with one modification:

> Do not build a formal parser benchmark, but keep a small manually verified regression corpus.

Everything else in its categorization is correct.

After the corrections above, I would freeze the design and start implementation. No further architectural brainstorming is needed. The project has a clear hierarchy:

```text
PDFs remain where they are
        ↓
semantic paper records + lean file bundles
        ↓
typed tags + FTS search units
        ↓
two-stage explainable retrieval
        ↓
equations and evidence-bearing method cards
        ↓
context packs
        ↓
CLI / MCP / Python / later GUI
```

That is a coherent, practical design matched to your actual scientific workflow rather than to generic database or RAG fashion.

---

# USER

I would like to correct few things
1) Markdown is not only for human, it is also for LLM as LLM can read .md files much better than .pdf, it is really central form of information ,we will often give to LLM whole markdown of relevant papers, it is important it is high quality with all the equations etc.
2) ad legacy artifacts - I do not want to preseve the strucutre/format, I want t convert them to new system, but I do not want to re-generate the .md files for all papers, or eventually LLM sumaris, as this is costly. I want to reuse exstiing data/metadata to new system, therefore generate conversion scripts, but we should do it in two phases - first convert (create new version), then check the conversion, and only very lazzyly delete the olad/backup

---

# Chat GPT 5.6 sol hi

I agree. These corrections make the design more precise.

The key distinction is:

* **Markdown is the central scientific representation**, optimized for both humans and LLMs.
* **SQLite is the searchable index and processing catalogue**, not the primary container of the complete paper.
* **JSON is the structured companion representation** for equations, methods, tags, provenance, and machine queries.

For migration, “competing legacy artifacts” was misleading. The old formats are temporary inputs to a one-time conversion, not permanent representations to preserve.

Here is wording I would put into the design document:

### Markdown as the central scientific representation

Markdown is not merely a human-readable export. It is the **central complete representation of a paper** used by both humans and LLM agents.

The original PDF remains the authoritative visual source, but PDF is poorly suited for automatic context gathering and LLM consumption. Paperdb therefore compiles each PDF into a high-quality Markdown document that preserves:

* the complete readable text in correct reading order;
* section hierarchy;
* equations in LaTeX;
* equation numbering and surrounding explanations;
* tables, captions, algorithms, and pseudocode where possible;
* bibliographic identity and links back to the source PDF;
* a clearly separated generated scientific summary.

A common workflow will be to retrieve several relevant papers and provide their **complete Markdown documents** directly to an LLM. Consequently, Markdown extraction quality is a primary scientific requirement, not merely a convenience for manual navigation.

The three representations have distinct roles:

* **PDF** — original visual source and final reference for verification.
* **Markdown** — central complete representation for reading, search, context gathering, and LLM consumption.
* **JSON** — structured companion containing metadata, tags, equations, method cards, source coordinates, and processing provenance.
* **SQLite** — searchable catalogue, relationships, processing state, FTS index, and access layer across all papers.

SQLite may contain searchable sections and structured objects derived from Markdown, but the complete Markdown document remains the main portable representation of the paper.

---

### Migration of existing processed data

Legacy data should be **converted into the new Paperdb representation**, not preserved indefinitely in its old directory structure or schema.

However, existing Markdown conversions, summaries, BibTeX metadata, tags, and embeddings should be reused whenever possible. Re-running PDF conversion or LLM summarization for hundreds of papers would be unnecessarily expensive and could even replace acceptable existing outputs with different results.

Migration therefore proceeds in two explicit phases.

#### Phase A — convert and construct the new database

1. Copy the existing legacy data to a safe backup location.
2. Inventory existing PDFs, Markdown files, summaries, BibTeX records, tags, databases, and processing logs.
3. Match legacy records to semantic Paperdb records using DOI, PDF path, filename, title, authors, year, and optional file hashes.
4. Select the best existing Markdown for each paper according to a transparent policy, for example:

   * existing high-quality Docling conversion;
   * other structured conversion;
   * VLM conversion;
   * pdfminer text as fallback.
5. Reuse existing summaries, tags, equations, BibTeX, and embeddings where they can be mapped reliably.
6. Convert these data into the new SQLite schema.
7. Generate the new semantic `.md`, `.json`, and `.bib` bundle for every successfully matched paper.
8. Build search units and FTS indices from the migrated Markdown.
9. Record the source and quality of each migrated component in `processing_runs`.
10. Produce a migration report listing conflicts, missing files, ambiguous matches, and papers that may require later reprocessing.

This phase creates a complete new Paperdb installation without modifying or deleting the original data.

#### Phase B — validate and gradually retire the legacy data

After migration:

1. Compare paper counts, DOI coverage, metadata, tags, Markdown sizes, summaries, and equations between the legacy and new systems.
2. Manually inspect a representative subset of papers, especially equation-heavy and algorithm-heavy papers.
3. Verify that the new Markdown files open correctly and that CLI, FTS, context retrieval, and MCP access return the expected papers.
4. Keep the old data as a read-only backup until the new system has been used successfully for a sufficient period.
5. Reprocess only papers that are missing data or whose migrated extraction is demonstrably inadequate.
6. Delete old copies only through a separate explicit cleanup operation after user approval.

The migration is therefore:

```text
legacy data
    ↓
conversion into the new representation
    ↓
independent validation
    ↓
normal use of the new system
    ↓
optional, delayed cleanup of old backups
```

Legacy formats are not part of the final architecture. They are temporary migration sources retained only until the correctness and completeness of the new system have been verified.

One additional schema consequence follows: `processing_runs` should record whether an output was **migrated** or freshly generated, for example:

```text
operation = convert | summarize | tag | equations | migrate_markdown | migrate_summary
backend   = docling | pdfminer | legacy_docling | legacy_llama8b | ...
```

This preserves useful provenance without preserving the legacy filesystem structure as part of the new system.
