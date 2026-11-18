import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.academic_email_extractor import AcademicEmailExtractor

extractor = AcademicEmailExtractor()

cases = [
    {
        "name": "Clear assignment with deadline",
        "message": {
            "subject": "Java Programming Assignment 3",
            "category": "assignment",
            "body": """
Dear Students,

Complete Assignment 3 on JDBC connectivity.
You must implement database connection and CRUD operations.

Submit by 20 November 2026.
Upload your work to Google Classroom.
Submit your Java source file and a PDF containing screenshots.

Regards,
Course Faculty
"""
        },
        "expected_deadline": "20 November 2026"
    },
    {
        "name": "Assignment without a deadline",
        "message": {
            "subject": "Python Practical Assignment",
            "category": "assignment",
            "body": """
Dear Students,

Prepare a Python program using Pandas to analyse a CSV dataset.
Submit your .py file through Google Classroom.

Further submission details will be announced later.
"""
        },
        "expected_deadline": None
    },
    {
        "name": "Schedule change",
        "message": {
            "subject": "Change in Java Practical Schedule",
            "category": "schedule_change",
            "body": """
Dear Students,

The Java practical examination originally scheduled for
22 November 2026 will now be conducted on 25 November 2026
at 10:00 AM in Lab 3.

Please bring your college ID card.
"""
        },
        "expected_deadline": None
    }
]

for index, case in enumerate(cases, start=1):
    print("\n" + "=" * 65)
    print(f"CASE {index}: {case['name']}")
    print("=" * 65)

    try:
        result = extractor.extract(case["message"])
        print(json.dumps(result, indent=2, ensure_ascii=False))

        expected = case["expected_deadline"]
        actual = result["deadline"]["value"]

        if actual == expected:
            print("PASS: Expected deadline result matches.")
        else:
            print(f"WARNING: Expected {expected!r}, received {actual!r}.")

    except Exception as exc:
        print(f"EXTRACTION FAILED: {type(exc).__name__}: {exc}")

print("\nLive local-model evaluation finished.")
