import openvino as ov

core = ov.Core()

print("OpenVINO version:", ov.__version__)
print("\nAvailable devices:")

for device in core.available_devices:
    print("-", device)

if "NPU" in core.available_devices:
    print("\nSUCCESS: Intel NPU detected!")
else:
    print("\nNPU plugin not detected. Further setup required.")
