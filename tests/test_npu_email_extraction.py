import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from services.academic_email_extractor import AcademicEmailExtractor

message = {
    "subject": "Java Practical Assignment - JDBC",
    "category": "assignment",
    "body": (
        "Java Practical Assignment: JDBC.\n"
        "Implement database connectivity using JDBC.\n"
        "Create a Java program to connect to a database and perform "
        "insert, update, delete and display operations.\n"
        "Submit by 20 November 2026.\n"
        "Upload your .java source file and PDF screenshots "
        "to Google Classroom."
    ),
}

print("Starting academic extraction using the NPU...")
extractor = AcademicEmailExtractor()
result = extractor.extract(message)

print("\n========== EXTRACTED RESULT ==========")
import json
print(json.dumps(result, indent=2, ensure_ascii=False))
print("======================================")
