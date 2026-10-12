"""Identify whether an unknown byte constant or digest belongs to a standard hash.

A recurring time-sink in reverse engineering is re-deriving, by hand, a native
routine that is actually a standard primitive behind custom names (for example
an ``aes*``/``gaes`` family that is plain MD5). Before doing that work, diff the
routine's constants against the well-known hash initialization vectors, and its
output size against common digest lengths.

This module is deliberately tiny and uses only the standard library.
"""

from __future__ import annotations

# Hash initialization states, in the byte order they appear in a raw binary
# dump (for example a ``.rodata`` constant). Diff your extracted constant
# against these before assuming anything is "custom".
#
# MD5 init state is the little-endian words 0x67452301, 0xefcdab89,
# 0x98badcfe, 0x10325476, which sit in memory as 01 23 45 67 ... 10.
MD5_IV = "0123456789abcdeffedcba9876543210"

# SHA-1 init state, five big-endian 32-bit words.
SHA1_IV = "67452301efcdab8998badcfe10325476c3d2e1f0"

# SHA-256 init state, eight big-endian 32-bit words.
SHA256_IV = "6a09e667bb67ae853c6ef372a54ff53a510e527f9b05688c1f83d9ab5be0cd19"

# SHA-384 init state, eight big-endian 64-bit words (distinct from SHA-512).
SHA384_IV = (
    "cbbb9d5dc1059ed8629a292a367cd5079159015a3070dd17152fecd8f70e5939"
    "67332667ffc00b318eb44a8768581511db0c2e0d64f98fa747b5481dbefa4fa4"
)

# SHA-512 init state, eight big-endian 64-bit words.
SHA512_IV = (
    "6a09e667f3bcc908bb67ae8584caa73b3c6ef372fe94f82ba54ff53a5f1d36f1"
    "510e527fade682d19b05688c2b3e6c1f1f83d9abfb41bd6b5be0cd19137e2179"
)

# First 16 bytes of the AES S-box (63 7c 77 7b f2 6b 6f c5 30 01 67 2b fe d7
# ab 76). A constant that starts with this sequence is very likely the AES
# S-box.
AES_SBOX_PREFIX = "637c777bf26b6fc53001672bfed7ab76"

CONSTANTS = {
    "md5": MD5_IV,
    "sha1": SHA1_IV,
    "sha256": SHA256_IV,
    "sha384": SHA384_IV,
    "sha512": SHA512_IV,
    "aes-sbox": AES_SBOX_PREFIX,
}

# Common digest lengths in hex characters. Length alone is not definitive:
# several algorithms share a size, so results are candidates, not verdicts.
DIGEST_CANDIDATES = {
    32: ["md5", "md4", "md2"],
    40: ["sha1"],
    56: ["sha224"],
    64: ["sha256", "sha3-256"],
    96: ["sha384", "sha3-384"],
    128: ["sha512", "sha3-512"],
}


def _normalize(data: str | bytes) -> str:
    """Lower-case hex, keep only hex digits (drops spaces, 0x, separators)."""
    if isinstance(data, bytes):
        return data.hex()
    return "".join(ch for ch in data.lower() if ch in "0123456789abcdef")


def identify_constant(data: str | bytes) -> list[dict]:
    """Match a byte constant against known hash IVs and the AES S-box prefix.

    Returns a list of matches, each ``{"name": str, "kind": str}`` where
    ``kind`` is one of ``exact`` (the input equals a known constant), ``prefix``
    (the input is the start of a known constant) or ``contained`` (a known
    constant appears inside a larger input).
    """
    needle = _normalize(data)
    if not needle:
        return []
    out: list[dict] = []
    for name, const in CONSTANTS.items():
        if needle == const:
            out.append({"name": name, "kind": "exact"})
        elif len(needle) >= 8 and const.startswith(needle):
            out.append({"name": name, "kind": "prefix"})
        elif len(const) >= 32 and len(needle) > len(const) and const in needle:
            out.append({"name": name, "kind": "contained"})
    return out


def guess_digest(data: str | bytes) -> list[dict]:
    """Guess candidate hash algorithms from a digest's length in hex chars."""
    needle = _normalize(data)
    return [
        {"name": name, "length": len(needle)}
        for name in DIGEST_CANDIDATES.get(len(needle), [])
    ]
