import json
import time

from services.academic_email_extractor import AcademicEmailExtractor
from services.npu_generation_service import NPUGenerationService
from services.openvino_genai_client import OpenVINOGenAIClient


def print_result(name, result, checks):
    print(f"\n{'=' * 65}")
    print(name)
    print("=" * 65)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    for description, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {description}")

    return all(passed for _, passed in checks)


def main():
    print("AcademicAI NPU edge-case evaluation")
    print("Device: Intel AI Boost NPU")
    print("Model: Qwen3-0.6B")
    print("Running sequentially. Do not start another model.")

    service = NPUGenerationService(max_new_tokens=384)
    client = OpenVINOGenAIClient(service=service)
    extractor = AcademicEmailExtractor(client=client)

    results = []

    # CASE 1: Assignment without a deadline.
    case_1 = {
        "subject": "Java Practical Assignment - JDBC",
        "category": "assignment",
        "body": (
            "Java Practical Assignment: JDBC.\n"
            "Implement database connectivity using JDBC.\n"
            "Create a Java program to connect to a database and perform "
            "insert, update, delete and display operations.\n"
            "Upload your Java source file and PDF screenshots to Google Classroom."
        ),
    }

    print("\n\nCASE 1: Missing deadline")
    start = time.perf_counter()
    try:
        result = extractor.extract(case_1)
        elapsed = time.perf_counter() - start

        checks = [
            (
                "Deadline remains null",
                result["deadline"]["value"] is None,
            ),
            (
                "No unsupported deadline evidence",
                result["deadline"]["evidence"] is None,
            ),
            (
                "Confidence is not high when deadline is missing",
                result["confidence"] in {"low", "medium"},
            ),
            (
                "Missing deadline alone does not trigger clarification",
                not result["needs_clarification"],
            ),
        ]

        results.append(print_result("CASE 1 RESULT", result, checks))
        print(f"Inference time: {elapsed:.2f} seconds")
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        results.append(False)

    # CASE 2: Conflicting deadlines.
    case_2 = {
        "subject": "Database Assignment - Final Submission",
        "category": "assignment",
        "body": (
            "Complete the database assignment and upload it to Google Classroom.\n"
            "The assignment must be submitted by 20 November 2026.\n"
            "Correction: the final submission deadline is 22 November 2026.\n"
            "Use the final deadline when planning your submission."
        ),
    }

    print("\n\nCASE 2: Conflicting deadlines")
    start = time.perf_counter()
    try:
        result = extractor.extract(case_2)
        elapsed = time.perf_counter() - start

        checks = [
            (
                "Conflicting dates are not silently treated as certain",
                result["needs_clarification"]
                or result["confidence"] == "low",
            ),
            (
                "If clarification is required, a question is provided",
                (
                    not result["needs_clarification"]
                    or len(result["clarification_questions"]) > 0
                ),
            ),
        ]

        results.append(print_result("CASE 2 RESULT", result, checks))
        print(f"Inference time: {elapsed:.2f} seconds")
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        results.append(False)

    # CASE 3: College announcement, not an assignment.
    case_3 = {
        "subject": "Department Seminar Announcement",
        "category": "announcement",
        "body": (
            "The Computer Science Department is organizing a seminar "
            "on Artificial Intelligence.\n"
            "The seminar will take place on 20 November 2026 at 10:00 AM "
            "in the college auditorium.\n"
            "All students are encouraged to attend.\n"
            "No assignment or submission is required."
        ),
    }

    print("\n\nCASE 3: College announcement")
    start = time.perf_counter()
    try:
        result = extractor.extract(case_3)
        elapsed = time.perf_counter() - start

        checks = [
            (
                "Announcement date is not invented as a submission deadline",
                result["deadline"]["value"] is None,
            ),
            (
                "No assignment submission method is invented",
                result["submission_method"]["value"] is None,
            ),
        ]

        results.append(print_result("CASE 3 RESULT", result, checks))
        print(f"Inference time: {elapsed:.2f} seconds")
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        results.append(False)

    # CASE 4: Promotional email must be rejected before model inference.
    print("\n\nCASE 4: Promotional email rejection")
    try:
        extractor.extract({
            "subject": "Special shopping discount",
            "category": "promotional",
            "body": "Get 50% off on selected products today.",
        })
        print("FAIL: Promotional email was not rejected")
        results.append(False)
    except ValueError as exc:
        print(f"PASS: Promotional email rejected: {exc}")
        results.append(True)

    print("\n\n" + "=" * 65)
    print("EVALUATION SUMMARY")
    print("=" * 65)
    print(f"Passed: {sum(results)}/{len(results)}")
    print(f"Failed: {len(results) - sum(results)}/{len(results)}")

    if all(results):
        print("All evaluation checks passed.")
    else:
        print("Some checks failed. Review the outputs before integration.")


if __name__ == "__main__":
    main()
