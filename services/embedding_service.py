from pathlib import Path

import numpy as np
import openvino as ov
from transformers import AutoTokenizer


class EmbeddingService:
    """Local Qwen3 embedding service using Intel OpenVINO NPU."""

    QUERY_INSTRUCTION = (
        "Given an academic question, retrieve relevant course materials, "
        "assignment instructions, and reference documents that answer it."
    )

    def __init__(
        self,
        model_path="qwen3-embedding-0.6b-ov",
        device="NPU",
        max_length=128,
    ):
        self.model_path = Path(model_path)
        self.device = device
        self.max_length = max_length

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Embedding model not found: {self.model_path}"
            )

        self.core = ov.Core()

        if device not in self.core.available_devices:
            raise RuntimeError(
                f"{device} is unavailable. "
                f"Detected devices: {self.core.available_devices}"
            )

        print(f"Loading tokenizer from {self.model_path}...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(self.model_path),
            use_fast=True,
        )

        print("Loading OpenVINO model...")
        model = self.core.read_model(
            str(self.model_path / "openvino_model.xml")
        )

        print(f"Setting static dimensions: [1, {max_length}]")
        model.reshape({
            "input_ids": [1, max_length],
            "attention_mask": [1, max_length],
        })

        print(f"Compiling model for {device}...")
        self.compiled_model = self.core.compile_model(model, device)
        self.output_layer = self.compiled_model.output(0)

        print(f"Embedding service ready on {device}.")

    def _embed(self, text):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Text must be a non-empty string.")

        tokens = self.tokenizer(
            text,
            return_tensors="np",
            truncation=False,
            padding="max_length",
            max_length=self.max_length,
        )

        actual_tokens = int(tokens["attention_mask"].sum())

        if actual_tokens > self.max_length:
            raise ValueError(
                f"Input exceeds embedding limit: "
                f"{actual_tokens}/{self.max_length} tokens."
            )

        result = self.compiled_model({
            "input_ids": tokens["input_ids"],
            "attention_mask": tokens["attention_mask"],
        })

        hidden = result[self.output_layer]

        # Qwen3 embedding uses last-token pooling.
        if self.tokenizer.padding_side == "left":
            sentence_vector = hidden[:, -1, :]
        else:
            last_index = tokens["attention_mask"].sum(axis=1) - 1
            sentence_vector = hidden[
                np.arange(len(last_index)),
                last_index
            ]

        norms = np.linalg.norm(
            sentence_vector,
            axis=1,
            keepdims=True,
        )

        embedding = sentence_vector / np.maximum(norms, 1e-12)

        return embedding[0].astype(np.float32)

    def embed_document(self, text):
        """Generate an embedding for stored academic content."""
        return self._embed(text)

    def embed_query(self, text):
        """Generate an instruction-aware academic search query embedding."""
        formatted_query = (
            f"Instruct: {self.QUERY_INSTRUCTION}\n"
            f"Query: {text}"
        )
        return self._embed(formatted_query)

    @staticmethod
    def similarity(vector_a, vector_b):
        """Cosine similarity between normalized embeddings."""
        return float(np.dot(vector_a, vector_b))
