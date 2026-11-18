import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.academic_email_classifier import classify_message


CASES = [
    ("Your NPTEL exam results are out", "assessment"),
    ("18th Young Psychologist Competition & Undergraduate Research Conference 2027", "academic_opportunity"),
    ("Invitation to Open Day & Daksh 2026 | CHRIST Central Campus", "announcement"),
    ("New! Introducing AI Series", "other"),
    ("How to brand a robot (without the blue gradients)", "promotional"),
    ("Ready: Introduction to Back-End Development", "course_update"),
    ("Message from the Vice Chancellor", "announcement"),
    ("Ends today: ₹6,999 Diwali offer", "promotional"),
    ("Library Timings During Diwali Holidays", "schedule_change"),
    ("Current Awareness Service (CAS) - Latest Update", "course_material"),
    ("SWAYAM CERTIFICATE UPLOAD _ NOVEMBER 2026", "general_college"),
    ("4 new image styles to try", "promotional"),
    ("Grow your career for ₹7,499/year | Coursera Plus", "promotional"),
]


def run_tests():
    print("Testing real-world academic email subjects...\n")

    failures = []

    for subject, expected in CASES:
        result = classify_message({"sender": "", "subject": subject})
        actual = result["category"]

        if actual == expected:
            print(f"PASS: {subject[:65]}")
        else:
            print(f"FAIL: {subject[:65]}")
            print(f"      Expected: {expected}, got: {actual}")
            failures.append((subject, expected, actual))

    print(f"\nPassed: {len(CASES) - len(failures)}/{len(CASES)}")

    if failures:
        raise AssertionError("Some subject classification tests failed.")

    print("All real-world subject tests passed.")


if __name__ == "__main__":
    run_tests()
