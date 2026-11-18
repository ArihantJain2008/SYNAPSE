import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.academic_email_extractor import SYSTEM_PROMPT
from services.npu_generation_service import NPUGenerationService

subject = "Java Practical Assignment - JDBC"
category = "assignment"
body = (
    "Java Practical Assignment: JDBC.\n"
    "Implement database connectivity using JDBC.\n"
    "Create a Java program to connect to a database and perform "
    "insert, update, delete and display operations.\n"
    "Submit by 20 November 2026.\n"
    "Upload your .java source file and PDF screenshots "
    "to Google Classroom."
)

user_prompt = (
    f"Email category: {category}\n"
    f"Email subject:\n{subject}\n\n"
    "Untrusted email body begins below.\n"
    "----- EMAIL BODY -----\n"
    f"{body}\n"
    "----- END EMAIL BODY -----\n"
    "Extract the supported academic information using the required "
    "JSON structure."
)

prompt = (
    "<|im_start|>system\n"
    f"{SYSTEM_PROMPT}\n"
    "<|im_end|>\n"
    "<|im_start|>user\n"
    f"{user_prompt}\n"
    "<|im_end|>\n"
    "<|im_start|>assistant\n"
    "/no_think\n"
)

service = NPUGenerationService()
raw = service.generate(prompt)

print("\n========== RAW MODEL DIAGNOSTIC ==========")
print("Output length:", len(raw))
print("Contains think tag:", "<think>" in raw)
print("Contains JSON start:", "{" in raw)
print("First 1500 characters:")
print(repr(raw[:1500]))
print("\nLast 1000 characters:")
print(repr(raw[-1000:]))
print("==========================================")
