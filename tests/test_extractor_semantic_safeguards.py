from services.academic_email_extractor import (
    _normalize_nullable_facts,
    _apply_semantic_safeguards,
)

passed = 0

def check(description, condition):
    global passed
    if not condition:
        raise AssertionError(description)
    passed += 1
    print(f"PASS: {description}")


# 1. Literal null normalization
data = {
    "deadline": {"value": "null", "evidence": None}
}
_normalize_nullable_facts(data)
check(
    "Literal null deadline becomes an actual null",
    data["deadline"] == {"value": None, "evidence": None},
)


# 2. Event date must not become an assignment deadline
data = {
    "deadline": {
        "value": "20 November 2026",
        "evidence": "The seminar will be held on 20 November 2026.",
    },
    "submission_method": {"value": None, "evidence": None},
    "required_files": [],
    "important_dates": [],
}
_apply_semantic_safeguards(data)
check(
    "Event date without deadline language is not accepted as a deadline",
    data["deadline"]["value"] is None,
)


# 3. A supported deadline must survive
data = {
    "deadline": {
        "value": "22 November 2026",
        "evidence": "Submit your assignment by 22 November 2026.",
    },
    "submission_method": {"value": None, "evidence": None},
    "required_files": [],
    "important_dates": [],
}
_apply_semantic_safeguards(data)
check(
    "Explicit submission deadline is preserved",
    data["deadline"]["value"] == "22 November 2026",
)


# 4. Contradictory evidence must remain available for validator rejection
data = {
    "deadline": {
        "value": "21 November 2026",
        "evidence": "Submit your assignment by 22 November 2026.",
    },
    "submission_method": {"value": None, "evidence": None},
    "required_files": [],
    "important_dates": [],
}
_apply_semantic_safeguards(data)
check(
    "Contradictory deadline is not silently converted to null",
    data["deadline"]["value"] == "21 November 2026",
)


# 5. Negative submission statement must not become a method
data = {
    "deadline": {"value": None, "evidence": None},
    "submission_method": {
        "value": "No assignment or submission is required.",
        "evidence": "No assignment or submission is required.",
    },
    "required_files": [],
    "important_dates": [],
}
_apply_semantic_safeguards(data)
check(
    "Negative submission statement is removed",
    data["submission_method"] == {"value": None, "evidence": None},
)


# 6. Negative required-file claims must be removed, real files retained
data = {
    "deadline": {"value": None, "evidence": None},
    "submission_method": {"value": None, "evidence": None},
    "required_files": [
        {
            "value": "No assignment or submission is required.",
            "evidence": "No assignment or submission is required.",
        },
        {
            "value": "Java source file",
            "evidence": "Upload your Java source file.",
        },
        {
            "value": "PDF screenshots",
            "evidence": "Include PDF screenshots.",
        },
    ],
    "important_dates": [],
}
_apply_semantic_safeguards(data)
check(
    "Negative file claim is removed while actual required files remain",
    [item["value"] for item in data["required_files"]]
    == ["Java source file", "PDF screenshots"],
)


# 7. Valid event dates may remain in important_dates
data = {
    "deadline": {"value": None, "evidence": None},
    "submission_method": {"value": None, "evidence": None},
    "required_files": [],
    "important_dates": [
        {
            "label": "Seminar date",
            "date_text": "20 November 2026",
            "evidence": "The seminar will be held on 20 November 2026.",
        },
        {
            "label": "Invalid date",
            "date_text": "Java Practical Assignment - JDBC",
            "evidence": "Java Practical Assignment - JDBC",
        },
    ],
}
_apply_semantic_safeguards(data)
check(
    "Valid event date is retained and fabricated subject date is removed",
    len(data["important_dates"]) == 1
    and data["important_dates"][0]["date_text"] == "20 November 2026",
)

print(f"\nAll {passed} semantic safeguard tests passed.")
