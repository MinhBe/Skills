import hashlib
import json
from pathlib import Path


def file_hash(path: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def cache_root() -> Path:
    root = Path(".ocr_cache")
    root.mkdir(exist_ok=True)
    return root


def cache_key(file_digest: str, page_index: int, engine: str, dpi: int, lang: str, profile: str) -> str:
    raw = json.dumps(
        {
            "file": file_digest,
            "page": page_index,
            "engine": engine,
            "dpi": dpi,
            "lang": lang,
            "profile": profile,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_cache(key: str) -> str | None:
    path = cache_root() / f"{key}.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def write_cache(key: str, text: str) -> None:
    path = cache_root() / f"{key}.txt"
    path.write_text(text, encoding="utf-8")
