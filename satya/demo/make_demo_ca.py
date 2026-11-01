"""Create a clearly labelled DEMO certificate authority for C2PA test signing.

Produces in demo/pki/:
  demo-root.pem                      trust anchor (only loaded via SATYA_DEMO_CA)
  kamera.pem / kamera.key            "Satya DEMO Kamera"  (simulates a C2PA camera)
  selbstsigniert.pem / .key          untrusted chain (simulates a forger with an own CA)

Never use these keys outside of the demo.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

OUT = Path(__file__).parent / "pki"
DOC_SIGNING = x509.ObjectIdentifier("1.3.6.1.5.5.7.3.36")


def _name(cn: str, org: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COUNTRY_NAME, "DE"),
                      x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
                      x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def make_ca(cn: str, org: str):
    key = ec.generate_private_key(ec.SECP256R1())
    now = dt.datetime.now(dt.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(_name(cn, org)).issuer_name(_name(cn, org))
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False, key_encipherment=False,
                                         data_encipherment=False, key_agreement=False, key_cert_sign=True,
                                         crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
            .sign(key, hashes.SHA256()))
    return key, cert


def make_leaf(ca_key, ca_cert, cn: str, org: str):
    key = ec.generate_private_key(ec.SECP256R1())
    now = dt.datetime.now(dt.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(_name(cn, org)).issuer_name(ca_cert.subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=730))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
                                         data_encipherment=False, key_agreement=False, key_cert_sign=False,
                                         crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.ExtendedKeyUsage([DOC_SIGNING, ExtendedKeyUsageOID.EMAIL_PROTECTION]), critical=False)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256()))
    return key, cert


def pem(cert) -> bytes:
    return cert.public_bytes(serialization.Encoding.PEM)


def key_pem(key) -> bytes:
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    root_key, root = make_ca("Satya DEMO Root CA", "Satya DEMO")
    (OUT / "demo-root.pem").write_bytes(pem(root))
    k, c = make_leaf(root_key, root, "Satya DEMO Kamera", "Satya DEMO")
    (OUT / "kamera.pem").write_bytes(pem(c) + pem(root))
    (OUT / "kamera.key").write_bytes(key_pem(k))
    # a forger's own CA - not on any trust list
    f_key, f_root = make_ca("Faelscher Root CA", "OpenAI OpCo, LLC (gefaelscht)")
    k2, c2 = make_leaf(f_key, f_root, "Faelscher Signer", "OpenAI OpCo, LLC (gefaelscht)")
    (OUT / "selbstsigniert.pem").write_bytes(pem(c2) + pem(f_root))
    (OUT / "selbstsigniert.key").write_bytes(key_pem(k2))
    print("Demo-PKI erzeugt in", OUT)


if __name__ == "__main__":
    main()
