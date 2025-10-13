import chromadb
from typing import List




def create_collection(name:str):
    client = chromadb.PersistentClient(path=f"chroma/{name}")
    return client.get_or_create_collection(name=name)

def add_data(c:chromadb.Collection, documents: List[str], ids: List[str],metadatas:List[chromadb.Metadata]):
    c.upsert(
    documents=documents,
    ids=ids,
    metadatas=metadatas
)

def get_result(c:chromadb.Collection, query:str, k:int = 2):
    return c.query(
    query_texts=query,
    n_results=k
)
