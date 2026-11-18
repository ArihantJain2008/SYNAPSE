import openvino as ov

core = ov.Core()

for device in core.available_devices:
    print(f"\n===== {device} =====")

    try:
        print("Name:", core.get_property(device, "FULL_DEVICE_NAME"))
    except Exception as e:
        print("Name unavailable:", e)

    if device == "NPU":
        try:
            print("Architecture:", core.get_property(device, "DEVICE_ARCHITECTURE"))
        except Exception as e:
            print("Architecture unavailable:", e)

        try:
            print("Supported properties:")
            print(core.get_property(device, "SUPPORTED_PROPERTIES"))
        except Exception as e:
            print("Properties unavailable:", e)
