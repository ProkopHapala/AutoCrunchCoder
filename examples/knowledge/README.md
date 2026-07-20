# examples/knowledge

Worked examples for the paper pipeline: PDF→markdown→summary→SQLite→RAG. Each script demonstrates one stage of the offline-first pipeline.

## Files

- `pdf_extraction.py` — Extract text and structure from scientific PDFs using the pipeline's backends.
- `pdf_summarization.py` — Produce structured summaries (title, keywords, essence, equations, algorithms) from article PDFs.
- `bibtex_classification.py` — Classify BibTeX entries using n-gram extraction and metadata normalization.
- `ingest_chroma.py` — Ingest processed markdown chunks into a Chroma vector store for RAG.
- `file_summarization.py` — Generic file summarization using an LLM agent.
- `rag_deepseek.py` — RAG query example using DeepSeek as the generation model.
- `rag_gemini_chroma.py` — RAG query example using Gemini + Chroma vector store.
