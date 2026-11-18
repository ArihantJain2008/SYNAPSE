import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.academic_email_classifier import classify_message


TEST_CASES = [
    (
        {"sender": "professor@christuniversity.in",
         "subject": "Assignment submission deadline"},
        "assignment"
    ),
    (
        {"sender": "examcell@christuniversity.in",
         "subject": "Mid Semester Examination Schedule"},
        "assessment"
    ),
    (
        {"sender": "college@christuniversity.in",
         "subject": "Important announcement for students"},
        "announcement"
    ),
    (
        {"sender": "faculty@christuniversity.in",
         "subject": "Lecture notes and study material"},
        "course_material"
    ),
    (
        {"sender": "faculty@christuniversity.in",
         "subject": "Class cancelled tomorrow"},
        "schedule_change"
    ),
    (
        {"sender": "office@christuniversity.in",
         "subject": "Fee payment information"},
        "general_college"
    ),
    (
        {"sender": "someone@example.com",
         "subject": "Weekend photography"},
        "other"
    )
]


def main():
    print("Testing academic email classifier...\n")

    for message, expected in TEST_CASES:
        result = classify_message(message)

        assert result["category"] == expected, (
            f"Expected {expected}, got {result['category']}"
        )

        print(f"PASS: {expected}")

    # Verify that message bodies are not used.
    first = classify_message({
        "sender": "professor@christuniversity.in",
        "subject": "Assignment submission",
        "body": "This is unrelated private content."
    })

    second = classify_message({
        "sender": "professor@christuniversity.in",
        "subject": "Assignment submission",
        "body": "Completely different content."
    })

    assert first == second

    # Validate input handling.
    try:
        classify_message("invalid")
        raise AssertionError("Invalid input was accepted.")
    except TypeError:
        pass

    print("\nBody independence: PASSED")
    print("Input validation: PASSED")
    print("All classifier tests passed.")


if __name__ == "__main__":
    main()
