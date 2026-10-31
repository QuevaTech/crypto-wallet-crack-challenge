#!/usr/bin/env python3
"""Independent verifier for the QuevaTech BIP39 challenge repository.

Checks, from the published files only:
  1. every public phrase is a valid BIP39 24-word mnemonic (checksum included)
  2. every phrase matches sha256(phrase) in manifest.json
  3. every derived ETH address matches manifest.json
  4. the redacted phrase has 19 known words + 5 placeholders
  5. MANIFEST.sha256 matches the data files

Exit code 0 = all checks passed.

Usage:  python tools/verify_phrases.py [--data data] [--addresses]
        (--addresses also re-derives 2001 ETH addresses; ~30 s)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

try:
    from mnemonic import Mnemonic
except ImportError:  # pragma: no cover
    sys.exit("pip install mnemonic")


def load_phrases(path: pathlib.Path) -> list[str]:
    return [ln.strip() for ln in path.read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--addresses", action="store_true")
    args = ap.parse_args()
    data = pathlib.Path(args.data)

    manifest = json.loads((data / "manifest.json").read_text())
    mnemo = Mnemonic("english")
    failures: list[str] = []

    # 5. MANIFEST.sha256
    for line in (data / "MANIFEST.sha256").read_text().splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(None, 1)
        target = data.parent / rel.strip()
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            failures.append(f"MANIFEST.sha256 mismatch: {rel}")

    first = load_phrases(data / "phrases_0001-1000.txt")
    second = load_phrases(data / "phrases_1002-2001.txt")
    print(f"public phrases: {len(first)} + {len(second)} = {len(first)+len(second)}")

    # 1 + 2
    bad = 0
    for idx, phrase in [(i + 1, p) for i, p in enumerate(first)] + \
                       [(i + 1002, p) for i, p in enumerate(second)]:
        entry = manifest["entries"].get(str(idx))
        if entry is None:
            failures.append(f"phrase {idx} missing from manifest")
            continue
        if not mnemo.check(phrase):
            bad += 1
            failures.append(f"phrase {idx} fails BIP39 checksum")
        if hashlib.sha256(phrase.encode()).hexdigest() != entry["sha256"]:
            failures.append(f"phrase {idx} sha256 mismatch")
    print(f"checksum failures: {bad}")

    # 4. redacted
    red = load_phrases(data / "phrase_1001_redacted.txt")[0].split()
    known = [w for w in red if not w.startswith("█")]
    hidden = len(red) - len(known)
    print(f"redacted: {len(known)} known + {hidden} hidden words")
    if len(red) != 24 or hidden != manifest["hidden_words"]:
        failures.append("redacted phrase shape unexpected")

    # 3. addresses
    if args.addresses:
        from eth_account import Account
        Account.enable_unaudited_hdwallet_features()
        mism = 0
        for idx, phrase in [(i + 1, p) for i, p in enumerate(first)] + \
                           [(i + 1002, p) for i, p in enumerate(second)]:
            addr = Account.from_mnemonic(phrase, account_path="m/44'/60'/0'/0/0").address
            if addr != manifest["entries"][str(idx)]["eth_address"]:
                mism += 1
        print(f"address mismatches: {mism}")
        if mism:
            failures.append(f"{mism} address mismatches")

    if failures:
        print("\nFAILED:")
        for f in failures[:20]:
            print(" -", f)
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
