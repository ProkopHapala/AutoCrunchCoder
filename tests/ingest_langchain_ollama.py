"""
pip install langchain
pip install langchain_chroma
ollama pull nomic-embed-text
"""

from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
import chromadb
import hashlib
import os

print("RAG.0")

chroma_client = chromadb.PersistentClient(path="./chroma_db")

print("RAG.0.1")

# Initialize loader for code files
#loader = DirectoryLoader('/home/prokophapala/git/FireCore_cpp_export_mini',     glob="**/*.[ch]pp",   show_progress=True)
loader = DirectoryLoader('/home/prokophapala/git/FireCore_cpp_export_mini',     glob="**/*.*",   show_progress=True)

# Load documents
documents = loader.load()

print("RAG.1")
# Split text into chunks using recursive splitter
text_splitter = RecursiveCharacterTextSplitter(    chunk_size=1000,    chunk_overlap=200 )
print("RAG.2")
texts = text_splitter.split_documents(documents)

# Deduplicate chunks based on content
unique_texts = {}
for text in texts:
    content_hash = hashlib.md5(text.page_content.encode()).hexdigest()
    unique_texts[content_hash] = text
texts = list(unique_texts.values())
print(f"Created {len(texts)} unique text chunks")



print("RAG.3")
# Create embeddings using Ollama's nomic-embed-text model
embeddings = OllamaEmbeddings(model="nomic-embed-text")
print("RAG.4")
# Create and persist vector store using Chroma
vector_store = Chroma.from_documents(documents=texts,embedding=embeddings,persist_directory="./chroma_db")
print("RAG.5")
#vector_store.persist()
# Add documents to the collection
vector_store.add_documents(documents=texts)
print("RAG.6")