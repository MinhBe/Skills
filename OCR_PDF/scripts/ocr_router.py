import argparse
import io
import json
import os
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

from cache_utils import cache_key, file_hash, read_cache, write_cache
from env_probe import probe


SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
MODE_ALIASES = {"fast": "native", "max": "quality"}
MODE_DPI = {
    "auto": 220,
    "native": 150,
    "scan-fast": 180,
    "balanced": 220,
    "quality": 300,
    "markdown": 300,
    "scientific": 300,
    "vlm-quality": 300,
}
PAGE_SEPARATOR = "\n\n---\n\n"


def parse_pages(pages: str | None, total_pages: int) -> list[int]:
    if not pages:
        return list(range(total_pages))
    result = set()
    for part in pages.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            result.update(range(int(start) - 1, int(end)))
        else:
            result.add(int(part) - 1)
    return sorted(i for i in result if 0 <= i < total_pages)


def inspect_pdf(path: str, page_indices: list[int]) -> list[dict]:
    import fitz

    doc = fitz.open(path)
    pages = []
    for index in page_indices:
        page = doc[index]
        text = page.get_text()
        blocks = page.get_text("dict").get("blocks", [])
        image_blocks = [block for block in blocks if block.get("type") == 1]
        rect = page.rect
        page_area = max(rect.width * rect.height, 1)
        image_area = 0.0
        for block in image_blocks:
            bbox = block.get("bbox") or [0, 0, 0, 0]
            image_area += max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 0)
        stripped = text.strip()
        image_ratio = min(image_area / page_area, 1.0)
        needs_ocr = len(stripped) < 80 or (len(stripped) < 250 and image_ratio > 0.35)
        pages.append(
            {
                "index": index,
                "native_text": text,
                "chars": len(stripped),
                "image_ratio": round(image_ratio, 3),
                "needs_ocr": needs_ocr,
            }
        )
    doc.close()
    return pages


def render_pdf_page(path: str, page_index: int, dpi: int) -> bytes:
    import fitz

    doc = fitz.open(path)
    page = doc[page_index]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    data = pix.pil_tobytes("png")
    doc.close()
    return data


def load_image_bytes(path: str) -> bytes:
    from PIL import Image

    image = Image.open(path)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def choose_engine(mode: str, env: dict) -> str:
    engines = env["engines"]
    if mode == "native":
        return "native"
    if mode == "markdown":
        for engine in ["marker", "surya", "paddleocr", "rapidocr", "easyocr", "tesseract"]:
            if engines.get(engine):
                return engine
    if mode in {"quality", "scientific", "vlm-quality"}:
        for engine in ["paddleocr", "surya", "easyocr", "rapidocr", "tesseract"]:
            if engines.get(engine):
                return engine
    if mode in {"scan-fast", "balanced", "auto"}:
        for engine in ["rapidocr", "paddleocr", "tesseract", "easyocr"]:
            if engines.get(engine):
                return engine
    return "none"


def image_to_array(image_bytes: bytes):
    import numpy as np
    from PIL import Image

    return np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))


def ocr_image(image_bytes: bytes, engine: str, lang: str, gpu: bool, paragraph: bool) -> str:
    if engine == "easyocr":
        import easyocr

        reader = easyocr.Reader([item.strip() for item in lang.split(",") if item.strip()], gpu=gpu)
        raw = reader.readtext(image_to_array(image_bytes), detail=0, paragraph=paragraph)
        return "\n".join(raw or [])
    if engine == "tesseract":
        import pytesseract
        from PIL import Image

        common_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if not shutil.which(str(pytesseract.pytesseract.tesseract_cmd)) and Path(common_path).exists():
            pytesseract.pytesseract.tesseract_cmd = common_path
        return pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes)), lang=lang.split(",")[0])
    if engine == "rapidocr":
        from rapidocr_onnxruntime import RapidOCR

        ocr = RapidOCR()
        result, _ = ocr(image_to_array(image_bytes))
        if not result:
            return ""
        return "\n".join(item[1] for item in result if len(item) > 1)
    if engine == "paddleocr":
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(use_angle_cls=True, lang=lang.split(",")[0], show_log=False)
        result = ocr.ocr(image_to_array(image_bytes), cls=True)
        lines = []
        for page in result or []:
            for item in page or []:
                if len(item) > 1 and item[1]:
                    lines.append(item[1][0])
        return "\n".join(lines)
    raise RuntimeError(f"OCR engine is not available or not implemented in router: {engine}")


def weak_text(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 30:
        return True
    printable = sum(1 for ch in stripped if ch.isprintable())
    return printable / max(len(stripped), 1) < 0.85


def write_error(output_dir: Path, entry: dict) -> None:
    path = output_dir / "ocr_router_errors.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = []
    else:
        data = []
    data.append(entry)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def process(args) -> str:
    input_path = args.input
    ext = Path(input_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {ext}")

    mode = MODE_ALIASES.get(args.mode, args.mode)
    env = probe()
    dpi = args.dpi or MODE_DPI[mode]
    engine = choose_engine(mode, env)
    if engine == "none":
        raise RuntimeError("No OCR engine available. Install an optional OCR engine or use a digital PDF with native text.")

    digest = file_hash(input_path)
    output_pages = []

    if ext == ".pdf":
        import fitz

        doc = fitz.open(input_path)
        page_indices = parse_pages(args.pages, len(doc))
        doc.close()
        page_info = inspect_pdf(input_path, page_indices)
        for info in page_info:
            page_index = info["index"]
            use_native = mode == "native" or (mode == "auto" and not info["needs_ocr"])
            if use_native:
                text = info["native_text"]
                source = "native"
            else:
                cache_id = cache_key(digest, page_index, engine, dpi, args.lang, mode)
                text = None if args.no_cache else read_cache(cache_id)
                source = f"{engine}:cache" if text is not None else engine
                if text is None:
                    image = render_pdf_page(input_path, page_index, dpi)
                    text = ocr_image(image, engine, args.lang, args.gpu, paragraph=mode in {"quality", "markdown"})
                    if not args.no_cache:
                        write_cache(cache_id, text)
            if weak_text(text):
                output_dir = Path(args.output or ".").parent
                write_error(
                    output_dir,
                    {
                        "timestamp": datetime.now().isoformat(),
                        "file": os.path.basename(input_path),
                        "page": page_index + 1,
                        "mode": mode,
                        "engine": source,
                        "dpi": dpi,
                        "error_type": "weak_page",
                        "output_chars": len(text.strip()),
                    },
                )
            output_pages.append(text)
    else:
        image = load_image_bytes(input_path)
        cache_id = cache_key(digest, 0, engine, dpi, args.lang, mode)
        text = None if args.no_cache else read_cache(cache_id)
        if text is None:
            text = ocr_image(image, engine, args.lang, args.gpu, paragraph=mode in {"quality", "markdown"})
            if not args.no_cache:
                write_cache(cache_id, text)
        output_pages.append(text)

    return args.page_separator.join(output_pages)


def parse_args():
    parser = argparse.ArgumentParser(description="Adaptive PDF/image OCR router.")
    parser.add_argument("--input", "-i", required=True, help="Path to input PDF/image")
    parser.add_argument("--output", "-o", default=None, help="Output text/Markdown path")
    parser.add_argument(
        "--mode",
        choices=["auto", "native", "scan-fast", "balanced", "quality", "markdown", "scientific", "vlm-quality", "fast", "max"],
        default="auto",
    )
    parser.add_argument("--lang", default="en", help="Language code(s), comma-separated")
    parser.add_argument("--dpi", type=int, default=None, help="Override render DPI")
    parser.add_argument("--pages", default=None, help="Pages such as 1,2,5-8")
    parser.add_argument("--page-separator", default=PAGE_SEPARATOR)
    parser.add_argument("--gpu", action="store_true", help="Prefer GPU when engine supports it")
    parser.add_argument("--no-cache", action="store_true", help="Disable OCR cache")
    return parser.parse_args()


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.upper() != "UTF-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    args = parse_args()
    try:
        output = process(args)
    except Exception as exc:
        output_dir = Path(args.output or ".").parent
        write_error(
            output_dir,
            {
                "timestamp": datetime.now().isoformat(),
                "file": os.path.basename(args.input),
                "mode": args.mode,
                "error_type": "exception",
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        raise
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
        print(f"Saved: {path}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
