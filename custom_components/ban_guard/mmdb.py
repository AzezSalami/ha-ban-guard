"""A minimal, pure-Python MaxMind DB (MMDB) reader.

Implements the subset of https://maxmind.github.io/MaxMind-DB/ needed to look
up addresses in DB-IP Lite databases: 24/28/32-bit search trees and every
data type. Written in-tree so Ban Guard has no third-party requirements.
The whole database is held in memory (bounded by the size cap) so lookups
never touch the disk from the event loop.
"""

from __future__ import annotations

import ipaddress
import struct
from typing import Any

_METADATA_MARKER = b"\xab\xcd\xefMaxMind.com"
_DATA_SECTION_SEPARATOR = 16


class InvalidDatabaseError(ValueError):
    """The file is not a valid MaxMind DB."""


class _Decoder:
    def __init__(self, buf: bytes, pointer_base: int) -> None:
        self._buf = buf
        self._base = pointer_base

    def decode(self, offset: int) -> tuple[Any, int]:
        buf = self._buf
        if offset >= len(buf):
            raise InvalidDatabaseError("Offset out of range")
        ctrl = buf[offset]
        offset += 1
        type_ = ctrl >> 5
        if type_ == 1:  # pointer
            pointer, offset = self._pointer(ctrl, offset)
            value, _ = self.decode(pointer)
            return value, offset
        if type_ == 0:
            type_ = 7 + buf[offset]
            offset += 1
        size = ctrl & 0x1F
        if size >= 29:
            extra = size - 28
            tail = int.from_bytes(buf[offset : offset + extra], "big")
            offset += extra
            size = {1: 29, 2: 285, 3: 65821}[extra] + tail
        return self._value(type_, size, offset)

    def _pointer(self, ctrl: int, offset: int) -> tuple[int, int]:
        buf = self._buf
        ss = (ctrl >> 3) & 0x3
        vvv = ctrl & 0x7
        if ss == 0:
            pointer = (vvv << 8) | buf[offset]
            offset += 1
        elif ss == 1:
            pointer = ((vvv << 16) | int.from_bytes(buf[offset : offset + 2], "big")) + 2048
            offset += 2
        elif ss == 2:
            pointer = ((vvv << 24) | int.from_bytes(buf[offset : offset + 3], "big")) + 526336
            offset += 3
        else:
            pointer = int.from_bytes(buf[offset : offset + 4], "big")
            offset += 4
        return pointer + self._base, offset

    def _value(self, type_: int, size: int, offset: int) -> tuple[Any, int]:
        buf = self._buf
        end = offset + size
        match type_:
            case 2:
                return buf[offset:end].decode("utf-8"), end
            case 3:
                return struct.unpack(">d", buf[offset : offset + 8])[0], offset + 8
            case 4:
                return bytes(buf[offset:end]), end
            case 5 | 6 | 9 | 10:
                return int.from_bytes(buf[offset:end], "big"), end
            case 7:
                result: dict[str, Any] = {}
                for _ in range(size):
                    key, offset = self.decode(offset)
                    value, offset = self.decode(offset)
                    result[str(key)] = value
                return result, offset
            case 8:
                return int.from_bytes(buf[offset:end], "big", signed=size == 4), end
            case 11:
                items: list[Any] = []
                for _ in range(size):
                    value, offset = self.decode(offset)
                    items.append(value)
                return items, offset
            case 14:
                return bool(size), offset
            case 15:
                return struct.unpack(">f", buf[offset : offset + 4])[0], offset + 4
        raise InvalidDatabaseError(f"Unknown data type {type_}")


class Reader:
    """Look up IP addresses in an in-memory MMDB."""

    def __init__(self, buf: bytes) -> None:
        """Parse metadata and prepare the search tree."""
        self._buf = buf
        start = buf.rfind(_METADATA_MARKER, max(0, len(buf) - 128 * 1024))
        if start < 0:
            raise InvalidDatabaseError("Metadata marker not found")
        meta_start = start + len(_METADATA_MARKER)
        metadata, _ = _Decoder(buf, meta_start).decode(meta_start)
        if not isinstance(metadata, dict):
            raise InvalidDatabaseError("Metadata is not a map")
        try:
            self.node_count = int(metadata["node_count"])
            self.record_size = int(metadata["record_size"])
            self.ip_version = int(metadata["ip_version"])
        except (KeyError, TypeError, ValueError) as err:
            raise InvalidDatabaseError("Incomplete metadata") from err
        if self.record_size not in (24, 28, 32):
            raise InvalidDatabaseError(f"Unsupported record size {self.record_size}")
        self.metadata = metadata
        self._node_bytes = self.record_size * 2 // 8
        self._tree_size = self._node_bytes * self.node_count
        self._decoder = _Decoder(buf, self._tree_size + _DATA_SECTION_SEPARATOR)
        self._ipv4_start = 0
        if self.ip_version == 6:
            node = 0
            for _ in range(96):
                if node >= self.node_count:
                    break
                node = self._record(node, 0)
            self._ipv4_start = node

    @property
    def database_type(self) -> str:
        """The database_type metadata field."""
        return str(self.metadata.get("database_type", ""))

    @property
    def build_epoch(self) -> int:
        """Build timestamp."""
        return int(self.metadata.get("build_epoch", 0))

    def _record(self, node: int, bit: int) -> int:
        buf = self._buf
        base = node * self._node_bytes
        if self.record_size == 24:
            offset = base + bit * 3
            return int.from_bytes(buf[offset : offset + 3], "big")
        if self.record_size == 28:
            if bit == 0:
                middle = (buf[base + 3] & 0xF0) << 20
                return middle | int.from_bytes(buf[base : base + 3], "big")
            middle = (buf[base + 3] & 0x0F) << 24
            return middle | int.from_bytes(buf[base + 4 : base + 7], "big")
        offset = base + bit * 4
        return int.from_bytes(buf[offset : offset + 4], "big")

    def get(self, address: str | ipaddress.IPv4Address | ipaddress.IPv6Address) -> Any:
        """Return the record for an address, or None."""
        addr = ipaddress.ip_address(address)
        if addr.version == 6 and self.ip_version == 4:
            return None
        packed = addr.packed
        bit_count = len(packed) * 8
        node = self._ipv4_start if addr.version == 4 and self.ip_version == 6 else 0
        for i in range(bit_count):
            if node >= self.node_count:
                break
            bit = (packed[i >> 3] >> (7 - (i & 7))) & 1
            node = self._record(node, bit)
        if node == self.node_count:
            return None
        if node > self.node_count:
            offset = node - self.node_count - _DATA_SECTION_SEPARATOR
            resolved = self._tree_size + _DATA_SECTION_SEPARATOR + offset
            if resolved >= len(self._buf):
                raise InvalidDatabaseError("Invalid data pointer")
            value, _ = self._decoder.decode(resolved)
            return value
        raise InvalidDatabaseError("Invalid node in search tree")
