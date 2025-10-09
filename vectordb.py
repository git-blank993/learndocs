import chromadb
from typing import List
client = chromadb.EphemeralClient()




def create_collection(name:str):
    return client.get_or_create_collection(name=name)

def add_data(c, documents: List[str]):
    c.upsert(
    documents=[
        "This is a document about pineapple",
        "This is a document about oranges"
    ],
    ids=["id1", "id2"]
)

def get_result(c, query:str, k:int = 2):
    return c.query(
    query_texts=query,
    n_results=k
)
