#!/usr/bin/env python3

"""
Example demonstrating RAG (Retrieval-Augmented Generation) using DeepSeek Coder and FAISS.
This example shows how to:
1. Set up FAISS with Hugging Face embeddings
2. Load and query a persisted vector store
3. Generate contextual code explanations using DeepSeek
4. Measure and log retrieval and inference times
"""

import time
from typing import Optional
from dataclasses import dataclass
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from pyCruncher2.agents.deepseek import AgentDeepSeek
from pyCruncher2.knowledge.store.faiss import setup_vector_store

@dataclass
class RAGConfig:
    """Configuration for RAG query execution."""
    model_name: str = "deepseek-coder"
    embeddings_model: str = "all-MiniLM-L6-v2"
    index_path: str = "codebase_index"
    debug_prompt_file: str = "debug/rag_query_prompt.md"
    debug_answer_file: str = "debug/rag_query_answer.md"

def create_rag_prompt(question: str, context: str) -> str:
    """Create a prompt combining the question and code context."""
    return f"""Given this code context:
{context}

Question: {question}
Please analyze the code and answer the question."""

def query_codebase(question: str, config: RAGConfig) -> str:
    """
    Query the codebase using RAG with DeepSeek and FAISS.
    
    Args:
        question: The question to answer about the codebase
        config: RAG configuration parameters
    
    Returns:
        str: Generated answer based on retrieved context
    """
    # Initialize components
    embeddings = HuggingFaceEmbeddings(model_name=config.embeddings_model)
    vector_store = setup_vector_store(config.index_path, embeddings)
    agent = AgentDeepSeek(config.model_name)
    
    # Time the retrieval process
    t0_retrieval = time.time()
    docs = vector_store.similarity_search(question)
    context = "\n".join(doc.page_content for doc in docs)
    
    # Create and save prompt
    prompt = create_rag_prompt(question, context)
    with open(config.debug_prompt_file, "w") as f:
        f.write(prompt)
    
    print(f"Retrieval time: {time.time() - t0_retrieval:.2f}s")
    
    # Generate response
    t0_llm = time.time()
    response = agent.query(prompt)
    print(f"LLM response time: {time.time() - t0_llm:.2f}s")
    
    # Save response
    with open(config.debug_answer_file, "w") as f:
        f.write(response.content)
    
    return response.content

def main():
    # Configuration
    config = RAGConfig(
        model_name="deepseek-coder",
        embeddings_model="all-MiniLM-L6-v2",
        index_path="codebase_index",
        debug_prompt_file="debug/rag_query_prompt.md",
        debug_answer_file="debug/rag_query_answer.md"
    )
    
    # Example questions
    questions = [
        "How does the quaternion normalization work in this codebase?",
        "What are the main data structures used for molecular geometry?",
        "How are force field parameters handled in the code?"
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
