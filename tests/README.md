# AutoCrunchCoder `/tests` 

## Features Implemented and Tested

This project contains a collection of scripts that demonstrate various functionalities, primarily focused on utilizing Large Language Models (LLMs) for different tasks and integrating them with other tools.  The following sections detail the individual scripts and their purposes.

### Research

##### Research Article Classification 

These scripts classify research articles based on their BibTeX entries and abstracts, extracting keywords and research areas.

- **files**: 
    - `test_bibtex.py`
    - `test_bibtex2.py`

##### Summarization using LLMs

These scripts demonstrate various approaches summarization of PDFs and text files and source-code, including parallel processing and different LLM agents.  Variations likely explore different summarization techniques or handle different file types (Fortran 90, SSE).

- **files**: 
    - PDF Summarization:
        - `test_sumarize_pdfs.py` 
        - `test_sumarize_pdfs_new.py`, 
    - Source Code Summarization:
        - `test_sumarize_files.py`, 
        - `test_sumarize_files_f90.py`, 
        - `test_sumarize_files_SSE.py`, 
        - `test_sumarize2.py`

### Coding AI

##### Retrieval Augmented Generation (RAG) for code

These scripts demonstrate different RAG implementations using Langchain, OpenAI, and potentially other LLM providers (DeepSeek, Gemini). They showcase various methods for querying and retrieving information from a vector database built from a codebase.

- **files**:
    - Generation (Vector Database Creation ): 
        -`ingest_codebase.py` - 
    - Retrieval & generation : 
        - `RAG_retrival_langchain_openai.py`
        - `RAG_retrival_DeepSeek.py`
        - `RAG_retrival_GeminiFlash.py`
        - `RAG_retrival_GeminiFlash_chroma.py`

##### LLM Agent Testing 
- **files**:
  - *LMstudio* : 
     - `LMstudio_agents.py`
     - `LMstudio_client.py`
     - `test_LMstutio.py`
  - *DeepSeek* : 
     - `test_DeepSeek.py`
     - `test_DeepSeek_FIM.py`
     - `test_DeepSeek_JSON.py`
     - `test_DeepSeek_Tools.py`
     -  `test_deepseek_curl.py`



- **Description**: These scripts test the interaction with and capabilities of different LLM agents through the LMstudio interface.
- **Key Components**: LMstudio integration, testing of various LLM agents.

##### Code Analysis

These scripts likely perform static code analysis on C++ code using Clang.
 
 - **files**:

  - `test_ctags.py` - Use universal ctags to generate a tags file for a codebase (C,C++, fortran etc. ) and export it as python dictionary (class, methods, free functions, files etc. )
  - `test_documenter.py` - Script to generate doc-strings for each function in a C/C++ codebase using LLMs and ctags.
  - `test_gen_math.py` 

  - `test_GitToMarkdown.py`, 
  - `test_GoogleAI_Tools.py` 
  - `test_GoogleAI.py` 
  - `test_Groq_Tools.py` 
  - `test_Groq.py` 
  - `test_maxima_derivs.py` 
  - `test_pdf_text.py`, 

- **files**:
  - `test_clang_lint copy.py`
  - `test_cpp_lint.py`
- **Description**: These scripts likely perform static code analysis on C++ code using Clang.
- **Key Components**: Clang integration, static code analysis.


### Other Coding

This category encompasses various utility scripts for tasks such code documentation, mathematical expression generation, error code generation, Git commit message conversion to Markdown, interaction with Google AI tools, Groq tools, Maxima symbolic calculations, PDF text extraction, and CUDA/OpenCL code testing.  These scripts demonstrate the versatility of the project in integrating LLMs with various tools and workflows.

- **files**:
 - `test_GenerateErrorCode.py` - Atempt to automatically generate errors in code as a way of generating examples for LLMs training to correct these errors.
 - `test_pyCUDA.py` - 
 - `test_pymaxima.py` - 
 - `test_pyOpenCL.py` -
 - `test_compile.py` - This script compiles and tests a C++ shared library for n-body simulations (Coulomb interactions), demonstrating the integration of compiled code with Python.
 - `test_coder_forcefield.py` -  This script tests the implementation of a force field equation (likely Lenard-Jones potential) and its derivatives, using LLMs to simplify mathematical expressions.


