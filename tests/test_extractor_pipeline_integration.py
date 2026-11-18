import json

from services.academic_email_extractor import AcademicEmailExtractor


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def generate(self, system_prompt, user_prompt):
        self.calls += 1
        return json.dumps(self.response)


def seminar_response():
    return {
        "course_or_subject": {"value": None, "evidence": None},
        "title": {"value": None, "evidence": None},
        "instructions": [],
        "deadline": {
            "value": "20 November 2026",
            "evidence": "The department seminar will take place on 20 November 2026."
        },
        "submission_method": {
            "value": "No assignment or submission is required",
            "evidence": "No assignment or submission is required."
        },
        "required_files": [
            {
                "value": "No assignment or submission is required",
                "evidence": "No assignment or submission is required."
            }
        ],
        "important_dates": [
            {
                "label": "Deadline",
                "date_text": "20 November 2026",
                "evidence": "The department seminar will take place on 20 November 2026."
            }
        ],
        "confidence": "high",
        "needs_clarification": False,
        "clarification_questions": []
    }


def assignment_response():
    return {
        "course_or_subject": {
            "value": "Java",
            "evidence": "Java Practical Assignment"
        },
        "title": {
            "value": "JDBC Practical Assignment",
            "evidence": "JDBC Practical Assignment"
        },
        "instructions": [
            {
                "value": "Implement database connectivity",
                "evidence": "Implement database connectivity."
            }
        ],
        "deadline": {
            "value": "20 November 2026",
            "evidence": "Submit by 20 November 2026."
        },
        "submission_method": {
            "value": "Google Classroom",
            "evidence": "Upload to Google Classroom."
        },
        "required_files": [
            {
                "value": ".java file",
                "evidence": "Submit your .java file."
            }
        ],
        "important_dates": [
            {
                "label": "Submission deadline",
                "date_text": "20 November 2026",
                "evidence": "Submit by 20 November 2026."
            }
        ],
        "confidence": "high",
        "needs_clarification": False,
        "clarification_questions": []
    }


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS:", message)


def main():
    print("Testing complete extraction pipeline with fake clients...\n")

    seminar_client = FakeClient(seminar_response())
    seminar_result = AcademicEmailExtractor(
        client=seminar_client
    ).extract({
        "subject": "Department Seminar Announcement",
        "category": "announcement",
        "body": (
            "The department seminar will take place on 20 November 2026. "
            "No assignment or submission is required."
        )
    })

    check(
        seminar_result["deadline"]["value"] is None,
        "Seminar date is not extracted as an assignment deadline"
    )
    check(
        seminar_result["submission_method"]["value"] is None,
        "Negative submission statement is not treated as a submission method"
    )
    check(
        seminar_result["required_files"] == [],
        "Negative submission statement does not create required files"
    )
    check(
        len(seminar_result["important_dates"]) == 1,
        "Valid seminar date is retained"
    )
    check(
        seminar_result["important_dates"][0]["label"] == "Date mentioned",
        "Seminar date is not labelled as a deadline"
    )
    check(
        seminar_client.calls == 1,
        "Seminar extraction uses exactly one fake model response"
    )

    assignment_client = FakeClient(assignment_response())
    assignment_result = AcademicEmailExtractor(
        client=assignment_client
    ).extract({
        "subject": "Java Practical Assignment",
        "category": "assignment",
        "body": (
            "JDBC Practical Assignment. "
            "Implement database connectivity. "
            "Submit by 20 November 2026. "
            "Upload to Google Classroom. "
            "Submit your .java file."
        )
    })

    check(
        assignment_result["deadline"]["value"] == "20 November 2026",
        "Genuine assignment deadline is preserved"
    )
    check(
        assignment_result["important_dates"][0]["label"] == "Submission deadline",
        "Genuine submission deadline label is preserved"
    )
    check(
        assignment_result["required_files"][0]["value"] == ".java file",
        "Genuine required file is preserved"
    )

    print("\nAll pipeline integration tests passed.")


if __name__ == "__main__":
    main()
