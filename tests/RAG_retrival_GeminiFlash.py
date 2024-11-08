from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

import sys
sys.path.append("../")
from pyCruncher.AgentGoogle import AgentGoogle
import time

print( "RAG.1" )

# Load the saved vector store
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
print( "RAG.2" )

vector_store = FAISS.load_local("codebase_index", embeddings, allow_dangerous_deserialization=True)
print( "RAG.3" )
# Create Google agent with Gemini model
#agent = AgentGoogle("gemini-1.5-flash-002")
agent = AgentGoogle("gemini-flash")

print( "RAG.4" )

def query_codebase(question: str, debug_file="debug_queries.md"):
    # Time the retrieval
    t0_retrieval = time.time()
    docs = vector_store.similarity_search(question)
    print( "query_codebase().1" )
    context = "\n".join(doc.page_content for doc in docs)
    print( "query_codebase().1" )
    retrieval_time = time.time() - t0_retrieval
    print( "query_codebase().1" )
    
    prompt = f"""Given this code context:
    {context}
    
    Question: {question}"""
    
    with open(debug_file, "w") as f:  f.write(prompt)
    print( "query_codebase() time(RAG): ", time.time() - t0_retrieval )
    print( "query_codebase() saved ", debug_file  )
    
    # Time the LLM response
    t0_llm = time.time()
    response = agent.query(prompt)
    llm_time = time.time() - t0_llm

    print ( "query_codebase() time(LLM): ", time.time() - t0_llm )
    
    return response

# Example usage
result = query_codebase("How does the quaternion normalization work in this codebase?")

print(result.text)

with open( "debug_rag_query_codebase_answer.md", "w") as f:  f.write(result.text) 
