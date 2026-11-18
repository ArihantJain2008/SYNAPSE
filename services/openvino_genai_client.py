from pathlib import Path
import re

from services.npu_generation_service import NPUGenerationService


class OpenVINOGenAIClient:
    """Adapter matching the existing academic extractor client interface."""

    def __init__(self, service=None):
        self.service = service or NPUGenerationService()

    def generate(self, system_prompt, user_prompt):
        prompt = (
            "<|im_start|>system\n"
            f"{system_prompt}\n"
            "<|im_end|>\n"
            "<|im_start|>user\n"
            f"{user_prompt}\n"
            "<|im_end|>\n"
            "<|im_start|>assistant\n"
            "/no_think\n"
        )

        output = self.service.generate(prompt)

        # Remove optional Qwen thinking blocks before JSON parsing.
        output = re.sub(
            r"<think>.*?</think>",
            "",
            output,
            flags=re.DOTALL,
        )

        output = output.strip()

        # Remove Markdown JSON fences without altering the JSON itself.
        if output.startswith("```"):
            lines = output.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                output = "\n".join(lines[1:-1]).strip()
                if output.lower().startswith("json"):
                    output = output[4:].lstrip()

        return output
