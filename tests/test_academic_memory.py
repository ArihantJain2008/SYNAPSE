from services.embedding_service import EmbeddingService
from services.academic_memory import AcademicMemory

print("=" * 55)
print("ACADEMICAI - ACADEMIC MEMORY TEST")
print("=" * 55)

embedding_service = EmbeddingService()
memory = AcademicMemory()

documents = [
    {
        "title": "Java JDBC Assignment",
        "content": "Java programming assignment covering JDBC, database connectivity, SQL queries and connection management.",
        "source_type": "assignment"
    },
    {
        "title": "Python Pandas Practical",
        "content": "Python practical involving pandas DataFrames, data analysis and CSV processing.",
        "source_type": "practical"
    },
    {
        "title": "History Nationalism Notes",
        "content": "History notes covering nationalism in nineteenth-century Europe and the unification of Germany.",
        "source_type": "notes"
    }
]

print("\nGenerating and storing documents...")

for doc in documents:
    vector = embedding_service.embed_document(doc["content"])

    document_id = memory.add_document(
        title=doc["title"],
        content=doc["content"],
        embedding=vector,
        source_type=doc["source_type"],
        metadata={"test_data": True}
    )

    print(f"Stored: {doc['title']} (ID: {document_id})")

print("\nTotal stored documents:", memory.count())

query = "Find my Java JDBC database assignment."

print("\nSearching academic memory...")
query_vector = embedding_service.embed_query(query)

results = memory.search(query_vector, top_k=3)

for index, result in enumerate(results, start=1):
    print(f"\nRank: {index}")
    print("Title:", result["title"])
    print("Source:", result["source_type"])
    print("Similarity:", round(result["similarity"], 4))
    print("Content:", result["content"])

print("\nAcademic memory test completed.")
