from services.embedding_service import EmbeddingService
from services.academic_memory import AcademicMemory

def main():
    embedder = EmbeddingService()
    memory = AcademicMemory()

    questions = [
        "What are the steps involved in JDBC connectivity?",
        "What is the purpose of PreparedStatement?",
        "Which object stores results returned by a SELECT query?",
    ]

    for question in questions:
        print("\n" + "=" * 70)
        print("QUESTION:", question)
        print("=" * 70)

        query_embedding = embedder.embed_query(question)

        results = memory.search(
            query_embedding=query_embedding,
            top_k=3,
            source_type="lecture_notes",
        )

        if not results:
            print("No matching documents found.")
            continue

        for rank, result in enumerate(results, start=1):
            print(f"\nRank: {rank}")
            print(f"Title: {result['title']}")
            print(f"Similarity: {result['similarity']:.4f}")
            print(f"Page: {result['metadata'].get('page')}")
            print("Content:")
            print(result["content"])


if __name__ == "__main__":
    main()
