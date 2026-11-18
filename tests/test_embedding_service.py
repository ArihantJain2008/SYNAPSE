import numpy as np
from services.embedding_service import EmbeddingService

print("=" * 55)
print("ACADEMICAI - NPU EMBEDDING SERVICE TEST")
print("=" * 55)

service = EmbeddingService()

documents = [
    "Java programming assignment covering JDBC and database connectivity.",
    "Python practical assignment involving pandas and data analysis.",
    "History assignment about nationalism in nineteenth-century Europe."
]

query = "I need my Java JDBC assignment instructions."

print("\nGenerating document embeddings...")
document_vectors = [
    service.embed_document(text)
    for text in documents
]

print("Generating query embedding...")
query_vector = service.embed_query(query)

print("\nEmbedding dimensions:", query_vector.shape)
print("Vector dtype:", query_vector.dtype)
print("Vector norm:", np.linalg.norm(query_vector))

print("\nSearch similarity results:")

scores = [
    service.similarity(query_vector, vector)
    for vector in document_vectors
]

ranked = sorted(
    zip(documents, scores),
    key=lambda item: item[1],
    reverse=True
)

for text, score in ranked:
    print(f"\nSimilarity: {score:.4f}")
    print("Document:", text)

print("\nAll embedding service tests completed.")
