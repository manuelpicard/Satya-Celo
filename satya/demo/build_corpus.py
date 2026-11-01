"""Build the evaluation corpus (demo/corpus/) with known ground truth.

Requires: anvil running + demo/seed_chain.py executed (demo/deployment.json).
Every item is labelled with its TRUE origin ("ki" or "mensch") - Satya never sees it.
"""

from __future__ import annotations

import io
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from eth_account import Account
from PIL import Image, PngImagePlugin
from web3 import Web3

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from c2pa_sign import sign_image  # noqa: E402
from seed_chain import KEYS  # noqa: E402

from satya.hashing import phash64, sha256_bytes, simhash64, text_hash  # noqa: E402
from satya.seal import seal_block, seal_text, sign_seal  # noqa: E402
from satya.watermark_check import check_open_watermarks, embed_open_watermark  # noqa: E402

SRC = HERE / "corpus_src"
OUT = HERE / "corpus"
PKI = HERE / "pki"
DEP = json.loads((HERE / "deployment.json").read_text())
w3 = Web3(Web3.HTTPProvider(DEP["rpc"]))
REG = w3.eth.contract(address=DEP["registry"], abi=json.loads((ROOT / "satya/abi/SatyaRegistry.json").read_text())["abi"])
ACC = {k: Account.from_key(v) for k, v in KEYS.items()}
CHAIN, REGADDR = DEP["chainId"], DEP["registry"]

KAFKA = ("Als Gregor Samsa eines Morgens aus unruhigen Träumen erwachte, fand er sich in seinem Bett zu einem "
         "ungeheueren Ungeziefer verwandelt. Er lag auf seinem panzerartig harten Rücken und sah, wenn er den Kopf "
         "ein wenig hob, seinen gewölbten, braunen, von bogenförmigen Versteifungen geteilten Bauch, auf dessen Höhe "
         "sich die Bettdecke, zum gänzlichen Niedergleiten bereit, kaum noch erhalten konnte.")
GOETHE = ("Habe nun, ach! Philosophie,\nJuristerei und Medizin,\nUnd leider auch Theologie\nDurchaus studiert, mit "
          "heißem Bemühn.\nDa steh ich nun, ich armer Tor!\nUnd bin so klug als wie zuvor;")
GRIMM = ("Es war einmal eine kleine süße Dirne, die hatte jedermann lieb, der sie nur ansah, am allerliebsten aber "
         "ihre Großmutter, die wußte gar nicht, was sie alles dem Kind geben sollte.")

items: list[dict] = []


def add(name: str, truth: str, desc: str, expected: str, data: bytes | str) -> Path:
    p = OUT / name
    if isinstance(data, str):
        p.write_text(data, encoding="utf-8")
    else:
        p.write_bytes(data)
    items.append({"datei": name, "wahrheit": truth, "beschreibung": desc, "erwartet": expected})
    return p


def tx(acct, fn) -> None:
    try:
        fn.call({"from": acct.address})  # dry run: skip if already attested
    except Exception as e:  # noqa: BLE001
        if "AlreadyAttested" in str(e) or "0x" in str(e):
            print("   (übersprungen:", str(e)[:60], ")")
            return
        raise
    t = fn.build_transaction({"from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address), "chainId": CHAIN})
    rc = w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(acct.sign_transaction(t).raw_transaction))
    assert rc["status"] == 1


def soft(hexstr: str | None) -> bytes:
    return bytes.fromhex(hexstr[2:]) if hexstr else b"\x00" * 8


def png_bytes(img: Image.Image, **kw) -> bytes:
    b = io.BytesIO()
    img.save(b, "PNG", **kw)
    return b.getvalue()


def jpeg_bytes(img: Image.Image, q: int = 90) -> bytes:
    b = io.BytesIO()
    img.convert("RGB").save(b, "JPEG", quality=q)
    return b.getvalue()


def anchor_human_text(who: str, text: str, ai_use: int) -> None:
    s = sign_seal(KEYS[who], text_hash(text), ai_use, CHAIN, REGADDR)
    tx(ACC["governance"], REG.functions.anchorSeal(s.as_tuple(), bytes.fromhex(s.sig[2:]), soft(simhash64(text))))


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    gpt = (HERE / "samples/ki_gpt_image.png").read_bytes()
    nano = (HERE / "samples/ki_nano_banana.png").read_bytes()
    photo = (SRC / "foto_A.jpg").read_bytes()
    photo2 = (SRC / "foto_XCA.jpg").read_bytes()

    # ------------------------------------------------------------------ images
    add("01_bild_ki_openai_original.png", "ki", "Echtes Bild aus gpt-image (OpenAI), unverändert mit C2PA", "KI_NACHGEWIESEN", gpt)
    add("02_bild_ki_google_original.png", "ki", "Echtes Bild aus Nano Banana 2 (Google), unverändert mit C2PA", "KI_NACHGEWIESEN", nano)
    gpt_img = Image.open(io.BytesIO(gpt))
    add("03_bild_ki_openai_reencodiert.jpg", "ki", "OpenAI-Bild als JPEG neu gespeichert (Metadaten weg, wie nach Upload/Screenshot); "
        "Anbieter hat das Original im Register hinterlegt", "UNBESTIMMT", jpeg_bytes(gpt_img, 88))
    tx(ACC["provider"], REG.functions.attestAI(Web3.to_bytes(hexstr=sha256_bytes(gpt)), soft(phash64(gpt))))
    d = bytearray(nano)
    i = d.rfind(b"IDAT") + 5000
    d[i] ^= 0xFF
    add("04_bild_ki_google_manipuliert.png", "ki", "Google-Bild, nach der Signatur ein Byte der Bilddaten verändert", "HERKUNFT_GEBROCHEN", bytes(d))
    nano_small = Image.open(io.BytesIO(nano)).convert("RGB").resize((1024, 1024))
    add("05_bild_ki_google_screenshot.png", "ki", "Google-Bild verkleinert und ohne Metadaten neu gespeichert", "UNBESTIMMT", png_bytes(nano_small))

    add("06_foto_kamera_signiert.jpg", "mensch", "Echtes Foto, von (Demo-)Kamera mit C2PA signiert: digitalCapture", "KAMERA_NACHGEWIESEN",
        sign_image(photo, "image/jpeg", PKI / "kamera.pem", PKI / "kamera.key", "digitalCapture", "Satya DEMO Kamera", "foto.jpg"))
    add("07_foto_unsigniert.jpg", "mensch", "Echtes Foto ohne jeden Nachweis", "UNBESTIMMT", photo)
    add("08_foto_gefaelschte_ki_signatur.jpg", "mensch",
        "Echtes Foto, Fälscher signiert mit eigener CA als „OpenAI OpCo, LLC“: trainedAlgorithmicMedia", "UNBESTIMMT",
        sign_image(photo, "image/jpeg", PKI / "selbstsigniert.pem", PKI / "selbstsigniert.key", "trainedAlgorithmicMedia", "Faelscher", "x.jpg"))
    arr = cv2.imdecode(np.frombuffer(photo2, np.uint8), cv2.IMREAD_COLOR)
    _, base_png = cv2.imencode(".png", arr)
    wm = embed_open_watermark(base_png.tobytes())
    assert check_open_watermarks(wm, "image/png"), "Wasserzeichen-Einbettung fehlgeschlagen"
    add("09_foto_mit_sd_wasserzeichen.png", "mensch", "Echtes Foto, nachträglich das öffentliche Stable-Diffusion-XL-Wasserzeichen eingebettet",
        "UNBESTIMMT", wm)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("parameters", "a photo of a street, masterpiece\nNegative prompt: blurry\nSteps: 30, Sampler: DPM++ 2M, "
                  "CFG scale: 7, Seed: 1234, Size: 1024x683, Model: sd_xl_base_1.0")
    add("10_foto_gefaelschte_sd_parameter.png", "mensch", "Echtes Foto mit nachträglich eingefügten Stable-Diffusion-Parametern",
        "UNBESTIMMT", png_bytes(Image.open(io.BytesIO(photo)), pnginfo=meta))
    crop = jpeg_bytes(Image.open(io.BytesIO(photo)).crop((0, 0, 800, 600)), 92)
    add("11_foto_mensch_bezeugt.jpg", "mensch", "Echtes Foto, Alice (verifizierter Mensch) hat es im Register als „ohne KI“ bezeugt",
        "MENSCH_BEZEUGT", crop)
    tx(ACC["alice"], REG.functions.attest(Web3.to_bytes(hexstr=sha256_bytes(crop)), 0, soft(phash64(crop))))

    # ------------------------------------------------------------------- texts
    sealed, _ = seal_text(KAFKA, KEYS["alice"], 0, CHAIN, REGADDR)
    add("12_text_kafka_versiegelt.txt", "mensch", "Kafka (1915), von Alice mit eingebettetem Siegel „ohne KI“ versehen", "MENSCH_BEZEUGT", sealed)
    add("13_text_kafka_versiegelt_veraendert.txt", "mensch", "Wie 12, danach ein Wort geändert", "HERKUNFT_GEBROCHEN",
        sealed.replace("ungeheueren", "riesigen"))
    add("14_text_goethe_registriert.txt", "mensch", "Goethe, Faust I: Alice hat ihn im Register als „ohne KI“ verankert", "MENSCH_BEZEUGT", GOETHE + "\n")
    anchor_human_text("alice", GOETHE, 0)
    add("15_text_grimm_ohne_nachweis.txt", "mensch", "Brüder Grimm, ohne jeden Nachweis", "UNBESTIMMT", GRIMM + "\n")

    bienen = (SRC / "ki_text_bienen.txt").read_text(encoding="utf-8")
    add("16_text_ki_bienen_registriert.txt", "ki", "Echter KI-Text (gpt-5-mini), vom Anbieter im Register hinterlegt", "KI_NACHGEWIESEN", bienen)
    tx(ACC["provider"], REG.functions.attestAI(Web3.to_bytes(hexstr=text_hash(bienen)), soft(simhash64(bienen))))
    add("17_text_ki_bienen_paraphrasiert.txt", "ki", "Text 16 von einer KI leicht umformuliert", "UNBESTIMMT",
        (SRC / "ki_text_bienen_paraphrasiert.txt").read_text(encoding="utf-8"))
    fahrrad = (SRC / "ki_text_fahrrad.txt").read_text(encoding="utf-8")
    add("18_text_ki_fahrrad_ohne_nachweis.txt", "ki", "Echter KI-Text ohne jeden Nachweis", "UNBESTIMMT", fahrrad)
    herbst = (SRC / "ki_text_herbst.txt").read_text(encoding="utf-8")
    s_agent = sign_seal(KEYS["agent"], text_hash(herbst), 0, CHAIN, REGADDR)
    add("19_text_ki_herbst_agent_siegel.txt", "ki", "KI-Text, ein KI-Agent (ohne HMN-Credential) versiegelt ihn als „ohne KI“",
        "UNBESTIMMT", herbst.strip() + "\n\n" + seal_block(s_agent) + "\n")
    tempo = (SRC / "ki_text_tempolimit.txt").read_text(encoding="utf-8")
    add("20_text_ki_tempolimit_widerspruch.txt", "ki", "KI-Text vom Anbieter registriert; Mallory (verifiziert) verankert trotzdem „ohne KI“",
        "WIDERSPRUCH", tempo)
    tx(ACC["provider"], REG.functions.attestAI(Web3.to_bytes(hexstr=text_hash(tempo)), soft(simhash64(tempo))))
    anchor_human_text("mallory", tempo, 0)
    herbst_edit = herbst.replace("Heute Morgen", "Gestern Morgen", 1)
    sealed_assist, _ = seal_text(herbst_edit, KEYS["alice"], 1, CHAIN, REGADDR)
    add("21_text_ki_unterstuetzt_alice.txt", "ki", "KI-Entwurf, von Alice überarbeitet und ehrlich als „mit KI-Unterstützung“ versiegelt",
        "KI_NACHGEWIESEN", sealed_assist)
    sealed_lie, _ = seal_text(fahrrad, KEYS["mallory"], 0, CHAIN, REGADDR)
    add("22_text_ki_mallory_luege.txt", "ki", "KI-Text, Mallory (verifiziert) versiegelt ihn wahrheitswidrig als „ohne KI“ (unentdeckte Lüge)",
        "MENSCH_BEZEUGT (falsch, Restrisiko)", sealed_lie)

    (OUT / "corpus.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(items)} Korpus-Einträge in {OUT}")


if __name__ == "__main__":
    main()
