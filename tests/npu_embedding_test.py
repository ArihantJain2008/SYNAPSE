import numpy as np
import openvino as ov
from transformers import AutoTokenizer

MODEL_PATH = "qwen3-embedding-0.6b-ov"
SEQUENCE_LENGTH = 128

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

print("Loading OpenVINO model...")
core = ov.Core()
model = core.read_model(f"{MODEL_PATH}/openvino_model.xml")

print("\nOriginal inputs:")
for inp in model.inputs:
    print(inp.get_any_name(), inp.get_partial_shape())

print("\nSetting static input dimensions...")
model.reshape({
    "input_ids": [1, SEQUENCE_LENGTH],
    "attention_mask": [1, SEQUENCE_LENGTH]
})

print("Updated inputs:")
for inp in model.inputs:
    print(inp.get_any_name(), inp.get_partial_shape())

print("\nCompiling model for Intel NPU...")
compiled_model = core.compile_model(model, "NPU")

print("Preparing test input...")
tokens = tokenizer(
    "Artificial intelligence can help students organise assignments.",
    return_tensors="np",
    truncation=True,
    padding="max_length",
    max_length=SEQUENCE_LENGTH
)

inputs = {
    "input_ids": tokens["input_ids"],
    "attention_mask": tokens["attention_mask"]
}

print("Running inference on NPU...")
result = compiled_model(inputs)

print("\nSUCCESS: NPU inference completed.")

for output in compiled_model.outputs:
    value = result[output]
    print("Output shape:", value.shape)
    print("Output dtype:", value.dtype)

