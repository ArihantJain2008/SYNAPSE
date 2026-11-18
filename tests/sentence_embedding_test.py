import numpy as np
import openvino as ov
from transformers import AutoTokenizer

MODEL_PATH = "qwen3-embedding-0.6b-ov"
MAX_LENGTH = 128

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
core = ov.Core()
model = core.read_model(f"{MODEL_PATH}/openvino_model.xml")

model.reshape({
    "input_ids": [1, MAX_LENGTH],
    "attention_mask": [1, MAX_LENGTH]
})

compiled = core.compile_model(model, "NPU")

def embed(text):
    tokens = tokenizer(
        text,
        return_tensors="np",
        truncation=True,
        padding="max_length",
        max_length=MAX_LENGTH
    )

    result = compiled({
        "input_ids": tokens["input_ids"],
        "attention_mask": tokens["attention_mask"]
    })

    hidden = next(iter(result.values()))

    if tokenizer.padding_side == "left":
        sentence_vector = hidden[:, -1, :]
    else:
        last_index = tokens["attention_mask"].sum(axis=1) - 1
        sentence_vector = hidden[np.arange(len(last_index)), last_index]

    norm = np.linalg.norm(sentence_vector, axis=1, keepdims=True)
    return sentence_vector / np.maximum(norm, 1e-12)

texts = [
    "How can I prepare for my Java programming examination?",
    "What should I study for my Java coding test?",
    "The weather is sunny today."
]

vectors = [embed(t)[0] for t in texts]

print("\nEmbedding dimensions:", vectors[0].shape)

print("\nCosine similarities:")
print("Related sentences:",
      float(np.dot(vectors[0], vectors[1])))
print("Unrelated sentences:",
      float(np.dot(vectors[0], vectors[2])))

print("\nNPU sentence embedding test completed.")
