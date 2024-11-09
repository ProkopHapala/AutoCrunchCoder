from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
import time
import sys
sys.path.append("../")
from pyCruncher.AgentGoogle import AgentGoogle
import hashlib

print("RAG.1")

# Initialize embeddings and load persisted vector store
embeddings = OllamaEmbeddings(model="nomic-embed-text")
print("RAG.2")

vector_store = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
print("RAG.3")

# Create Google agent with Gemini model
agent = AgentGoogle("gemini-flash")
print("RAG.4")


# def format_relevant_contexts(docs_and_scores, min_score: float = 0.5):
#     relevant_contexts = []
#     i=0
#     for doc, score in docs_and_scores:
#         if score >= min_score:
#             relevant_contexts.append(f"#### Code chunk [{i}] (relevance score: {score:.3f}) \n```C++\n{doc.page_content}\n```")
#             i+=1
#     return relevant_contexts

def deduplicate_docs_and_scores(docs_and_scores):
    unique_chunks = {}
    for doc, score in docs_and_scores:
        content = doc.page_content
        if content not in unique_chunks or score > unique_chunks[content][1]:
            unique_chunks[content] = (doc, score)
    return [(doc, score) for content, (doc, score) in unique_chunks.items()]

def format_relevant_contexts(docs_and_scores, min_score: float = 0.5):
    # First deduplicate
    unique_docs_and_scores = deduplicate_docs_and_scores(docs_and_scores)
    # Then format chunks that meet threshold
    i=0
    relevant_contexts = []
    for doc, score in unique_docs_and_scores:
        if score >= min_score:
             relevant_contexts.append(f"#### Code chunk [{i}] (relevance score: {score:.3f}) \n```C++\n{doc.page_content}\n```")
             i+=1
    return relevant_contexts


def query_codebase(question: str, debug_file="debug_rag_query_codebase.md" , k: int = 8, min_score: float = 0.5 ):
    # Time the retrieval
    question = question.strip()
    t0_retrieval = time.time()
    #docs = vector_store.similarity_search(question)
    docs_and_scores = vector_store.similarity_search_with_score(question, k=k)

    relevant_contexts = format_relevant_contexts(docs_and_scores, min_score)

    print("query_codebase().1")
    #context = "\n".join(doc.page_content for doc in docs)
    context = '\n\n'.join(relevant_contexts)
    print("query_codebase().2")
    retrieval_time = time.time() - t0_retrieval
    print("query_codebase().3")
    
    prompt = f"""
### Read the following source-codes in order to answer following question:

*{question}*

### Context:

There are {len(relevant_contexts)} most relevant chunks of source code speaking about the subject.
Each chunk is shown with its relevance score (higher is more relevant).

{context}

### Now answer the question:

*{question}*
"""
    
    with open(debug_file, "w") as f:  f.write(prompt)
    print("query_codebase() time(RAG): ", time.time() - t0_retrieval)
    print("query_codebase() saved ", debug_file)
    
    # Time the LLM response
    t0_llm = time.time()
    response = agent.query(prompt)
    llm_time = time.time() - t0_llm
    
    print("query_codebase() time(LLM): ", time.time() - t0_llm)
    
    return response

# Example usage
#result = query_codebase("Tell me what is GridFF? What is it good for and How it works ?")
result = query_codebase("What interpolation methods are used in GridFF ? ")
#result = query_codebase("How pi-orbitals are used to calculate the molecula mechanics?")
#print(result.text)

out_file = "debug_rag_query_codebase_answer.md"

with open(out_file, "w") as f:  f.write(result.text)
print("query_codebase(), output saved to: ", out_file)