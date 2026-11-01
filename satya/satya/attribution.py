"""Minimal ERC-8021 Schema-2 encoder for Satya's EIP-3009 relayer.

The wire layout and canonical short-key map match @celo/attribution-tags:
CBOR({a: app, w: wallet, s?: [service...]}) || uint16_be(len(CBOR)) || 0x02 || marker.
Keep vectors in tests cross-checked against the official Celo SDK.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

ERC_8021_MARKER = bytes.fromhex("80218021802180218021802180218021")
_CODE = re.compile(r"^[a-z0-9_]{1,32}$")


def _code(value: str, role: str) -> str:
    if not isinstance(value, str) or not _CODE.fullmatch(value):
        raise ValueError(f"invalid ERC-8021 {role} code")
    return value


def _cbor_length(major: int, length: int) -> bytes:
    if length < 0:
        raise ValueError("negative CBOR length")
    if length < 24:
        return bytes([(major << 5) | length])
    if length <= 0xFF:
        return bytes([(major << 5) | 24, length])
    if length <= 0xFFFF:
        return bytes([(major << 5) | 25]) + length.to_bytes(2, "big")
    raise ValueError("ERC-8021 value exceeds supported CBOR length")


def _cbor_text(value: str) -> bytes:
    raw = value.encode("utf-8")
    return _cbor_length(3, len(raw)) + raw


def _cbor_array(values: Sequence[str]) -> bytes:
    return _cbor_length(4, len(values)) + b"".join(_cbor_text(v) for v in values)


def _canonical_map(fields: dict[str, bytes]) -> bytes:
    # RFC 8949 deterministic map order: shorter encoded key first, then bytewise.
    entries = sorted((_cbor_text(key), value) for key, value in fields.items())
    return _cbor_length(5, len(entries)) + b"".join(k + v for k, v in entries)


def to_role_data_suffix(app: str, wallet: str, service: str | Sequence[str] | None = None) -> bytes:
    """Encode a role-based ERC-8021 Schema-2 suffix for a payment relay.

    The app and wallet codes are separate because the resource server and the
    transaction-submitting relayer play different roles. Service codes are
    optional; each code is validated using the Celo SDK's supported grammar.
    """
    app = _code(app, "app")
    wallet = _code(wallet, "wallet")
    fields: dict[str, bytes] = {"a": _cbor_text(app), "w": _cbor_text(wallet)}
    if service is not None:
        services = [service] if isinstance(service, str) else list(service)
        if not services:
            raise ValueError("service codes cannot be empty")
        checked = [_code(item, "service") for item in services]
        fields["s"] = _cbor_array(checked)

    cbor = _canonical_map(fields)
    if len(cbor) > 0xFFFF:
        raise ValueError("ERC-8021 CBOR map is too long")
    return cbor + len(cbor).to_bytes(2, "big") + b"\x02" + ERC_8021_MARKER


def append_role_data_suffix(calldata: str, app: str, wallet: str,
                            service: str | Sequence[str] | None = None) -> str:
    """Append a Schema-2 suffix to 0x-prefixed EVM transaction calldata."""
    if not isinstance(calldata, str) or not calldata.startswith("0x"):
        raise ValueError("calldata must be 0x-prefixed hex")
    raw = calldata[2:]
    if len(raw) % 2 or not re.fullmatch(r"[0-9a-fA-F]*", raw):
        raise ValueError("calldata must contain complete hex bytes")
    if raw.endswith(ERC_8021_MARKER.hex()):
        raise ValueError("calldata already contains an ERC-8021 tag")
    return "0x" + raw + to_role_data_suffix(app, wallet, service).hex()
