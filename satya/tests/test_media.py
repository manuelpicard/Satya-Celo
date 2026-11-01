import io
import json
from pathlib import Path

import pytest
from PIL import Image

from satya.c2pa_check import C2paChecker, TrustConfig, sniff_mime
from satya.metadata_check import check_metadata
from satya.model import Direction, Tier
from satya.watermark_check import check_open_watermarks

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "demo/samples"
CORPUS = ROOT / "demo/corpus"
pytestmark = pytest.mark.skipif(not (SAMPLES / "ki_gpt_image.png").exists(), reason="Beispielbilder fehlen")


@pytest.fixture(scope="module")
def checker():
    return C2paChecker(TrustConfig.default())


@pytest.mark.parametrize("name,issuer", [("ki_gpt_image.png", "OpenAI"), ("ki_nano_banana.png", "Google")])
def test_real_ai_images_are_proven(checker, name, issuer):
    data = (SAMPLES / name).read_bytes()
    ev = checker.check(data, sniff_mime(data))
    proof = [e for e in ev if e.tier == Tier.PROOF]
    assert len(proof) == 1 and proof[0].direction == Direction.AI and issuer in proof[0].issuer


def test_reencoding_removes_proof_but_never_flips(checker):
    img = Image.open(SAMPLES / "ki_gpt_image.png")
    b = io.BytesIO()
    img.convert("RGB").save(b, "JPEG", quality=90)
    ev = checker.check(b.getvalue(), "image/jpeg")
    assert all(e.tier == Tier.INFO for e in ev)


def test_tampering_is_detected(checker):
    d = bytearray((SAMPLES / "ki_nano_banana.png").read_bytes())
    d[d.rfind(b"IDAT") + 5000] ^= 0xFF
    ev = checker.check(bytes(d), "image/png")
    assert any(e.tier == Tier.PROOF and e.direction == Direction.BROKEN for e in ev)
    assert not any(e.tier == Tier.PROOF and e.direction == Direction.AI for e in ev)


def test_metadata_word_boundaries():
    # "ImageNumber" in camera XMP must not be read as the generator "Imagen"
    xmp = b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF aux:ImageNumber="0"/></x:xmpmeta>'
    img = Image.new("RGB", (64, 64))
    b = io.BytesIO()
    img.save(b, "PNG")
    data = b.getvalue().replace(b"IEND", b"IEND") + xmp
    assert check_metadata(data, "image/png") == []


def test_open_watermark_no_false_positive_on_ai_and_clean_images():
    for name in ("ki_gpt_image.png",):
        data = (SAMPLES / name).read_bytes()
        assert check_open_watermarks(data, "image/png") == []


@pytest.mark.skipif(not (ROOT / "demo/auswertung.json").exists(), reason="Auswertung fehlt")
def test_evaluation_guarantees():
    r = json.loads((ROOT / "demo/auswertung.json").read_text(encoding="utf-8"))
    for phase in ("phase1", "phase2"):
        for row in r[phase]["zeilen"]:
            if row["sicher"]:
                assert row["beweise"], f"sicheres Urteil ohne Beweis: {row['datei']}"
    # the only wrong certain verdict is the documented, undetected lie of a verified human
    assert r["phase1"]["statistik"]["falsch_sicher"] == ["22_text_ki_mallory_luege.txt"]
    assert r["phase2"]["statistik"]["sicher_falsch"] == 0
