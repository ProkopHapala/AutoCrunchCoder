from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

import time
import sys
sys.path.append("../")
from pyCruncher.AgentDeepSeek import AgentDeepSeek

print( "RAG.1" )

# Load the saved vector store
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

print( "RAG.2" )

vector_store = FAISS.load_local("codebase_index", embeddings, allow_dangerous_deserialization=True)

print( "RAG.3" )

# Create DeepSeek agent instead of OpenAI
agent = AgentDeepSeek("deepseek-coder")

print( "RAG.4" )

# Function to query codebase
def query_codebase(question: str, debug_file="debug_rag_query_codebase.md"):
    # Get relevant code snippets
    t0_retrieval = time.time()
    print( "query_codebase().1" )
    docs = vector_store.similarity_search(question)
    print( "query_codebase().1" )
    context = "\n".join(doc.page_content for doc in docs)
    print( "query_codebase().1" )
    
    # Format prompt with context
    prompt = f"""Given this code context:
    {context}
    
    Question: {question}
    Please analyze the code and answer the question."""

    with open(debug_file, "w") as f:  f.write(prompt)
    print( "query_codebase() time(RAG): ", time.time() - t0_retrieval )
    print( "query_codebase() saved ", debug_file  )
    
    t0_llm = time.time()
    # Get response using DeepSeek
    response = agent.query(prompt)
    print ( "query_codebase() time(LLM): ", time.time() - t0_llm )
    return response

# Example usage
result = query_codebase("How does the quaternion normalization work in this codebase?")

with open( "debug_rag_query_codebase_answer.md", "w") as f:  f.write(result.content) 

print(result.content)
