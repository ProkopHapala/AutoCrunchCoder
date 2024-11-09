'''
pip install langchain
pip install faiss-cpu
pip install sentence-transformers
pip install langchain-community
pip install unstructured
'''

from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Initialize loader for cpp and h files
loader = DirectoryLoader('/home/prokophapala/git/FireCore_cpp_export',   glob="**/*.[ch]pp",     show_progress=True)

# Load documents
documents = loader.load()

# Split text into chunks
text_splitter = CharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
texts = text_splitter.split_documents(documents)

# Create embeddings using a lightweight local model
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Create and save the vector store
vector_store = FAISS.from_documents(texts, embeddings)
vector_store.save_local("codebase_index")
