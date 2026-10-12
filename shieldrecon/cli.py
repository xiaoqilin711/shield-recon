"""Command-line interface for shieldrecon."""

from __future__ import annotations

import argparse
import sys

from .primitives import guess_digest, identify_constant


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="shieldrecon",
        description="Check whether a constant or digest is a standard hash.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_id = sub.add_parser(
        "identify", help="match a byte constant against known hash IVs / AES S-box"
    )
    p_id.add_argument("value", help="hex string (spaces and 0x tolerated)")

    p_guess = sub.add_parser(
        "guess", help="guess hash candidates from a digest's length in hex chars"
    )
    p_guess.add_argument("value", help="hex digest string")

    args = parser.parse_args(argv)

    if args.command == "identify":
        matches = identify_constant(args.value)
        if not matches:
            print("no known-hash constant matched")
        for m in matches:
            print(f"{m['name']:<10} {m['kind']}")
        return 0

    matches = guess_digest(args.value)
    if not matches:
        print("no common digest length matched")
    for m in matches:
        print(f"{m['length']:>4} hex chars -> {m['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
