from pathlib import Path
from threading import Lock


class NPUGenerationService:
    """Reusable, local OpenVINO GenAI inference service."""

    def __init__(
        self,
        model_path=None,
        device="NPU",
        max_new_tokens=768,
    ):
        if device != "NPU":
            raise ValueError("This service is configured for NPU execution")

        if (
            not isinstance(max_new_tokens, int)
            or isinstance(max_new_tokens, bool)
            or max_new_tokens < 1
        ):
            raise ValueError("max_new_tokens must be a positive integer")

        project_root = Path(__file__).resolve().parents[1]
        self.model_path = Path(
            model_path or project_root / "models" / "qwen3-0.6b-npu"
        ).resolve()

        self.device = device
        self.max_new_tokens = max_new_tokens
        self._pipeline = None
        self._genai = None
        self._lock = Lock()

    def _load(self):
        if self._pipeline is not None:
            return

        if not (self.model_path / "openvino_model.xml").is_file():
            raise FileNotFoundError(
                f"OpenVINO model not found: {self.model_path}"
            )

        try:
            import openvino_genai
        except ImportError as exc:
            raise RuntimeError(
                "OpenVINO GenAI is not installed in this environment"
            ) from exc

        self._genai = openvino_genai
        self._pipeline = openvino_genai.LLMPipeline(
            str(self.model_path),
            self.device,
        )

    def generate(self, prompt):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be non-empty text")

        with self._lock:
            self._load()

            config = self._genai.GenerationConfig()
            config.max_new_tokens = self.max_new_tokens
            config.do_sample = False

            result = self._pipeline.generate(prompt, config)
            return str(result)
