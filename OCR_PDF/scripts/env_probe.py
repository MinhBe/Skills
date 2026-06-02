import argparse
import importlib.util
import json
import os
import platform
import shutil
import sys
from pathlib import Path


PACKAGES = {
    "PyMuPDF": "fitz",
    "Pillow": "PIL",
    "EasyOCR": "easyocr",
    "pytesseract": "pytesseract",
    "PaddleOCR": "paddleocr",
    "RapidOCR": "rapidocr_onnxruntime",
    "Surya": "surya",
    "Marker": "marker",
    "docTR": "doctr",
    "Torch": "torch",
    "OpenCV": "cv2",
    "NumPy": "numpy",
}

BINARIES = ["tesseract"]
COMMON_BINARIES = {
    "tesseract": [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
}


def package_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def find_binary(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for candidate in COMMON_BINARIES.get(name, []):
        if Path(candidate).exists():
            return candidate
    return None


def get_memory_gb() -> float | None:
    try:
        import psutil

        return round(psutil.virtual_memory().total / (1024**3), 2)
    except Exception:
        return None


def get_torch_gpu() -> dict:
    if not package_available("torch"):
        return {"available": False, "reason": "torch_not_installed"}
    try:
        import torch

        available = bool(torch.cuda.is_available())
        return {
            "available": available,
            "device_count": torch.cuda.device_count() if available else 0,
            "devices": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())] if available else [],
            "cuda_version": getattr(torch.version, "cuda", None),
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def get_model_caches() -> dict:
    home = Path.home()
    candidates = {
        "easyocr": home / ".EasyOCR",
        "paddleocr": home / ".paddleocr",
        "huggingface": home / ".cache" / "huggingface",
        "torch": home / ".cache" / "torch",
    }
    return {name: {"path": str(path), "exists": path.exists()} for name, path in candidates.items()}


def probe() -> dict:
    packages = {name: package_available(module) for name, module in PACKAGES.items()}
    binaries = {name: find_binary(name) for name in BINARIES}
    engines = {
        "native_pdf": packages["PyMuPDF"],
        "easyocr": packages["EasyOCR"],
        "tesseract": packages["pytesseract"] and bool(binaries["tesseract"]),
        "pytesseract_wrapper": packages["pytesseract"],
        "rapidocr": packages["RapidOCR"],
        "paddleocr": packages["PaddleOCR"],
        "surya": packages["Surya"],
        "marker": packages["Marker"],
        "doctr": packages["docTR"],
    }
    missing_recommended = [
        engine
        for engine in ["rapidocr", "paddleocr", "surya", "marker", "tesseract"]
        if not engines.get(engine)
    ]
    return {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "memory_gb": get_memory_gb(),
        "packages": packages,
        "binaries": binaries,
        "engines": engines,
        "torch_gpu": get_torch_gpu(),
        "model_caches": get_model_caches(),
        "missing_recommended": missing_recommended,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe OCR engine availability and hardware.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON only.")
    args = parser.parse_args()
    result = probe()
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print("OCR environment probe")
    print(f"Python: {result['python']} ({result['executable']})")
    print(f"Platform: {result['platform']}")
    print(f"CPU cores: {result['cpu_count']}")
    print(f"RAM: {result['memory_gb'] if result['memory_gb'] is not None else 'unknown'} GB")
    gpu = result["torch_gpu"]
    print(f"GPU: {'yes' if gpu.get('available') else 'no'}")
    if gpu.get("devices"):
        print(f"GPU devices: {', '.join(gpu['devices'])}")
    print("\nEngines:")
    for name, available in result["engines"].items():
        print(f"  {name}: {'available' if available else 'missing'}")
    if result["missing_recommended"]:
        print("\nMissing recommended engines:")
        for name in result["missing_recommended"]:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
