import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json

from services.academic_email_extractor import AcademicEmailExtractor


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


def valid_response():
    return {
        "course_or_subject": {
            "value": "Java",
            "evidence": "Java Practical Assignment",
        },
        "title": {
            "value": "JDBC Practical Assignment",
            "evidence": "JDBC Practical Assignment",
        },
        "instructions": [
            {
                "value": "Implement database connectivity",
                "evidence": "Implement database connectivity",
            }
        ],
        "deadline": {
            "value": "20 November 2026",
            "evidence": "Submit by 20 November 2026",
        },
        "submission_method": {
            "value": "Google Classroom",
            "evidence": "Upload to Google Classroom",
        },
        "required_files": [
            {
                "value": ".java file",
                "evidence": "Submit your .java file",
            }
        ],
        "important_dates": [
            {
                "label": "Submission deadline",
                "date_text": "20 November 2026",
                "evidence": "Submit by 20 November 2026",
            }
        ],
        "confidence": "high",
        "needs_clarification": False,
        "clarification_questions": [],
    }


def check(condition, description):
    if not condition:
        raise AssertionError(description)
    print(f"PASS: {description}")


def expect_error(function, description):
    try:
        function()
    except (ValueError, TypeError):
        print(f"PASS: {description}")
        return
    raise AssertionError(description)


def main():
    print("Testing academic email extractor...\n")

    body = (
        "JDBC Practical Assignment. "
        "Implement database connectivity. "
        "Submit by 20 November 2026. "
        "Upload to Google Classroom. "
        "Submit your .java file."
    )

    response = valid_response()
    client = FakeClient(json.dumps(response))
    extractor = AcademicEmailExtractor(client=client)

    result = extractor.extract({
        "subject": "Java Practical Assignment",
        "category": "assignment",
        "body": body,
    })

    check(
        result["title"]["value"] == "JDBC Practical Assignment",
        "Valid assignment title is extracted",
    )
    check(
        result["deadline"]["value"] == "20 November 2026",
        "Deadline is extracted as written",
    )
    check(
        result["submission_method"]["value"] == "Google Classroom",
        "Submission method is extracted",
    )
    check(
        len(result["required_files"]) == 1,
        "Required file information is extracted",
    )
    check(
        len(client.calls) == 1,
        "Local model client is called once",
    )
    check(
        "untrusted data" in client.calls[0][0].lower(),
        "System prompt treats email content as untrusted",
    )

    missing_deadline = valid_response()
    missing_deadline["deadline"] = {"value": None, "evidence": None}
    missing_deadline["important_dates"] = []
    missing_deadline["needs_clarification"] = False
    missing_deadline["clarification_questions"] = []
    missing_deadline["confidence"] = "high"

    missing_client = FakeClient(json.dumps(missing_deadline))
    missing_result = AcademicEmailExtractor(
        client=missing_client
    ).extract({
        "subject": "Java Practical Assignment",
        "category": "assignment",
        "body": "JDBC Practical Assignment. Implement database connectivity. Upload to Google Classroom. Submit your .java file.",
    })

    check(
        missing_result["deadline"]["value"] is None,
        "Missing deadline remains null instead of being invented",
    )
    check(
        not missing_result["needs_clarification"],
        "Missing deadline alone does not trigger clarification",
    )
    check(
        missing_result["clarification_questions"] == [],
        "No deadline-only question is retained",
    )
    check(
        missing_result["confidence"] == "medium",
        "Missing assignment deadline downgrades confidence",
    )

    invented = valid_response()
    invented["deadline"] = {
        "value": "25 November 2026",
        "evidence": "Submit by 25 November 2026",
    }

    expect_error(
        lambda: AcademicEmailExtractor(
            client=FakeClient(json.dumps(invented))
        ).extract({
            "subject": "Java Practical Assignment",
            "category": "assignment",
            "body": body,
        }),
        "Invented evidence is rejected",
    )

    expect_error(
        lambda: AcademicEmailExtractor(
            client=FakeClient("not valid json")
        ).extract({
            "subject": "Java Practical Assignment",
            "category": "assignment",
            "body": body,
        }),
        "Malformed JSON is rejected",
    )

    expect_error(
        lambda: extractor.extract({
            "subject": "Special offer",
            "category": "promotional",
            "body": "An offer for you.",
        }),
        "Promotional messages cannot enter extraction",
    )

    expect_error(
        lambda: extractor.extract({
            "subject": "Java assignment",
            "category": "assignment",
            "body": "   ",
        }),
        "Empty message bodies are rejected",
    )

    invalid_questions = valid_response()
    invalid_questions["needs_clarification"] = True
    invalid_questions["clarification_questions"] = []

    expect_error(
        lambda: AcademicEmailExtractor(
            client=FakeClient(json.dumps(invalid_questions))
        ).extract({
            "subject": "Java Practical Assignment",
            "category": "assignment",
            "body": body,
        }),
        "Clarification flag requires at least one question",
    )


    mismatched_deadline = valid_response()
    mismatched_deadline["deadline"] = {
        "value": "25 November 2026",
        "evidence": "Submit by 20 November 2026",
    }

    expect_error(
        lambda: AcademicEmailExtractor(
            client=FakeClient(json.dumps(mismatched_deadline))
        ).extract({
            "subject": "Java Practical Assignment",
            "category": "assignment",
            "body": body,
        }),
        "Deadline contradicting its evidence is rejected",
    )

    mismatched_date = valid_response()
    mismatched_date["important_dates"][0]["date_text"] = "25 November 2026"

    expect_error(
        lambda: AcademicEmailExtractor(
            client=FakeClient(json.dumps(mismatched_date))
        ).extract({
            "subject": "Java Practical Assignment",
            "category": "assignment",
            "body": body,
        }),
        "Important date contradicting its evidence is rejected",
    )


    no_subject = valid_response()
    no_subject["course_or_subject"] = {"value": None, "evidence": None}
    fallback_result = AcademicEmailExtractor(
        client=FakeClient(json.dumps(no_subject))
    ).extract({
        "subject": "Java Practical Assignment - JDBC",
        "category": "assignment",
        "body": body,
    })
    check(
        fallback_result["course_or_subject"] == {
            "value": "Java",
            "evidence": "Java Practical Assignment - JDBC",
        },
        "Clear course name is inferred from subject line",
    )

    generic_subject = valid_response()
    generic_subject["course_or_subject"] = {"value": None, "evidence": None}
    generic_subject["deadline"] = {"value": None, "evidence": None}
    generic_subject["important_dates"] = []

    body_without_deadline = body.replace(
        "Submit by 20 November 2026. ", ""
    )

    generic_result = AcademicEmailExtractor(
        client=FakeClient(json.dumps(generic_subject))
    ).extract({
        "subject": "Important Update",
        "category": "assignment",
        "body": body_without_deadline,
    })
    check(
        generic_result["course_or_subject"]["value"] is None,
        "Generic subject does not produce a guessed course",
    )
    check(
        generic_result["confidence"] == "low",
        "Missing subject and assignment deadline produce low confidence",
    )

    ambiguous = valid_response()
    ambiguous["needs_clarification"] = True
    ambiguous["clarification_questions"] = [
        "Which of the two listed projects should be submitted?"
    ]
    ambiguous_result = AcademicEmailExtractor(
        client=FakeClient(json.dumps(ambiguous))
    ).extract({
        "subject": "Java Practical Assignment",
        "category": "assignment",
        "body": body,
    })
    check(
        ambiguous_result["needs_clarification"],
        "Genuine ambiguity still triggers clarification",
    )
    check(
        ambiguous_result["confidence"] == "low",
        "Clarification requirement downgrades confidence",
    )

    inconsistent = valid_response()
    inconsistent["clarification_questions"] = ["Which file is required?"]
    expect_error(
        lambda: AcademicEmailExtractor(
            client=FakeClient(json.dumps(inconsistent))
        ).extract({
            "subject": "Java Practical Assignment",
            "category": "assignment",
            "body": body,
        }),
        "Inconsistent clarification flag and questions are rejected",
    )

    print("\nAll academic email extractor tests passed.")


if __name__ == "__main__":
    main()

