import openvino as ov

core = ov.Core()

properties = [
    "DEVICE_ARCHITECTURE",
    "NPU_DRIVER_VERSION",
    "NPU_COMPILER_VERSION",
    "NPU_PLATFORM",
    "NPU_DEVICE_TOTAL_MEM_SIZE",
    "OPTIMIZATION_CAPABILITIES",
]

print("OpenVINO:", ov.__version__)

for prop in properties:
    try:
        print(f"{prop}: {core.get_property('NPU', prop)}")
    except Exception as e:
        print(f"{prop}: unavailable ({e})")
