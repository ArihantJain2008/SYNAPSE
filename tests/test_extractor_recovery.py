import json

from services.academic_email_extractor import AcademicEmailExtractor


class FakeClient:
    def __init__(self, response):
        self.response = response

    def generate(self, system_prompt, user_prompt):
        return json.dumps(self.response)


def response():
    return {
        "course_or_subject": {"value": None, "evidence": None},
        "title": {"value": None, "evidence": None},
        "instructions": [],
        "deadline": {"value": None, "evidence": None},
        "submission_method": {"value": "Google Classroom", "evidence": "Google Classroom"},
        "required_files": [
            {"value": "Java source file", "evidence": "Java source file"}
        ],
        "important_dates": [],
        "confidence": "high",
        "needs_clarification": False,
        "clarification_questions": [],
    }


def run():
    # Explicit deadline must be recovered.
    data = response()
    result = AcademicEmailExtractor(client=FakeClient(data)).extract({
        "subject": "Java Practical Assignment",
        "category": "assignment",
        "body": (
            "Implement database connectivity. "
            "Submit by 20 November 2026. "
            "Upload to Google Classroom. "
            "Submit your .java source file."
        ),
    })

    assert result["deadline"]["value"] == "20 November 2026"
    assert result["deadline"]["evidence"] == "Submit by 20 November 2026."
    print("PASS: Missing explicit deadline is recovered")

    assert result["required_files"][0]["value"] == ".java source file"
    assert result["required_files"][0]["evidence"] == ".java source file"
    print("PASS: Explicit .java extension is preserved")

    # An event date must not be recovered as a deadline.
    data = response()
    data["required_files"] = []
    data["submission_method"] = {"value": None, "evidence": None}
    result = AcademicEmailExtractor(client=FakeClient(data)).extract({
        "subject": "Department Seminar Announcement",
        "category": "announcement",
        "body": (
            "The department seminar will take place on "
            "20 November 2026. Students are invited to attend."
        ),
    })

    assert result["deadline"]["value"] is None
    print("PASS: Event date is not promoted to a deadline")

    # "Due 20 November" must also be recognized.
    data = response()
    data["required_files"] = []
    data["submission_method"] = {"value": None, "evidence": None}
    result = AcademicEmailExtractor(client=FakeClient(data)).extract({
        "subject": "Java Assignment",
        "category": "assignment",
        "body": "The assignment is due 20 November 2026.",
    })

    assert result["deadline"]["value"] == "20 November 2026"
    print("PASS: 'Due [date]' deadline wording is recognized")


    # Explicitly requested PDF screenshots must be recovered.
    data = response()
    result = AcademicEmailExtractor(client=FakeClient(data)).extract({
        "subject": "Java Practical Assignment",
        "category": "assignment",
        "body": (
            "Upload your .java source file and PDF screenshots "
            "to Google Classroom."
        ),
    })

    pdf_files = [
        item for item in result["required_files"]
        if "pdf screenshots" in item["value"].casefold()
    ]
    assert len(pdf_files) == 1
    assert pdf_files[0]["evidence"] == "PDF screenshots"
    print("PASS: Explicit PDF screenshots requirement is recovered")

    # A passive mention must not become a submission requirement.
    data = response()
    data["required_files"] = []
    data["submission_method"] = {"value": None, "evidence": None}
    result = AcademicEmailExtractor(client=FakeClient(data)).extract({
        "subject": "Lecture Resources",
        "category": "course_material",
        "body": (
            "The PDF screenshots from last year's project "
            "are available in the lecture archive."
        ),
    })

    assert result["required_files"] == []
    print("PASS: Passive PDF screenshot mention is not treated as required")

    # Recovery must not create duplicate file entries.
    data = response()
    data["required_files"].append({
        "value": "PDF screenshots",
        "evidence": "PDF screenshots",
    })
    result = AcademicEmailExtractor(client=FakeClient(data)).extract({
        "subject": "Java Practical Assignment",
        "category": "assignment",
        "body": (
            "Upload your .java source file and PDF screenshots "
            "to Google Classroom."
        ),
    })

    pdf_files = [
        item for item in result["required_files"]
        if "pdf screenshots" in item["value"].casefold()
    ]
    assert len(pdf_files) == 1
    print("PASS: Existing PDF requirement is not duplicated")

    print("\nAll recovery regression tests passed.")


if __name__ == "__main__":
    run()
