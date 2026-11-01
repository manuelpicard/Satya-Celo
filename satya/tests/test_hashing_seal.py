from hypothesis import given
from hypothesis import strategies as st

from satya.devkeys import anvil_key
from satya.hashing import hamming, normalize_text, simhash64, strip_seal, text_hash
from satya.ledger import seal_evidence
from satya.model import Direction, Tier
from satya.seal import extract_seal, recover_signer, seal_text, sign_seal

KEY = anvil_key(2)
OTHER = anvil_key(4)
REG = "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"


@given(st.text(max_size=300))
def test_normalization_is_idempotent(s):
    assert normalize_text(normalize_text(s)) == normalize_text(s)


def test_normalization_ignores_formatting_noise():
    a = "Hallo Welt\r\nZweite Zeile   \n"
    b = "Hallo\u200b Welt\nZweite Zeile"
    assert text_hash(a) == text_hash(b.replace("\u200b", ""))
    assert text_hash("Hallo Welt\nZweite Zeile") == text_hash(a)
    assert text_hash("Hallo Welt") != text_hash("Hallo Welt!")


def test_simhash_similarity():
    a = "Die Wildbiene bestäubt viele Kulturpflanzen und sichert so die Ernte in der Landwirtschaft."
    b = "Die Wildbiene bestäubt viele Kulturpflanzen und sichert so die Ernte in der Landwirtschaft!"
    c = "Völlig anderer Text über Fahrräder, Autobahnen und das Wetter im Herbst des Jahres."
    assert hamming(simhash64(a), simhash64(b)) < hamming(simhash64(a), simhash64(c))


def test_seal_roundtrip_and_strip():
    text = "Mein eigener Text.\nZweite Zeile."
    sealed, seal = seal_text(text, KEY, 0, 31337, REG)
    clean, parsed, err = extract_seal(sealed)
    assert err is None and parsed == seal
    assert text_hash(clean) == seal.hash == text_hash(text)
    assert recover_signer(parsed).lower() == seal.signer.lower()
    assert strip_seal(clean)[1] is None


def test_tampered_text_breaks_seal():
    sealed, seal = seal_text("Original", KEY, 0, 31337, REG)
    clean, parsed, _ = extract_seal(sealed.replace("Original", "Fälschung"))
    ev = seal_evidence(parsed, text_hash(clean), None)
    assert ev[0].tier == Tier.PROOF and ev[0].direction == Direction.BROKEN


def test_forged_signer_is_rejected_offline():
    s = sign_seal(OTHER, text_hash("x"), 0, 31337, REG)
    s.signer = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"  # claim to be Alice
    # the signer address is part of the signed message, so the recovered key never matches the claim
    assert recover_signer(s).lower() != s.signer.lower()
    ev = seal_evidence(s, text_hash("x"), None)
    assert ev[0].tier == Tier.HINT and "ungültig" in ev[0].title


def test_seal_without_registry_is_only_a_hint():
    s = sign_seal(KEY, text_hash("x"), 0, 31337, REG)
    ev = seal_evidence(s, text_hash("x"), None)
    assert ev[0].tier == Tier.HINT  # human status cannot be checked offline


def test_seal_bound_to_chain_and_registry():
    s = sign_seal(KEY, text_hash("x"), 0, 31337, REG)
    s.chainId = 1  # replay on another chain must not verify as the same signer
    assert recover_signer(s).lower() != s.signer.lower()
