import argparse
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small OCR timing sample.")
    parser.add_argument("--input", "-i", required=True)
    parser.add_argument("--pages", default="1-2")
    parser.add_argument("--mode", default="auto")
    args = parser.parse_args()

    output = Path(".ocr_benchmark_sample.md")
    command = [
        sys.executable,
        str(Path(__file__).with_name("ocr_router.py")),
        "--input",
        args.input,
        "--output",
        str(output),
        "--pages",
        args.pages,
        "--mode",
        args.mode,
    ]
    start = time.perf_counter()
    completed = subprocess.run(command, text=True, capture_output=True)
    elapsed = time.perf_counter() - start
    print(f"command: {' '.join(command)}")
    print(f"returncode: {completed.returncode}")
    print(f"seconds: {elapsed:.2f}")
    if completed.stderr:
        print("stderr:")
        print(completed.stderr)
    if output.exists():
        text = output.read_text(encoding="utf-8")
        print(f"output_chars: {len(text)}")


if __name__ == "__main__":
    main()
