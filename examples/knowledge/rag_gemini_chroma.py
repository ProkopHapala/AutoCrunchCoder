#!/usr/bin/env python3

"""
Example demonstrating RAG (Retrieval-Augmented Generation) using Google's Gemini model and ChromaDB.
This example shows how to:
1. Set up ChromaDB with Ollama embeddings
2. Perform semantic search over a codebase
3. Format and deduplicate search results
4. Generate contextual responses using Gemini
"""

import time
from typing import List, Tuple, Dict
from dataclasses import dataclass
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from pyCruncher2.agents.google import AgentGoogle
from pyCruncher2.knowledge.store.chroma import setup_vector_store

@dataclass
class RAGConfig:
    """Configuration for RAG query execution."""
    min_score: float = 0.5
    num_results: int = 8
    debug_prompt_file: str = "debug/rag_query_prompt.md"
    debug_answer_file: str = "debug/rag_query_answer.md"

def deduplicate_docs_and_scores(docs_and_scores: List[Tuple]) -> List[Tuple]:
    """Remove duplicate documents, keeping the one with highest score."""
    unique_chunks: Dict = {}
    for doc, score in docs_and_scores:
        content = doc.page_content
        if content not in unique_chunks or score > unique_chunks[content][1]:
            unique_chunks[content] = (doc, score)
    return [(doc, score) for content, (doc, score) in unique_chunks.items()]

def format_relevant_contexts(docs_and_scores: List[Tuple], min_score: float = 0.5) -> List[str]:
    """Format and filter relevant code chunks with their scores."""
    unique_docs_and_scores = deduplicate_docs_and_scores(docs_and_scores)
    relevant_contexts = []
    
    for i, (doc, score) in enumerate(unique_docs_and_scores):
        if score >= min_score:
            context = f"""#### Code chunk [{i}] (relevance score: {score:.3f})
```C++
{doc.page_content}
```"""
            relevant_contexts.append(context)
    
    return relevant_contexts

def create_rag_prompt(question: str, relevant_contexts: List[str]) -> str:
    """Create a prompt combining the question and relevant code contexts."""
    context_text = '\n\n'.join(relevant_contexts)
    
    return f"""### Read the following source-codes in order to answer following question:

*{question}*

### Context:

There are {len(relevant_contexts)} most relevant chunks of source code speaking about the subject.
Each chunk is shown with its relevance score (higher is more relevant).

{context_text}

### Now answer the question:

*{question}*
"""

def query_codebase(question: str, config: RAGConfig) -> str:
    """
    Query the codebase using RAG with Gemini and ChromaDB.
    
    Args:
        question: The question to answer about the codebase
        config: RAG configuration parameters
    
    Returns:
        str: Generated answer based on retrieved context
    """
    # Initialize components
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vector_store = setup_vector_store("./chroma_db", embeddings)
    agent = AgentGoogle("gemini-flash")
    
    # Time the retrieval process
    t0_retrieval = time.time()
    docs_and_scores = vector_store.similarity_search_with_score(
        question.strip(),
        k=config.num_results
    )
    
    # Format and create prompt
    relevant_contexts = format_relevant_contexts(docs_and_scores, config.min_score)
    prompt = create_rag_prompt(question, relevant_contexts)
    
    # Save debug information
    with open(config.debug_prompt_file, "w") as f:
        f.write(prompt)
    
    print(f"Retrieval time: {time.time() - t0_retrieval:.2f}s")
    
    # Generate response
    t0_llm = time.time()
    response = agent.query(prompt)
    print(f"LLM response time: {time.time() - t0_llm:.2f}s")
    
    # Save response
    with open(config.debug_answer_file, "w") as f:
        f.write(response.text)
    
    return response.text

def main():
    # Configuration
    config = RAGConfig(
        min_score=0.5,
        num_results=8,
        debug_prompt_file="debug/rag_query_prompt.md",
        debug_answer_file="debug/rag_query_answer.md"
    )
    
    # Example questions
    questions = [
        "What interpolation methods are used in GridFF?",
        "Tell me what is GridFF? What is it good for and How it works?",
        "How pi-orbitals are used to calculate the molecular mechanics?"
    ]
    
    # Run queries
    for i, question in enumerate(questions, 1):
        print(f"\n=== Query {i}: {question} ===")
        answer = query_codebase(question, config)
        print("\nAnswer:")
        print(answer)
        print("\n" + "="*80)

if __name__ == "__main__":
    main()
