import re

RULES = {
    "assignment": {
        "strong": (
            "assignment", "submit your work", "submission deadline",
            "submit by", "practical file", "lab record",
            "project submission", "upload your assignment",
            "last date for submission"
        ),
        "weak": ("homework", "coursework", "practical", "project work")
    },
    "assessment": {
        "strong": (
            "examination", "exam schedule", "exam result",
            "exam results", "mid semester", "end semester",
            "internal assessment", "class test", "quiz", "cia",
            "mse", "viva voce", "test timetable", "results are out",
            "result declared", "marks published"
        ),
        "weak": ("assessment", "marks", "evaluation", "question paper",
                 "nptel results")
    },
    "announcement": {
        "strong": (
            "important announcement", "notice to students",
            "circular", "all students are informed",
            "official announcement", "student notice",
            "message from the vice chancellor",
            "invitation to open day"
        ),
        "weak": ("announcement", "notice", "student update",
                 "vice chancellor", "open day", "daksh")
    },
    "course_material": {
        "strong": (
            "lecture notes", "study material", "course material",
            "presentation slides", "reading material",
            "reference material", "chapter notes",
            "current awareness service"
        ),
        "weak": ("notes", "slides", "pdf", "reading", "syllabus")
    },
    "schedule_change": {
        "strong": (
            "class cancelled", "class postponed",
            "class rescheduled", "timetable changed",
            "change in timetable", "room changed",
            "lecture rescheduled", "revised schedule",
            "library timings", "library timing",
            "revised library hours"
        ),
        "weak": ("timetable", "schedule change", "class timing",
                 "room allocation", "timings during holidays")
    },
    "general_college": {
        "strong": (
            "fee payment", "fee receipt", "attendance shortage",
            "registration notice", "document verification",
            "university administration", "certificate upload"
        ),
        "weak": ("college office", "administration", "registration",
                 "student portal", "swayam certificate")
    },
    "academic_opportunity": {
        "strong": (
            "research conference", "undergraduate research",
            "psychologist competition", "student competition",
            "academic conference", "call for papers",
            "workshop registration"
        ),
        "weak": ("competition", "conference", "workshop",
                 "hackathon", "seminar", "symposium")
    },
    "course_update": {
        "strong": (
            "course completed", "course completion",
            "course is ready", "ready:", "course enrollment",
            "course enrolled", "learning path"
        ),
        "weak": ("course update", "course progress", "back-end development",
                 "online course", "course available")
    },
    "promotional": {
        "strong": (
            "limited time offer", "special offer",
            "discount offer", "ends today", "subscribe now",
            "save today", "annual subscription",
            "career for", "new image styles to try"
        ),
        "weak": ("offer", "discount", "promotion", "coursera plus",
                 "newsletter", "brand a robot")
    }
}


def _normalize(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.lower()).strip()


def classify_message(message):
    """
    Classifies using sender and subject only.
    Does not read message bodies or snippets.
    """
    if not isinstance(message, dict):
        raise TypeError("message must be a dictionary")

    sender = _normalize(message.get("sender", ""))
    subject = _normalize(message.get("subject", ""))
    text = f"{sender} {subject}"

    scores = {}
    matched = {}

    for category, groups in RULES.items():
        strong_matches = [
            term for term in groups["strong"] if term in text
        ]
        weak_matches = [
            term for term in groups["weak"] if term in text
        ]

        score = len(strong_matches) * 3 + len(weak_matches)

        if score:
            scores[category] = score
            matched[category] = strong_matches + weak_matches

    if not scores:
        return {
            "category": "other",
            "confidence": 0.0,
            "matched_terms": [],
            "requires_body": True
        }

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    best_category, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score >= 6 and best_score >= second_score + 3:
        confidence = 0.95
    elif best_score >= 3 and best_score > second_score:
        confidence = 0.80
    elif best_score > second_score:
        confidence = 0.65
    else:
        confidence = 0.40

    return {
        "category": best_category,
        "confidence": confidence,
        "matched_terms": matched[best_category],
        "requires_body": confidence < 0.80
    }
