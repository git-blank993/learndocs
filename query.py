
import chromadb

client = chromadb.PersistentClient(path=f"chroma/drizzle")
collection = client.get_collection("drizzle")
results = collection.query(
    query_texts=["what is drizzle orm?"],
    n_results=5
)

print(results)