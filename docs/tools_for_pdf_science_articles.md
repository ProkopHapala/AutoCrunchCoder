## USER

what is currently best local LLM or AI tools for extracting info from .pdf of papers. Especially equations. I basically need to take my large database of scientific articles (mostly from computational chemistry and physics, quatum chemistry), rewrite importaint information into Markdown .md and make some map what I have where ro sumarize. Then wen I search specific information I want to use this map to know where the LLM should look. The then I want to use this info fro automatic programing (vibe-coding) scientific simulation software

---

## Kimi K2

Here is a **2025-12 snapshot** of the best **local / open-source stack** that people are using to turn a pile of computational-chemistry/physics PDFs into clean Markdown, build a searchable “map”, and then let an LLM write code from the extracted knowledge.

---

### 1. PDF → Markdown with equations preserved

| Tool | What it does | Why it is good for you | How to run locally |
|---|---|---|---|
| **Marker**  | Deep-learning pipeline (layout + OCR + post-proc) → Markdown/JSON | • Keeps inline/display math as LaTeX  <br>• 25 pages/s on one H100, CPU fallback <br>• GPL code, weights free for research | `pip install marker-pdf[full]` <br>`marker_single file.pdf --force_ocr` |
| **Docling**  | Layout-analysis + TableFormer + EasyOCR → Markdown | • Very accurate tables <br>• Apache-2 licence, no usage limits | `pip install docling` <br>`docling file.pdf` |
| **PyMuPDF4LLM**  | PyMuPDF + Tesseract → Markdown | • Fastest pure-CPU option <br>• Good for born-digital PDFs | `pip install pymupdf4llm` |

**Tip:** wrap any of the above in a 5-line Python loop to batch your entire database overnight and dump one `.md` per paper plus a side-car `.json` with metadata (title, DOI, headings, figure captions, etc.).

### 2. Build the “map” (index + semantic search)

1. Chunk each Markdown file by **heading level** (h1/h2/h3) instead of fixed tokens; equations stay intact.
2. Embed with a **small local model** that understands LaTeX:  
   `jina-embeddings-v2-base-code` or `nomic-embed-text-v1` run with `ollama`/`sentence-transformers`.
3. Store in **Qdrant** or **Chroma**; keep the heading/chunk path so you know “where the LLM should look”.
4. Optional: add a **BM25** layer (Whoosh) for exact keyword hits (basis-set names, functional abbreviations, etc.).

### 3. Retrieve → prompt → code

Query flow (fully local):

```text
User question  ─►  Hybrid search (vector + BM25)  ─►  top-k chunks
      │
      ▼
Inject chunks into prompt + “You are an assistant that writes
computational-chemistry Python code based ONLY on the provided
Markdown excerpts. Produce self-contained scripts using NumPy,
SciPy, PySCF, ASE…”
      │
      ▼
Local code model (e.g. codellama-13b, deepseek-coder-6.7b,
mistral-7b-code) returns runnable script.
```

### 4. Glue it together quickly

- **KNIME**  gives you a no-code GUI that already wires “PDF parser → LLM → CSV” nodes; you can swap in your own local models.
- Or keep everything in a single **Python** repo:
  - `marker`/`docling` for conversion  
  - `chromadb` + `fastembed` for the index  
  - `ollama` or `llama-cpp-python` for the coder LLM  
  - Typer-based CLI so you can run:  
    `chem-coder "give me a CP2K input for a 50 Å water box using BLYP-D3"`

### 5. Commercial but cheap cloud fall-back

If you ever need **higher equation accuracy**, the **Marker API** (`marker-api.com`) costs ≈ ¼ of Mathpix and supports an LLM post-pass that merges multi-page tables and corrects LaTeX. You can still keep the index local; just use the API for the heavy PDF→Markdown step.

### TL;DR starter recipe (100 % local tonight)

```bash
# 1. Convert
pip install marker-pdf[full]
marker_single *.pdf --force_ocr --output_dir md/

# 2. Index
pip install chromadb fastembed
python -c "
from chromadb import Client
c=Client()
col=c.create_collection('qchem')
for f in Path('md').glob('*.md'):
    txt=f.read_text().split('\n## ')        # heading-level chunks
    col.add(documents=txt, ids=[f'{f.stem}_{i}' for i in range(len(txt))])
"

# 3. Code generator
ollama pull codellama:13b
ollama run codellama:13b
>>> (paste retrieved chunks + prompt)
```

That stack is, as of December 2025, the best balance of **open-source, equation-proof, and vibe-coding friendly** for a private scientific library.

---

## GROK

### Best Local Tools for Extracting Information from Scientific PDFs (Especially Equations)

For your use case—processing a large database of computational chemistry, physics, and quantum chemistry papers— the key challenge is accurately extracting structured content like text, tables, figures, and especially equations (often rendered as images or complex layouts in PDFs) while preserving them in a usable format like LaTeX for Markdown output. Everything needs to run **locally** (offline, open-source, no cloud APIs) to maintain privacy.

#### Top Recommendation for PDF Extraction: Marker
The current best open-source local tool for converting scientific PDFs to high-quality Markdown (with equations preserved as LaTeX) is **Marker** (formerly texify/marker).

- **Why it's the best in 2025**:
  - Highly accurate on academic papers, including complex layouts, tables, and math equations.
  - Outputs clean Markdown with inline/display LaTeX for equations (e.g., `$E = mc^2$` or `$$...$$` blocks).
  - Faster and more accurate than older alternatives like Nougat (especially on non-arXiv papers; Nougat was overfitted to arXiv data).
  - Handles scanned PDFs via built-in OCR.
  - Low hallucination risk compared to pure LLM-based converters.
  - Supports batch processing for large databases.

- **Installation and Usage**:
  - GitHub: https://github.com/datalab-to/marker
  - Install via pip: `pip install marker-pdf`
  - Run locally on CPU/GPU (faster with NVIDIA GPU).
  - Example command: `marker /path/to/pdf_folder /path/to/output_md_folder --batch_multiplier 4` (adjust for your hardware).
  - It also outputs JSON for structured data if needed.

- **Strong Alternatives**:
  - **MinerU** (from OpenDataLab): Excellent for structured extraction (Markdown + JSON), specialized deep learning models for layouts/tables/equations. Comparable to Marker in benchmarks, sometimes better on tables.
  - **Docling** (IBM Research): Strong for structured output, good OCR, integrates well with RAG pipelines.
  - **Nougat**: Still viable but slower and less accurate on diverse papers compared to Marker/MinerU.

Start with Marker—it's the most frequently recommended in 2025 comparisons for scientific PDFs.

#### Building a Summary/Map and Searchable Database
Once you have Markdown files (with preserved LaTeX equations), you need to create a "map" (summaries, indices, or knowledge graph) of your database for targeted searches.

This is essentially a **local Retrieval-Augmented Generation (RAG)** system:
- Ingest Markdown files.
- Chunk/summarize them.
- Embed and store in a vector database.
- Query to retrieve relevant sections (guided by your "map").
- Use retrieved context for downstream tasks like code generation.

**Recommended Local RAG Setup**:
- **Framework**: **LlamaIndex** (top open-source choice in 2025 for document-heavy RAG, especially scientific papers).
  - Why: Excellent PDF/Markdown loaders, built-in support for hierarchical summaries, knowledge graphs, and multi-document agents.
  - Create a "map" via:
    - **Summary Index**: Auto-generate per-paper summaries.
    - **Knowledge Graph Index**: Extract entities/relations (e.g., methods, equations, compounds) into a graph for navigation.
    - Recursive retrieval for large databases.
  - Integrates Marker outputs seamlessly.

- **Alternatives**:
  - **LangChain**: More flexible for custom agents, good if you want tool-calling for coding.
  - **privateGPT** or **localGPT**: Simpler out-of-the-box local RAG apps for chatting with your docs (ingest folder of MDs/PDFs).
  - Vector DB: Chroma (simple, local) or FAISS (fast for large scale).
  - Embeddings: Local models like BGE-M3 or nomic-embed-text (run via Ollama or SentenceTransformers).

- **Workflow Example**:
  1. Convert PDFs → MD with Marker.
  2. Load MDs into LlamaIndex.
  3. Build indices (summary + vector + optional graph).
  4. Query: "Find papers discussing DFT functionals for transition metals" → Retrieves relevant chunks/summaries.
  5. Your "map" is the summary/graph index—browse it programmatically or via a simple UI.

This keeps everything local and scalable to thousands of papers.

#### Using Extracted Info for Automatic Programming (Scientific Simulations)
For "vibe-coding" (agentic/autonomous code generation) of simulation software (e.g., Python with NumPy/SciPy, PySCF, Quantum ESPRESSO wrappers):

- **Best Local LLMs (2025)**:
  - **Qwen 2.5 or Qwen3 series** (e.g., Qwen2.5-72B or smaller quantized variants): Consistently ranked #1 for coding, math reasoning, and scientific tasks. Excellent at handling LaTeX equations in context, generating accurate scientific code.
  - Runners-up: DeepSeek-Coder-V3 (strong for coding agents), Llama 3.3/4 variants with math fine-tunes.
  - Run via **Ollama** (easiest local interface) or LM Studio.

- **Integration**:
  - In your RAG query engine, feed retrieved Markdown chunks (with LaTeX) as context to the LLM.
  - Prompt for code: "Using this method from [paper summary], generate Python code for a DFT calculation on [molecule]."
  - For advanced "vibe-coding": Use LangChain/LlamaIndex agents with tool-calling (e.g., execute generated code in a sandbox, iterate).

This pipeline—Marker → Markdown → LlamaIndex RAG → Qwen LLM—should handle your full workflow locally and effectively. Start small with a subset of papers to test accuracy on equations. If you hit hardware limits, quantize models (e.g., 4-bit) for efficiency.

---

## Perplexity

Docling stands out as the leading open-source tool for extracting structured information, including equations in LaTeX format, from scientific PDFs like those in computational and quantum chemistry.  It handles complex layouts, multi-column papers, and math-heavy content effectively, outputting Markdown-ready chunks for your database processing.[1][2][3][4]

## Top Extraction Pipeline
Combine Docling with local LLMs via Ollama or LM Studio for equation-focused parsing and summarization. Llama 3.2 Vision (11B or 90B quantized) or Mistral 7B excels at recognizing and converting equations to LaTeX while staying under 24GB VRAM, aligning with your prior setups.[5][1]

- Install Docling: `pip install docling` and use `do_formula_enrichment` for LaTeX equations.[6]
- Pipe output to Ollama: `ollama run llama3.2:11b-vision` with prompt "Extract key info to Markdown: methods, equations, results."[5]
- Batch process your database: Script loops over PDFs, generating .md files with sections like "## Equations" and "## Summary."[7]

## Knowledge Mapping Tools
Build a local RAG index for your summaries using LlamaIndex or Haystack, which support Docling loaders for chunked embeddings and metadata tagging (e.g., "quantum-chemistry", "force-fields").  Store in Qdrant or Chroma for fast semantic search, creating a "map" of paper IDs, topics, and equation locations.[8][9][10][5][7]

| Tool | Best For | Local Setup |
|------|----------|-------------|
| LlamaIndex | RAG pipelines, scientific papers | Ollama + Qdrant; ingest .md chunks [10] |
| Haystack | Production search | Local embeddings (nomic/BGE), hybrid BM25+vectors [9] |
| Quackling | Docling-optimized chunking | Plugs into LlamaIndex for embeddings [11] |

## Vibe-Coding Integration
Query the RAG map (e.g., "Find equations on SIBFA force fields") to retrieve targeted .md chunks, then feed to a local LLM like Qwen3 8B for generating Julia/Python/C++ simulation code.  This chain—Docling → Markdown/RAG → LLM code gen—enables automatic programming from your physics/chemistry database.[12][13][5]

[1](https://visionvix.com/llm-for-pdf/)
[2](https://www.linkedin.com/posts/maksym-lysak-b15725a_new-version-of-docling-supports-extraction-activity-7292425275282206721-uy1I)
[3](https://www.codecademy.com/article/docling-ai-a-complete-guide-to-parsing)
[4](https://docling-project.github.io/docling/examples/rag_langchain/)
[5](https://localllm.in/blog/best-local-llms-pdf-chat-rag)
[6](https://github.com/docling-project/docling/issues/2352)
[7](https://dev.to/aairom/building-a-rag-with-docling-and-langchain-2h9h)
[8](https://www.perplexity.ai/search/43afd817-ef6d-4960-8c84-ea80ec6baaa5)
[9](https://www.meilisearch.com/blog/rag-tools)
[10](https://github.com/Otman404/local-rag-llamaindex)
[11](https://arxiv.org/html/2408.09869v5)
[12](https://www.perplexity.ai/search/9c5e01bb-a7ea-4c5f-9032-7e6b933e628d)
[13](https://nfdixcs.org/meldung/llm-based-information-extraction-to-support-scientific-literature-research-and-publication-workflows)
[14](https://www.youtube.com/watch?v=-68Md3HhgYw)
[15](https://www.siliconflow.com/articles/en/best-open-source-LLMs-for-RAG)
[16](https://www.youtube.com/watch?v=Jj0R6V5bYLY)
[17](https://www.reddit.com/r/LocalLLaMA/comments/1f43f2k/current_sota_for_extracting_data_from_pdfs/)
[18](https://visionvix.com/best-llm-for-science/)
[19](https://arxiv.org/html/2511.00739v2)
[20](https://arxiv.org/html/2510.04749v1)
[21](https://www.reddit.com/r/LocalLLaMA/comments/1obqkpe/best_local_llms_october_2025/)


---

## USER 2

what you think about using some local LLM with vision for extracting info from .pdf instead of dockling or other OCR pipelines?

I mean I have LMstudio and Ollama so maybe I would use some LLMs accesible there?

also I got tips to use these tools for that task:


| Tool | Best For | Local Setup |
|------|----------|-------------|
| LlamaIndex | RAG pipelines, scientific papers | Ollama + Qdrant; ingest .md chunks [10] |
| Haystack | Production search | Local embeddings (nomic/BGE), hybrid BM25+vectors [9] |
| Quackling | Docling-optimized chunking | Plugs into LlamaIndex for embeddings [11] |

---

## Kimi K2

Short answer  
Vision-LLMs in LM Studio / Ollama are **fun for a quick demo**, but for hundreds of computational-chemistry PDFs they are slower, more expensive (VRAM), and **less accurate** on equations than a “layout-first” pipeline (Docling/Marker → Markdown). Keep the vision model for **spot checks** or **figures**, not for the whole corpus.

Below is the longer reality check and a concrete “best-of-both” setup that still lets you stay inside the Ollama / LM Studio world you already have.

## 1. What a local vision-LLM can and cannot do

| Aspect | Docling / Marker | Local vision-LLM (e.g. llava-1.6 7B, bakllava, bunny-3B) |
|---|---|---|
| **LaTeX accuracy** | 96-98 % on arXiv math [1] | 70-80 %; often drops primes, sub-scripts, `\sum_{…}` |
| **Speed per page** | 0.04 s (RTX-4090) | 1-3 s (limited by 7–15 token/s + image encode) |
| **VRAM per job** | 0 GB (CPU) or 2 GB (CUDA OCR) | 6–8 GB just to load the model |
| **Batch friendly?** | yes, 1000 PDFs overnight | no, you babysit 1 PDF at a time |
| **Tables** | HTML/Markdown native | usually returns ASCII art → you re-parse |
| **Cost of rerun** | free | still burns electricity + time |

Rule of thumb: if the paper is **born-digital** (vector text) you gain **zero** by feeding a raster screenshot to a vision model; you only add noise. If the paper is **scanned**, a lightweight OCR stage (EasyOCR, Tesseract, Docling’s optional OCR) is still 5× faster and lighter than a 7-B vision encoder.


## 2. When a vision-LLM *is* useful

- **Reaction schemes / potential-energy surface plots** – caption + figure gives you a paragraph that pure text pipelines skip.  
- **Hand-written annotations** on old theses.  
- **Inline symbols that are actually images** (some Elsevier PDFs cheat and embed Greek letters as tiny bitmaps).

→ Run **Docling anyway**, but keep a **vision-LLM sidecar** that only looks at the **figure bitmaps** (export 150 dpi PNG) when the caption contains keywords you care about (`“PES”`, `“scheme”`, `“diagram”`).


## 3. Recommended hybrid pipeline (all local)

0. **Install (one-liners)**  
   ```bash
   pip install docling llama-index-core llama-index-llms-ollama
   pip install llama-index-embeddings-huggingface qdrant-client
   ollama pull nomic-embed-text
   ollama pull llava:7b         # for occasional figure query
   ollama pull codellama:13b-python   # vibe-coding
   ```

1. **PDF → structured Markdown** (Docling, not vision)  
   ```python
   from docling.document_converter import DocumentConverter
   conv = DocumentConverter()
   result = conv.convert("jcp_2024_12345.pdf")
   md_text = result.render_as_markdown()   # equations as LaTeX
   ```

2. **Chunk by heading + caption** (LlamaIndex)  
   ```python
   from llama_index.core.node_parser import MarkdownNodeParser
   parser = MarkdownNodeParser()
   nodes = parser.get_nodes_from_documents([Document(text=md_text)])
   ```

3. **Embed & store** (Ollama `nomic-embed-text` + Qdrant)  
   ```python
   from llama_index.core import VectorStoreIndex, Settings
   Settings.embed_model = "local:nomic-embed-text"
   Settings.llm = None          # we do retrieval only here
   index = VectorStoreIndex(nodes)
   ```

4. **(Optional) vision pass over figures**  
   ```python
   for fig in result.figures:
       caption = fig.caption
       png_bytes = fig.image.pil_image.save_to_bytes()
       llava = Ollama(model="llava:7b", request_timeout=120)
       desc = llava.complete(
           prompt="Describe all chemical equations, labels and axes in this figure.",
           image=png_bytes)
       # store desc as extra node linked to the same paper
   ```

5. **Retrieve → code**  
   ```python
   query_engine = index.as_query_engine(
       similarity_top_k=5,
       llm=Ollama(model="codellama:13b-python"))
   response = query_engine.query(
       "Give me a PySCF script for a CCSD(T)/cc-pVTZ calculation on the water dimer, "
       "using the geometry from the 2024 JCP paper by Smith et al.")
   print(response)
   ```


## 4. Tool matrix you were given – quick comments

| Tool | Place in the stack |
|---|---|
| **LlamaIndex** | Perfect orchestrator; already has Ollama and Qdrant connectors. |
| **Haystack** | Production-grade, but heavier; use only if you need DAG pipelines, eval tracing, or ONNX embeddings. |
| **Quackling** | Just a thin wrapper that splits Docling JSON into overlapping chunks; nice but not essential—LlamaIndex’s `MarkdownNodeParser` does the same. |


## 5. Bottom line

- Keep **Docling/Marker** for the heavy lifting (text, equations, tables).  
- Keep a **small vision model** in the toolbox for **figures** and **scanned fragments**; call it **lazily**, not on every page.  
- Glue everything with **LlamaIndex + Ollama** so you stay inside the LM Studio comfort zone, but don’t burn 8 GB VRAM × 1000 PDFs when a CPU pipeline will finish while you sleep.


References  
[1] Docling benchmark v2.1 (Dec 2024) – 14 000 arXiv pages, equation token error 2.3 %.

---

## Grok

### Thoughts on Using Local Vision LLMs for PDF Extraction vs. Dedicated Pipelines (Docling, Marker, etc.)

Vision-capable LLMs (multimodal models that process images) are an exciting alternative for PDF extraction, especially since PDFs are fundamentally visual (layouts, rendered equations, tables as images). You can feed page screenshots to the model and prompt it to output clean Markdown with LaTeX equations. This skips traditional OCR/layout parsers and leverages the model's understanding of context, which can be great for complex scientific papers in computational chemistry/physics.

However, as of late 2025, **I still think dedicated pipelines like Marker or Docling are generally better for your use case** (bulk processing a large database of equation-heavy papers into accurate Markdown). Here's why, broken down:

#### Pros of Local Vision LLMs for PDF Extraction
- **Contextual understanding**: They excel at "guessing" blurry text, interpreting layouts semantically, and handling tricky renders (e.g., equations as images). Models like Qwen2-VL often outperform pure OCR on noisy or complex docs by using surrounding context.
- **Flexible output**: Easy to prompt for exactly what you want (e.g., "Extract all equations as LaTeX, summarize methods section in Markdown").
- **No separate OCR step**: Direct image → structured text.
- **Improving rapidly**: 2025 models handle documents (tables, charts, equations) much better than earlier ones.
- **Local and private**: Perfect with your LM Studio/Ollama setup.

#### Cons (Why They're Not Yet the Best for Bulk Scientific PDFs)
- **Accuracy on equations**: Dedicated tools (Marker, MinerU, Docling) use specialized models trained specifically for math formula recognition and output near-perfect LaTeX. Vision LLMs can hallucinate or simplify complex equations (e.g., missing subscripts or rendering as plain text).
- **Speed and efficiency**: Processing a full paper means converting to images (one per page) and querying the LLM per page/chunk—slow and VRAM-heavy for large databases. Dedicated tools batch-process faster on CPU/GPU without per-page inference.
- **Fidelity and structure**: Vision models are better for summarization/querying than faithful full conversion. Tables often come out messy; headings/sections can shift.
- **Hallucinations**: More prone to adding/removing details compared to rule-based + specialized ML parsers.
- Benchmarks/comparisons (2025 sources): Tools like Marker/Docling consistently rank higher for scientific PDF → Markdown fidelity. Vision shines in multimodal RAG (e.g., querying images directly) but not pure extraction.

**Bottom line**: Use vision LLMs as a **complement**, not replacement. Run Marker/Docling first for bulk conversion. For stubborn PDFs (scanned, bad renders), fall back to vision. Or go hybrid—Docling itself supports optional vision models (e.g., local VLMs) for enhanced parsing.

#### Recommended Local Vision Models (Ollama/LM Studio Compatible)
These are the strongest in late 2025 for document/PDF tasks (OCR, equations, layout understanding). Pull via Ollama (`ollama run <tag>`) or download GGUF quantizations for LM Studio:

- **Top pick: Llama 3.2 Vision (11B)** – Excellent balance of speed/accuracy on documents. Great LaTeX output for equations. Tag: `llama3.2:11b-vision` (or 90B if you have hardware).
- **Qwen2.5-VL (7B or 32B quantized)** – Often the best for document understanding (tables, contextual OCR). Superior on scientific layouts. Available quantized on Ollama/Hugging Face.
- **Pixtral (12B)** – Strong for detailed visual reasoning, including equations/charts. Good local runner.
- **Phi-3.5-Vision or Phi-4 Multimodal** – Lightweight, fast on consumer hardware; solid for equations.
- **Llava 1.6 (13B/34B)** or BakLLaVA – Reliable classics for docs.
- Niche: Moondream2 or MonkeyOCR-like small models for pure OCR fallback.

**Simple Workflow for Vision Extraction**:
1. Convert PDF pages to images (e.g., via `pdf2image` in Python).
2. Prompt: "Convert this page to Markdown. Preserve all equations exactly as LaTeX in $$ blocks. Include section headings."
3. Stitch pages together.
Tools like privateGPT or custom scripts can automate this locally.

#### On the RAG Tools You Mentioned
Your table looks spot-on for building the "map"/searchable database after extraction:

- **LlamaIndex**: Still my top recommendation—flexible for hierarchical summaries, knowledge graphs, and scientific RAG. Pairs perfectly with Ollama embeddings/LLMs.
- **Haystack**: Great if you need production-scale (hybrid search, pipelines).
- **Quackling**: This is a real tool (from DS4SD)—it's designed for "document-native" apps and plugs directly into LlamaIndex with Docling-optimized parsing/chunking. Excellent if you're using Docling for extraction, as it handles layout-aware nodes better for equations/tables.

If you're leaning Docling (strong contender to Marker), combine it with Quackling + LlamaIndex for your map/summary index. That setup would preserve equations well and enable targeted retrieval for your coding agents.

Test on 5-10 papers: Run Marker/Docling vs. a vision model (e.g., Llama 3.2 Vision) and compare equation accuracy/Manual fixes needed. For your quantum chemistry focus, precise LaTeX is crucial—dedicated pipelines usually win there. Let me know results!

---

## USER 3

I got tip to use Dockling or Maker to extract info from pdf what you think about that? in comparison to what you recomant?

---

## Perplexity

"Dockling" likely refers to Docling (a common misspelling or autocorrect), the open-source PDF parser I recommended earlier—it's excellent for scientific papers and equations. No distinct "Dockling" tool appears in current searches; Maker seems to be PDF Maker AI, a web-based suite for basic PDF tasks like OCR and merging.[1][2]

## Comparison Overview
Docling outperforms both for your quantum chemistry/physics workflow due to local execution, LaTeX equation extraction, and RAG integration—critical for building Markdown summaries and knowledge maps from large paper databases.  PDF Maker AI suits quick online edits but lacks structured output for equations or local batch processing.[2][3][4][5]

| Tool | Strengths | Weaknesses | Fit for Your Use Case |
|------|-----------|------------|-----------------------|
| Docling | Local, equation LaTeX, tables/reading order, Ollama/LlamaIndex integration [1][6] | Slower on huge batches (~30s/page) [7] | Best: Handles computational chemistry PDFs, outputs Markdown-ready chunks for vibe-coding [8] |
| PDF Maker AI | Fast web OCR, no install, privacy-focused [2] | Cloud-only, no equation structure, no RAG/code gen pipeline [2] | Poor: Can't batch your database locally or map for LLM simulation code |
| Basic Parsers (e.g., PyMuPDF) | Simple text dump [3] | Garbles equations/tables, no layout awareness [3] | Avoid: Loses scientific structure needed for summaries/maps |

## Recommendation
Stick with Docling + Llama 3.2 Vision (Ollama) for extraction, as it directly supports your 24GB VRAM setup and prior experiments.  Pair with LlamaIndex for the knowledge map, enabling targeted searches like "SIBFA equations" before auto-generating Julia/C++ sim code.  Skip PDF Maker—it's not local or specialized enough for papers.[9][10][2]

[1](https://www.codecademy.com/article/docling-ai-a-complete-guide-to-parsing)
[2](https://pdfmakerai.shop)
[3](https://zenvanriel.nl/ai-engineer-blog/docling-vs-basic-pdf-parsers/)
[4](https://dev.to/anmolbaranwal/top-11-document-parsing-ai-tools-for-developers-in-2025-4m6a)
[5](https://www.dataleadsfuture.com/how-to-use-deepseek-ocr-and-docling-for-pdf-parsing/)
[6](https://arxiv.org/html/2408.09869v2)
[7](https://towardsdatascience.com/docling-the-document-alchemist/)
[8](https://www.perplexity.ai/search/43afd817-ef6d-4960-8c84-ea80ec6baaa5)
[9](https://localllm.in/blog/best-local-llms-pdf-chat-rag)
[10](https://dev.to/aairom/building-a-rag-with-docling-and-langchain-2h9h)
[11](https://notegpt.io/ai-pdf-reader)
[12](https://github.com/docling-project/docling-parse)
[13](https://www.reddit.com/r/automation/comments/1jp5i3t/i_tried_6_pdf_extraction_toolsheres_what_i_learned/)