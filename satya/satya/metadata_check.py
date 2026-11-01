"""Unsigned metadata hints (EXIF, XMP, IPTC, PNG text chunks).

Everything here is a HINT at most: unsigned metadata can be written, copied or deleted by
anyone in seconds. It is still useful because many generators write it by default.
"""

from __future__ import annotations

import io
import re

from .model import Direction, Evidence, Tier

GENERATOR_NAMES = [
    "midjourney", "dall-e", "dall·e", "dalle", "stable diffusion", "stablediffusion", "sdxl", "comfyui",
    "automatic1111", "invokeai", "novelai", "firefly", "imagen", "gemini", "nano banana", "chatgpt",
    "gpt-image", "openai", "leonardo.ai", "ideogram", "flux", "black forest labs", "runway", "sora",
    "kling", "pika", "veo", "synthid", "grok", "aurora", "recraft", "playground ai", "krea",
]
# whole words only - "ImageNumber" must not match "imagen"
_GEN_RE = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(n) for n in GENERATOR_NAMES) + r")(?![A-Za-z0-9])", re.I)
_DST_RE = re.compile(r"digitalsourcetype/(\w+)", re.I)
_XMP_RE = re.compile(rb"<x:xmpmeta.*?</x:xmpmeta>", re.S)
AI_TYPES = {"trainedalgorithmicmedia", "compositewithtrainedalgorithmicmedia"}


def _hint(title: str, detail: str, data: dict | None = None, direction: Direction = Direction.AI) -> Evidence:
    return Evidence("metadaten", Tier.HINT, direction, title,
                    detail + " Unsignierte Metadaten kann jeder setzen oder löschen, daher nur ein Indiz.",
                    data=data or {})


def check_metadata(data: bytes, mime: str | None) -> list[Evidence]:
    if not mime or not mime.startswith("image/"):
        return []
    out: list[Evidence] = []
    try:
        from PIL import Image

        im = Image.open(io.BytesIO(data))
        info = dict(im.info)
        exif = im.getexif()
    except Exception:
        return []

    # Stable-Diffusion front-ends write the full generation parameters into PNG text chunks
    if "parameters" in info and isinstance(info["parameters"], str):
        p = info["parameters"]
        out.append(_hint("Generierungsparameter im Bild (A1111/Forge/SD.Next)",
                         "Die Datei enthält einen PNG-Textblock „parameters“ mit Prompt und Sampler-Einstellungen, "
                         "wie ihn Stable-Diffusion-Oberflächen schreiben.",
                         {"auszug": p[:200]}))
    if "workflow" in info or ("prompt" in info and isinstance(info.get("prompt"), str) and "class_type" in info["prompt"]):
        out.append(_hint("ComfyUI-Workflow im Bild",
                         "Die Datei enthält einen ComfyUI-Workflow bzw. Prompt-Graphen."))

    # XMP / IPTC digital source type (unsigned copy of what C2PA would sign)
    xmp_blobs = [m.group(0) for m in _XMP_RE.finditer(data[: 4 * 1024 * 1024])]
    for key in ("xmp", "XML:com.adobe.xmp"):
        v = info.get(key)
        if isinstance(v, (bytes, str)):
            xmp_blobs.append(v.encode() if isinstance(v, str) else v)
    seen: set[str] = set()
    seen_names: set[str] = set()
    for blob in xmp_blobs:
        text = blob.decode("utf-8", "ignore")
        for t in _DST_RE.findall(text):
            if t.lower() in seen:
                continue
            seen.add(t.lower())
            if t.lower() in AI_TYPES:
                out.append(_hint("XMP/IPTC: KI-Quelltyp eingetragen",
                                 f"Die unsignierten XMP-Metadaten nennen den IPTC-Quelltyp „{t}“.", {"quelltyp": t}))
            else:
                out.append(Evidence("metadaten", Tier.INFO, Direction.NEUTRAL, "XMP/IPTC: Quelltyp eingetragen",
                                    f"Unsignierter IPTC-Quelltyp „{t}“.", data={"quelltyp": t}))
        names = sorted({m.group(0).lower() for m in _GEN_RE.finditer(text)} - seen_names)
        seen_names.update(names)
        if names:
            out.append(_hint("XMP: Name eines KI-Generators", f"Die XMP-Metadaten erwähnen: {', '.join(names)}.",
                             {"namen": names}))

    # EXIF Software (305), ImageDescription (270), Artist (315), UserComment via text chunks
    fields = {"Software": exif.get(305), "ImageDescription": exif.get(270), "Artist": exif.get(315)}
    for k in ("Software", "Comment", "Description", "Title", "Author", "Source"):
        if isinstance(info.get(k), str):
            fields[k] = info[k]
    for k, v in fields.items():
        if isinstance(v, str) and _GEN_RE.search(v):
            out.append(_hint(f"Metadatenfeld „{k}“ nennt einen KI-Generator", f"„{k}“ = „{v[:120]}“.",
                             {"feld": k, "wert": v[:200]}))
    return out
