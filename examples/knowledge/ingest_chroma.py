#!/usr/bin/env python3

"""
Example demonstrating code ingestion for RAG using LangChain and ChromaDB.
This example shows how to:
1. Load code files from a directory
2. Split code into meaningful chunks
3. Generate embeddings using Ollama
4. Store embeddings in ChromaDB for later retrieval

Requirements:
    pip install langchain langchain_chroma
    ollama pull nomic-embed-text
"""

import os
import hashlib
from dataclasses import dataclass
from typing import List, Optional
import chromadb
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

@dataclass
class IngestConfig:
    """Configuration for code ingestion process."""
    source_dir: str
    db_path: str = "./chroma_db"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    file_pattern: str = "**/*.*"
    embeddings_model: str = "nomic-embed-text"

def setup_chroma_client(db_path: str) -> chromadb.PersistentClient:
    """Initialize ChromaDB client with persistent storage."""
    return chromadb.PersistentClient(path=db_path)

def load_documents(source_dir: str, file_pattern: str) -> List:
    """Load documents from the specified directory."""
    loader = DirectoryLoader(
        source_dir,
        glob=file_pattern,
        show_progress=True
    )
    return loader.load()

def split_documents(documents: List, chunk_size: int, chunk_overlap: int) -> List:
    """Split documents into chunks using recursive character splitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(documents)

def deduplicate_chunks(chunks: List) -> List:
    """Remove duplicate chunks based on content hash."""
    unique_chunks = {}
    for chunk in chunks:
        content_hash = hashlib.md5(chunk.page_content.encode()).hexdigest()
        unique_chunks[content_hash] = chunk
    return list(unique_chunks.values())

def create_vector_store(
    texts: List,
    embeddings: OllamaEmbeddings,
    persist_directory: str
) -> Chroma:
    """Create and persist vector store using ChromaDB."""
    vector_store = Chroma.from_documents(
        documents=texts,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    vector_store.add_documents(documents=texts)
    return vector_store

def ingest_codebase(config: IngestConfig) -> None:
    """
    Main function to ingest codebase into ChromaDB.
    
    Args:
        config: Configuration parameters for ingestion
    """
    print("Setting up ChromaDB client...")
    chroma_client = setup_chroma_client(config.db_path)
    
    print(f"Loading documents from {config.source_dir}...")
    documents = load_documents(config.source_dir, config.file_pattern)
    
    print("Splitting documents into chunks...")
    texts = split_documents(documents, config.chunk_size, config.chunk_overlap)
    
    print("Deduplicating chunks...")
    texts = deduplicate_chunks(texts)
    print(f"Created {len(texts)} unique text chunks")
    
    print("Initializing embeddings model...")
    embeddings = OllamaEmbeddings(model=config.embeddings_model)
    
    print("Creating vector store...")
    vector_store = create_vector_store(texts, embeddings, config.db_path)
    print("Vector store created and persisted successfully!")

def main():
    # Example configuration
    config = IngestConfig(
        source_dir="/home/prokophapala/git/FireCore_cpp_export_mini",
        db_path="./chroma_db",
        chunk_size=1000,
        chunk_overlap=200,
        file_pattern="**/*.*",
        embeddings_model="nomic-embed-text"
    )
    
    # Run ingestion
    ingest_codebase(config)

if __name__ == "__main__":
    main()
