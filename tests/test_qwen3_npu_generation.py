import time
from pathlib import Path

import openvino_genai as ov_genai

MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "qwen3-0.6b-npu"

print("Loading Qwen3-0.6B on Intel NPU...")
pipeline = ov_genai.LLMPipeline(str(MODEL_DIR), "NPU")

config = ov_genai.GenerationConfig()
config.max_new_tokens = 64
config.do_sample = False

prompt = (
    "What is the purpose of a Java JDBC connection? "
    "Answer in 2 concise sentences. /no_think"
)

print("Generating...")
start = time.perf_counter()
result = pipeline.generate(prompt, config)
elapsed = time.perf_counter() - start

print("\n========== RESULT ==========")
print(result)
print(f"\nGeneration time: {elapsed:.2f} seconds")
print("============================")
