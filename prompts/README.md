# prompts

Prompt templates used when querying LLMs for scientific code generation, article summarization, and force-field implementation. These templates are filled by `pyCruncher/code_derivs.py` with Maxima-derived formulas.

## Subdirectories

- `ImplementPotential/` — Force-field code generation pipeline: `coder_system_prompt.md` and `matematician_system_prompt.md` define agent personas; `code_first.md`/`code_cpp.md` generate initial code; `simplify.md`/`substitution.md` optimize expressions; `code_incorect_result.md`/`code_not_compile.md` handle failures; `understand.md` explains concepts.
- `cpp_templates/` — `FFderivs.cpp` reference C++ force-field derivative code used as a prompt input.

## Top-level files

- `sumarize_article_pdf.md` — Prompt template for structured article summarization (title, keywords, essence, equations, algorithms, methods, connections).
- `OpenAI_Canvas_SysPromptLeak.md` — Notes on an OpenAI Canvas system prompt analysis.

See `docs/topical_audit/01_literature_pdf_and_reference_management.md` and `docs/topical_audit/02_local_llms_and_api_integration.md` for context.
