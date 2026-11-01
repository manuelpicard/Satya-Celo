"""C2PA signing helper for building the demo corpus (wraps c2pa-python's Builder)."""

from __future__ import annotations

import io
from pathlib import Path

import c2pa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

IPTC = "http://cv.iptc.org/newscodes/digitalsourcetype/"


def sign_image(src: bytes, mime: str, cert_pem: Path, key_pem: Path, source_type: str, generator: str,
               title: str) -> bytes:
    key = serialization.load_pem_private_key(key_pem.read_bytes(), password=None)

    def cb(data: bytes) -> bytes:
        return key.sign(data, ec.ECDSA(hashes.SHA256()))

    manifest = {
        "claim_generator_info": [{"name": generator, "version": "0.1"}],
        "title": title,
        "format": mime,
        "assertions": [{"label": "c2pa.actions", "data": {"actions": [
            {"action": "c2pa.created", "digitalSourceType": IPTC + source_type}]}}],
    }
    ctx = c2pa.Context.from_dict({"builder": {"thumbnail": {"enabled": False}}, "verify": {"verify_after_sign": False}})
    out = io.BytesIO()
    with c2pa.Signer.from_callback(cb, c2pa.C2paSigningAlg.ES256, cert_pem.read_text(), None) as signer:
        with c2pa.Builder(manifest, ctx) as b:
            b.sign(signer, mime, io.BytesIO(src), out)
    return out.getvalue()
