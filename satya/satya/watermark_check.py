"""Open (keyless) watermark detection - HINT only.

Stable Diffusion reference pipelines embed a public DWT-DCT watermark (invisible-watermark).
Because the scheme and the message are public, ANYONE can embed it into a real photo or
strip it, so a hit can never be proof.

Calibration finding (see docs/evaluation.md): on clean images the decoder output is NOT
uniformly random - it is often (almost) all ones or all zeros. A naive binomial p-value
would therefore be wrong. We require a near-exact match (>= 95 % of the bits) and reject
degenerate bit strings, and we never report a probability.

Proprietary watermarks (SynthID, OpenAI, Meta Video Seal ...) can only be checked with the
provider's detector; Satya exposes a plugin point for such APIs (see ProviderDetector).
"""

from __future__ import annotations

import io
from math import comb

from .model import Direction, Evidence, Tier

# Stable Diffusion XL (generative-models/sgm/modules/diffusionmodules/sampling watermark)
SDXL_MESSAGE = 0b101100111110110010010000011110111011000110011110
SDXL_BITS = [int(b) for b in bin(SDXL_MESSAGE)[2:]]
# Stable Diffusion 1.x/2.x reference scripts: bytes "StableDiffusionV1"
SDV1_BYTES = b"StableDiffusionV1"
SDV1_BITS = [int(b) for byte in SDV1_BYTES for b in f"{byte:08b}"]

PATTERNS = {
    "Stable Diffusion XL": SDXL_BITS,
    "Stable Diffusion 1.x/2.x": SDV1_BITS,
}
MIN_MATCH_FRACTION = 0.95


def binom_tail(n: int, k: int) -> float:
    """P(X >= k) for X ~ Binomial(n, 1/2) - only valid if bits were uniform (they are not)."""
    return sum(comb(n, i) for i in range(k, n + 1)) / 2**n


def _decode_bits(bgr, length: int) -> list[int]:
    from imwatermark import WatermarkDecoder

    dec = WatermarkDecoder("bits", length)
    bits = dec.decode(bgr, "dwtDct")
    return [int(bool(b)) for b in bits]


def embed_open_watermark(image_bytes: bytes, pattern: str = "Stable Diffusion XL") -> bytes:
    """Embed a public SD watermark (used to build the evaluation corpus / show forgeability)."""
    import cv2
    import numpy as np
    from imwatermark import WatermarkEncoder

    arr = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    enc = WatermarkEncoder()
    enc.set_watermark("bits", PATTERNS[pattern])
    out = enc.encode(arr, "dwtDct")
    ok, png = cv2.imencode(".png", out)
    return png.tobytes()


def check_open_watermarks(data: bytes, mime: str | None) -> list[Evidence]:
    if not mime or not mime.startswith("image/") or mime == "image/svg+xml":
        return []
    try:
        import cv2
        import numpy as np

        arr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return []
    if arr is None or min(arr.shape[:2]) < 256:
        return []
    out: list[Evidence] = []
    for name, pattern in PATTERNS.items():
        try:
            bits = _decode_bits(arr, len(pattern))
        except Exception:
            continue
        ones = sum(bits) / len(bits)
        if ones < 0.1 or ones > 0.9:  # degenerate decoder output, typical for clean images
            continue
        matches = sum(1 for a, b in zip(bits, pattern) if a == b)
        if matches >= MIN_MATCH_FRACTION * len(pattern):
            out.append(Evidence(
                "wasserzeichen", Tier.HINT, Direction.AI, f"Offenes Wasserzeichen: {name}",
                f"{matches}/{len(pattern)} Bits stimmen mit dem öffentlichen {name}-Wasserzeichen überein. "
                "Da Verfahren und Botschaft öffentlich sind, kann jeder dieses Zeichen in echte Fotos "
                "einbetten oder es entfernen, daher nur ein Indiz.",
                data={"muster": name, "treffer": matches, "bits": len(pattern)}))
    return out


class ProviderDetector:
    """Plugin interface for proprietary detectors (SynthID Detector, OpenAI verification API ...).

    A provider's own statement "this is our output" about the exact content is accountable
    and may be returned as PROOF; a statistical score must be returned as HINT.
    """

    name = "abstract"

    def check(self, data: bytes, mime: str | None) -> list[Evidence]:  # pragma: no cover - interface
        raise NotImplementedError
