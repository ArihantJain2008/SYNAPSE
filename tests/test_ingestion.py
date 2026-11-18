from services.ingestion_service import IngestionService

service = IngestionService()

result = service.ingest(
    "workspace/jdbc_notes.txt",
    source_type="lecture_notes"
)

print("\nINGESTION RESULT")
print("================")

for key, value in result.items():
    print(f"{key}: {value}")
