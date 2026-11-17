"""Tiny MaxMind DB writer used only to build test fixtures."""

from __future__ import annotations

import ipaddress
import struct
from typing import Any

MARKER = b"\xab\xcd\xefMaxMind.com"


def _ctrl(type_: int, size: int) -> bytes:
    if size < 29:
        first, extra = size, b""
    elif size < 285:
        first, extra = 29, bytes([size - 29])
    elif size < 65821:
        first, extra = 30, (size - 285).to_bytes(2, "big")
    else:
        first, extra = 31, (size - 65821).to_bytes(3, "big")
    if type_ <= 7:
        return bytes([(type_ << 5) | first]) + extra
    return bytes([first, type_ - 7]) + extra


def encode(value: Any) -> bytes:
    if isinstance(value, bool):
        return _ctrl(14, int(value))
    if isinstance(value, str):
        raw = value.encode()
        return _ctrl(2, len(raw)) + raw
    if isinstance(value, bytes):
        return _ctrl(4, len(value)) + value
    if isinstance(value, float):
        return _ctrl(3, 8) + struct.pack(">d", value)
    if isinstance(value, int):
        if value < 0:
            return _ctrl(8, 4) + value.to_bytes(4, "big", signed=True)
        raw = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")
        if value < 2**16:
            return _ctrl(5, len(raw)) + raw
        if value < 2**32:
            return _ctrl(6, len(raw)) + raw
        if value < 2**64:
            return _ctrl(9, len(raw)) + raw
        return _ctrl(10, len(raw)) + raw
    if isinstance(value, dict):
        out = _ctrl(7, len(value))
        for k, v in value.items():
            out += encode(k) + encode(v)
        return out
    if isinstance(value, list):
        out = _ctrl(11, len(value))
        for v in value:
            out += encode(v)
        return out
    raise TypeError(value)


def pointer(offset: int) -> bytes:
    if offset < 2048:
        return bytes([0x20 | (offset >> 8), offset & 0xFF])
    if offset < 526336:
        v = offset - 2048
        return bytes([0x28 | (v >> 16)]) + (v & 0xFFFF).to_bytes(2, "big")
    if offset < 134744064:
        v = offset - 526336
        return bytes([0x30 | (v >> 24)]) + (v & 0xFFFFFF).to_bytes(3, "big")
    return bytes([0x38]) + offset.to_bytes(4, "big")


def build(
    entries: list[tuple[str, dict[str, Any]]],
    *,
    ip_version: int = 6,
    record_size: int = 28,
    shared_prefix: bytes = b"",
) -> bytes:
    """Build an MMDB. `shared_prefix` is raw data placed at data offset 0."""
    data = bytearray(shared_prefix)
    nodes: list[list[Any]] = [[None, None]]
    bits_total = 128 if ip_version == 6 else 32
    for network, record in entries:
        net = ipaddress.ip_network(network)
        if net.version == 4 and ip_version == 6:
            value = int(net.network_address)
            prefix = net.prefixlen + 96
        else:
            value = int(net.network_address)
            prefix = net.prefixlen
        offset = len(data)
        data += encode(record)
        node = 0
        for i in range(prefix):
            bit = (value >> (bits_total - 1 - i)) & 1
            if i == prefix - 1:
                nodes[node][bit] = ("data", offset)
                break
            nxt = nodes[node][bit]
            if not isinstance(nxt, int):
                nodes.append([None, None])
                nxt = len(nodes) - 1
                nodes[node][bit] = nxt
            node = nxt
    count = len(nodes)

    def rec(value: Any) -> int:
        if value is None:
            return count
        if isinstance(value, int):
            return value
        return count + 16 + value[1]

    tree = bytearray()
    for left, right in nodes:
        lv, rv = rec(left), rec(right)
        if record_size == 24:
            tree += lv.to_bytes(3, "big") + rv.to_bytes(3, "big")
        elif record_size == 28:
            tree += (lv & 0xFFFFFF).to_bytes(3, "big")
            tree += bytes([((lv >> 24) & 0x0F) << 4 | ((rv >> 24) & 0x0F)])
            tree += (rv & 0xFFFFFF).to_bytes(3, "big")
        else:
            tree += lv.to_bytes(4, "big") + rv.to_bytes(4, "big")
    metadata = {
        "node_count": count,
        "record_size": record_size,
        "ip_version": ip_version,
        "database_type": "DBIP-Country-Lite",
        "build_epoch": 2**40,
        "languages": ["en"],
        "binary_format_major_version": 2,
        "binary_format_minor_version": 0,
        "description": {"en": "test"},
    }
    return bytes(tree) + b"\x00" * 16 + bytes(data) + MARKER + encode(metadata)
