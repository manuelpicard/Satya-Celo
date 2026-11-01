"""Hashing helpers: exact content hashes and similarity fingerprints.

contentHash (exact, used as proof key):
  * files: SHA-256 of the raw bytes
  * text:  SHA-256 of the Satya-normalised UTF-8 text ("satya-text-v1")
softHash (similarity, never proof):
  * images: 64-bit DCT perceptual hash
  * text:   64-bit SimHash over word 3-shingles
"""

from __future__ import annotations

import hashlib
import io
import re
import unicodedata

import numpy as np

# Zero-width / invisible characters that are often used to hide data in text
INVISIBLE_RE = re.compile(
    "[\u200b\u200c\u200d\u2060\u2061\u2062\u2063\u2064\ufeff\u00ad\u180e"
    "\ufe00-\ufe0f\U000e0000-\U000e007f\U000e0100-\U000e01ef]"
)

SEAL_BEGIN = "-----BEGIN SATYA-SIEGEL-----"
SEAL_END = "-----END SATYA-SIEGEL-----"
SEAL_BLOCK_RE = re.compile(re.escape(SEAL_BEGIN) + r"\s*(?P<body>[A-Za-z0-9_\-=\s]+?)\s*" + re.escape(SEAL_END), re.S)


def count_invisible(text: str) -> int:
    return len(INVISIBLE_RE.findall(text))


def strip_seal(text: str) -> tuple[str, str | None]:
    """Remove an embedded seal block; return (text_without_seal, seal_body_or_None)."""
    m = SEAL_BLOCK_RE.search(text)
    if not m:
        return text, None
    body = re.sub(r"\s+", "", m.group("body"))
    return text[: m.start()] + text[m.end() :], body


def normalize_text(text: str) -> str:
    """satya-text-v1: NFC, LF line endings, no invisible chars, no trailing spaces, trimmed."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = INVISIBLE_RE.sub("", text)
    lines = [ln.rstrip() for ln in text.split("\n")]
    return "\n".join(lines).strip()


def sha256_bytes(data: bytes) -> str:
    return "0x" + hashlib.sha256(data).hexdigest()


def text_hash(text: str) -> str:
    return sha256_bytes(normalize_text(text).encode("utf-8"))


def simhash64(text: str) -> str:
    words = re.findall(r"\w+", normalize_text(text).lower())
    shingles = [" ".join(words[i : i + 3]) for i in range(max(1, len(words) - 2))] if words else [""]
    acc = np.zeros(64, dtype=np.int64)
    for sh in shingles:
        h = int.from_bytes(hashlib.blake2b(sh.encode(), digest_size=8).digest(), "big")
        bits = np.array([(h >> i) & 1 for i in range(64)], dtype=np.int64)
        acc += 2 * bits - 1
    value = 0
    for i in range(64):
        if acc[i] > 0:
            value |= 1 << i
    return "0x" + value.to_bytes(8, "big").hex()


def _dct_matrix(n: int) -> np.ndarray:
    k = np.arange(n)
    m = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n))
    m[0] *= 1 / np.sqrt(2)
    return m * np.sqrt(2 / n)


_DCT32 = _dct_matrix(32)


def phash64(image_bytes: bytes) -> str | None:
    try:
        from PIL import Image

        im = Image.open(io.BytesIO(image_bytes)).convert("L").resize((32, 32), Image.Resampling.LANCZOS)
    except Exception:
        return None
    px = np.asarray(im, dtype=np.float64)
    dct = _DCT32 @ px @ _DCT32.T
    low = dct[:8, :8].flatten()
    med = np.median(low[1:])
    value = 0
    for i, c in enumerate(low):
        if c > med:
            value |= 1 << (63 - i)
    return "0x" + value.to_bytes(8, "big").hex()


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")
