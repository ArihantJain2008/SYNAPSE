import json
import time
import traceback

from services.academic_email_extractor import AcademicEmailExtractor
from services.npu_generation_service import NPUGenerationService
from services.openvino_genai_client import OpenVINOGenAIClient


MESSAGES = [
    {
        "name": "Seminar announcement — event date, no assignment",
        "message": {
            "subject": "Department Seminar Announcement",
            "category": "announcement",
            "body": (
                "The department seminar will take place on 20 November 2026. "
                "Students are invited to attend. "
                "No assignment or submission is required."
            )
        }
    },
    {
        "name": "Java assignment — explicit submission deadline",
        "message": {
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
            )
        }
    }
]


def show_result(name, result, elapsed):
    print("\n" + "=" * 65)
    print(name)
    print("=" * 65)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nInference + extraction time: {elapsed:.2f} seconds")


def main():
    print("LIVE QWEN3-0.6B NPU EXTRACTION TEST")
    print("Device: Intel NPU")
    print("Model: models/qwen3-0.6b-npu")
    print("Generation: deterministic, max 384 tokens")
    print("Gmail access: disabled")
    print("Database writes: disabled")
    print("\nInitializing one reusable NPU pipeline...")

    service = NPUGenerationService(
        device="NPU",
        max_new_tokens=384
    )
    client = OpenVINOGenAIClient(service=service)
    extractor = AcademicEmailExtractor(client=client)

    outcomes = []

    for item in MESSAGES:
        print(f"\nRunning: {item['name']}")
        started = time.perf_counter()

        try:
            result = extractor.extract(item["message"])
            elapsed = time.perf_counter() - started

            show_result(item["name"], result, elapsed)
            outcomes.append((item["name"], result, None))

        except Exception as exc:
            elapsed = time.perf_counter() - started
            print(f"\nFAILED: {type(exc).__name__}: {exc}")
            print(f"Elapsed: {elapsed:.2f} seconds")
            traceback.print_exc()
            outcomes.append((item["name"], None, exc))

    print("\n" + "=" * 65)
    print("SEMANTIC CHECKS")
    print("=" * 65)

    failures = []

    seminar = outcomes[0][1]
    assignment = outcomes[1][1]

    if seminar is not None:
        checks = [
            (
                seminar["deadline"]["value"] is None,
                "Seminar event date is not treated as an assignment deadline"
            ),
            (
                seminar["submission_method"]["value"] is None,
                "No submission method is invented for the seminar"
            ),
            (
                len(seminar["required_files"]) == 0,
                "No required files are invented for the seminar"
            ),
        ]

        for passed, description in checks:
            print(("PASS: " if passed else "FAIL: ") + description)
            if not passed:
                failures.append(description)
    else:
        failures.append("Seminar extraction failed")

    if assignment is not None:
        checks = [
            (
                assignment["deadline"]["value"] == "20 November 2026",
                "Explicit assignment deadline is extracted correctly"
            ),
            (
                assignment["submission_method"]["value"] is not None
                and "Google Classroom"
                in assignment["submission_method"]["value"],
                "Google Classroom submission method is extracted"
            ),
            (
                len(assignment["required_files"]) >= 2
                and any(".java" in item["value"].lower()
                        for item in assignment["required_files"])
                and any("pdf" in item["value"].lower()
                        for item in assignment["required_files"]),
                "Java source file and PDF screenshots are extracted"
            ),
        ]

        for passed, description in checks:
            print(("PASS: " if passed else "FAIL: ") + description)
            if not passed:
                failures.append(description)
    else:
        failures.append("Assignment extraction failed")

    print("\n" + "=" * 65)
    if failures:
        print(f"RESULT: {len(failures)} CHECK(S) FAILED")
        for failure in failures:
            print(" -", failure)
        raise SystemExit(1)

    print("RESULT: ALL LIVE NPU SEMANTIC CHECKS PASSED")
    print("Both emails were processed using the same NPU service instance.")


if __name__ == "__main__":
    main()
