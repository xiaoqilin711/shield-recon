"""Tests for shieldrecon.primitives (run with pytest, or plain python)."""

from shieldrecon.primitives import CONSTANTS, guess_digest, identify_constant


def test_md5_iv_exact():
    assert any(m["name"] == "md5" and m["kind"] == "exact"
               for m in identify_constant(CONSTANTS["md5"]))


def test_sha256_iv_exact():
    assert any(m["name"] == "sha256" and m["kind"] == "exact"
               for m in identify_constant(CONSTANTS["sha256"]))


def test_md5_iv_prefix():
    assert any(m["name"] == "md5" and m["kind"] == "prefix"
               for m in identify_constant(CONSTANTS["md5"][:16]))


def test_sha256_sha512_share_first_word():
    # 6a09e667 is the first word of both SHA-256 and SHA-512: both surface.
    names = {m["name"] for m in identify_constant("6a09e667")}
    assert {"sha256", "sha512"} <= names


def test_aes_sbox_prefix_exact():
    assert any(m["name"] == "aes-sbox" and m["kind"] == "exact"
               for m in identify_constant(CONSTANTS["aes-sbox"]))


def test_unknown_constant_no_match():
    assert identify_constant("deadbeef" * 8) == []


def test_guess_digest_lengths():
    assert any(m["name"] == "sha1" for m in guess_digest("ab" * 20))
    assert any(m["name"] == "sha256" for m in guess_digest("ab" * 32))
    assert any(m["name"] == "sha512" for m in guess_digest("ab" * 64))


if __name__ == "__main__":
    for name in sorted(n for n in globals() if n.startswith("test_")):
        globals()[name]()
        print(f"{name}: ok")
    print("all tests passed")
