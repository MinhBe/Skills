import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
MODE_CONFIG = {
    "fast": {"dpi": 150, "paragraph": False},
    "max": {"dpi": 300, "paragraph": True},
}
ERROR_LOG = "ocr_errors.json"


def _check_deps():
    try:
        import easyocr
    except ImportError:
        print("Error: 'easyocr' not installed. Run: pip install easyocr", file=sys.stderr)
        sys.exit(1)
    try:
        import fitz
    except ImportError:
        print("Error: 'PyMuPDF' not installed. Run: pip install PyMuPDF", file=sys.stderr)
        sys.exit(1)


def load_pdf_pages(file_path: str, dpi: int, page_indices: list[int]):
    import fitz
    doc = fitz.open(file_path)
    pages = []
    for i in page_indices:
        page = doc[i]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img = pix.pil_tobytes("png")
        pages.append(img)
    doc.close()
    return pages


def load_image(file_path: str):
    from PIL import Image
    import io
    img = Image.open(file_path)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return [buf.getvalue()]


def ocr_images(images: list[bytes], reader, paragraph: bool) -> list[str]:
    import numpy as np
    from PIL import Image
    import io
    results = []
    total = len(images)
    for idx, img_bytes in enumerate(images):
        print(f"  OCR page {idx + 1}/{total}...", file=sys.stderr)
        pil_img = Image.open(io.BytesIO(img_bytes))
        arr = np.array(pil_img)
        raw = reader.readtext(arr, detail=0, paragraph=paragraph)
        text = "\n".join(raw) if raw else ""
        results.append(text)
    return results


def extract_images_from_pdf(file_path: str, output_dir: str, base_name: str, dpi: int):
    import fitz
    doc = fitz.open(file_path)
    images_dir = Path(output_dir) / f"{base_name}_images"
    images_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for i in range(len(doc)):
        page = doc[i]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_path = images_dir / f"page_{i + 1}.png"
        pix.save(str(img_path))
        count += 1
    doc.close()
    return count, str(images_dir)


def log_error(output_dir: str, entry: dict):
    log_path = Path(output_dir) / ERROR_LOG
    if log_path.exists():
        try:
            data = json.loads(log_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            data = []
    else:
        data = []
    data.append(entry)
    log_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def detect_error(file_path: str, text: str, pages: int, mode: str, exception: str = None) -> dict | None:
    if exception:
        return {
            "file": os.path.basename(file_path),
            "path": file_path,
            "mode": mode,
            "pages": pages,
            "output_chars": len(text),
            "error_type": "exception",
            "message": exception.split("\n")[0] if exception else "Unknown error",
        }
    if not text.strip():
        return {
            "file": os.path.basename(file_path),
            "path": file_path,
            "mode": mode,
            "pages": pages,
            "output_chars": 0,
            "error_type": "empty_output",
            "message": "OCR returned no text",
        }
    if pages > 0 and len(text.strip()) < 50:
        return {
            "file": os.path.basename(file_path),
            "path": file_path,
            "mode": mode,
            "pages": pages,
            "output_chars": len(text.strip()),
            "error_type": "output_too_short",
            "message": f"Only {len(text.strip())} chars for {pages} pages",
        }
    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Local OCR processor using EasyOCR. Fully offline. Supports PDF, PNG, JPG, WEBP, GIF."
    )
    parser.add_argument("--input", "-i", required=True, help="Path to input file")
    parser.add_argument("--output", "-o", default=None, help="Output .md file (default: stdout)")
    parser.add_argument("--lang", default="en", help="Language code(s) for OCR (default: en). Comma-separated for multiple.")
    parser.add_argument("--mode", choices=["fast", "max"], default="fast",
                        help="fast: DPI 150, no paragraph (speed). max: DPI 300, paragraph grouping (quality).")
    parser.add_argument("--page-separator", default="\n\n---\n\n", help="Separator between pages (default: '---')")
    parser.add_argument("--include-images", action="store_true", help="Save rendered PDF pages as PNG images")
    parser.add_argument("--dpi", type=int, default=None, help="Override DPI (overrides mode default)")
    parser.add_argument("--gpu", action="store_true", help="Use GPU if available")
    parser.add_argument("--pages", default=None, help="Specific pages to process (e.g., '1,2,5' or '1-3'). Default: all.")
    return parser.parse_args()


def get_page_indices(pages_str: str, total_pages: int) -> list[int]:
    if not pages_str:
        return list(range(total_pages))
    indices = set()
    parts = pages_str.split(",")
    for part in parts:
        if "-" in part:
            start, end = part.split("-")
            indices.update(range(int(start) - 1, int(end)))
        else:
            indices.add(int(part) - 1)
    return sorted([i for i in indices if 0 <= i < total_pages])


def extract_native_text(file_path: str, page_indices: list[int]) -> list[str]:
    import fitz
    doc = fitz.open(file_path)
    texts = []
    for i in page_indices:
        page = doc[i]
        texts.append(page.get_text())
    doc.close()
    return texts


def main():
    if sys.stdout.encoding and sys.stdout.encoding.upper() != "UTF-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    args = parse_args()
    _check_deps()

    input_path = args.input
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    ext = Path(input_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        print(f"Error: Unsupported file format '{ext}'. Supported: {supported}", file=sys.stderr)
        sys.exit(1)

    mode_cfg = MODE_CONFIG[args.mode]
    dpi = args.dpi if args.dpi is not None else mode_cfg["dpi"]

    print(f"Loading: {input_path}", file=sys.stderr)
    print(f"Mode: {args.mode}, DPI: {dpi if args.mode == 'max' else 'N/A'}, Paragraph: {mode_cfg['paragraph']}", file=sys.stderr)

    error_entry = None
    pages_count = 0
    output_text = ""
    exception_str = None

    try:
        import fitz
        doc_meta = fitz.open(input_path) if ext == ".pdf" else None
        total_pages = len(doc_meta) if doc_meta else 1
        page_indices = get_page_indices(args.pages, total_pages)
        if doc_meta: doc_meta.close()

        # Fast mode for PDF: use native extraction
        if args.mode == "fast" and ext == ".pdf":
            print(f"Extracting native text (Fast mode) for pages: {page_indices}...", file=sys.stderr)
            texts = extract_native_text(input_path, page_indices)
            pages_count = len(texts)
            output_text = args.page_separator.join(texts)
        elif args.mode == "fast":
            # Fast mode for images: User said "ảnh có thì bỏ", so we skip OCR.
            print(f"Fast mode: Skipping OCR for image file.", file=sys.stderr)
            output_text = ""
            pages_count = 1
        else:
            # Max mode: Full OCR
            if ext == ".pdf":
                images = load_pdf_pages(input_path, dpi=dpi, page_indices=page_indices)
            else:
                images = load_image(input_path)

            print(f"Initializing EasyOCR (language: {args.lang})...", file=sys.stderr)
            import easyocr
            lang_list = [l.strip() for l in args.lang.split(",")]
            reader = easyocr.Reader(lang_list, gpu=args.gpu)

            pages_count = len(images)
            print(f"Running OCR on {pages_count} page(s)...", file=sys.stderr)
            texts = ocr_images(images, reader, paragraph=mode_cfg["paragraph"])
            output_text = args.page_separator.join(texts)

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_text, encoding="utf-8")
            print(f"Saved: {output_path} ({pages_count} pages)", file=sys.stderr)
        else:
            sys.stdout.write(output_text)
            if output_text and not output_text.endswith("\n"):
                sys.stdout.write("\n")

        if args.include_images and ext == ".pdf":
            base_name = Path(args.output or input_path).stem
            output_dir = Path(args.output or ".").parent if args.output else Path(".")
            img_count, img_dir = extract_images_from_pdf(input_path, str(output_dir), base_name, dpi=dpi)
            print(f"Saved {img_count} page images to: {img_dir}", file=sys.stderr)

        error_entry = detect_error(input_path, output_text, pages_count, args.mode)

    except Exception as e:
        exception_str = traceback.format_exc()
        print(f"Error: {e}", file=sys.stderr)
        print(exception_str, file=sys.stderr)
        error_entry = detect_error(input_path, output_text, pages_count, args.mode, exception=exception_str)
        if not args.output:
            sys.exit(1)

    if error_entry:
        error_entry["timestamp"] = datetime.now().isoformat()
        error_entry["mode"] = args.mode
        error_entry["dpi"] = dpi
        output_dir = Path(args.output or ".").parent if args.output else Path(".")
        log_error(str(output_dir), error_entry)
        print(f"Logged error to {Path(output_dir) / ERROR_LOG}", file=sys.stderr)


if __name__ == "__main__":
    main()
