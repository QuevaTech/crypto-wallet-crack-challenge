#!/usr/bin/env python3
"""Reference solver for the QuevaTech BIP39 partial-seed challenge.

Recovers k missing words at the END of a 24-word phrase. This is a *reference*
implementation: it is correct and dependency-light, not fast. For real work it
prints ready-to-run commands for hashcat / btcrecover (see --tools).

How the search is pruned
------------------------
24 words carry 264 bits: 256 entropy + 8 checksum. The last word's 11 bits hold
3 entropy bits and the 8 checksum bits, so the number of *valid* candidates for
k hidden tail words is 2^(11k-8):

    k=2 -> 2^14   |  k=3 -> 2^25  |  k=4 -> 2^36  |  k=5 -> 2^47

Checksum checking costs one SHA-256 and rejects 255 of every 256 candidates
before the expensive PBKDF2 seed derivation. The cost here is dominated by
that SHA-256 stage, which is why the reference implementation is tolerable at
k<=3 and useless beyond it.

Usage
-----
  python tools/solve.py --k 3                 # search 3 missing tail words
  python tools/solve.py --k 2 --prefix <19 words> --limit 100000
  python tools/solve.py --k 3 --tools         # only print external tool commands
  python tools/solve.py --self-test           # validate against a synthetic case
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import pathlib
import sys
import time

WORDS: list[str] | None = None
INDEX: dict[str, int] = {}


def load_wordlist(path: pathlib.Path | None = None) -> list[str]:
    global WORDS, INDEX
    if WORDS is not None:
        return WORDS
    if path is None:
        from mnemonic import Mnemonic
        WORDS = Mnemonic("english").wordlist
    else:
        WORDS = [w.strip() for w in path.read_text().splitlines() if w.strip()]
    INDEX = {w: i for i, w in enumerate(WORDS)}
    return WORDS


def bits_to_int(indices: list[int]) -> int:
    v = 0
    for i in indices:
        v = (v << 11) | i
    return v


def checksum_ok(prefix19: list[int], tail: list[int]) -> bool:
    """prefix19 = indices of the known leading words.
    tail = candidate indices for the hidden trailing words (1..5 of them)."""
    total_words = len(prefix19) + len(tail)
    total_bits = 11 * total_words
    v = bits_to_int(prefix19 + tail)
    ent_bits = total_bits - 8
    entropy = (v >> 8).to_bytes(ent_bits // 8, "big")
    return hashlib.sha256(entropy).digest()[0] == (v & 0xFF)


def phrase_from(prefix_words: list[str], tail_words: list[str]) -> str:
    return " ".join(prefix_words + tail_words)


def address_of(phrase: str) -> str:
    from eth_account import Account
    Account.enable_unaudited_hdwallet_features()
    return Account.from_mnemonic(phrase, account_path="m/44'/60'/0'/0/0").address


def search(prefix_words: list[str], k: int, limit: int | None = None,
           progress_every: float = 5.0,
           target_address: str | None = None) -> tuple[str | None, float, int]:
    """Brute-force the hidden tail words.

    NOTE: a checksum alone does NOT identify the phrase. For k hidden words there
    are 2^(11k-8) *different valid phrases* sharing the same known prefix, so a
    solver must match the derived address. Pass target_address to do that here;
    without it the first checksum-valid candidate is returned (useless for k>=2).
    """
    words = load_wordlist()
    prefix19 = [INDEX[w] for w in prefix_words]
    t0 = time.time()
    tried = 0
    valid = 0
    last = t0
    for combo in itertools.product(range(len(words)), repeat=k):
        tried += 1
        if checksum_ok(prefix19, list(combo)):
            valid += 1
            cand = phrase_from(prefix_words, [words[i] for i in combo])
            if target_address is None:
                return cand, time.time() - t0, tried
            if address_of(cand).lower() == target_address.lower():
                return cand, time.time() - t0, tried
        if limit and tried >= limit:
            print(f"  reached limit · {valid:,} checksum-valid candidates seen")
            return None, time.time() - t0, tried
        now = time.time()
        if now - last >= progress_every:
            rate = tried / (now - t0)
            print(f"  {tried:,} combinations · {valid:,} valid · {rate:,.0f}/s · {now-t0:.0f}s",
                  flush=True)
            last = now
    return None, time.time() - t0, tried


def print_tools(prefix_words: list[str], k: int) -> None:
    known = " ".join(prefix_words)
    print(f"""# hashcat (GPU build; mode 26600 = BIP39 / MetaMask HD wallet)
# hashcat masks cover small k only; btcrecover is the practical route for k>=4
hashcat -m 26600 -a 3 target.hash "<mask>"

# btcrecover (recommended for BIP39 known-words attacks)
#   pip install btcrecover
#   wallet.txt must hold the address derived from the target phrase
python btcrecover.py --wallet wallet.txt --bip39 \\
    --mnemonic-prefix "{known}" \\
    --mnemonic-length 24 --bip39-wordcount {k}""")


def self_test(k: int = 1) -> int:
    from mnemonic import Mnemonic
    mnemo = Mnemonic("english")
    secret = "0000000000000000000000000000000000000000000000000000000000000001"
    phrase = mnemo.to_mnemonic(bytes.fromhex(secret))
    words = phrase.split()
    prefix, tail_true = words[:24 - k], words[24 - k:]
    target = address_of(phrase)
    print(f"synthetic target: ...{ ' '.join(tail_true) } (hidden) · address {target}")
    found, secs, tried = search(prefix, k, progress_every=1.0, target_address=target)
    ok = found == phrase
    print(f"searched {tried:,} in {secs:.1f}s -> {'FOUND, phrase matches' if ok else 'MISS'}")
    if not ok and found:
        print("warning: a checksum-valid but WRONG phrase was returned (address mismatch)")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=None, help="number of hidden tail words")
    ap.add_argument("--prefix", help="19 known words (space separated). "
                                     "Default: read data/phrase_1001_redacted.txt")
    ap.add_argument("--address", help="target ETH address to match (default: from manifest)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tools", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--wordlist", default=None)
    args = ap.parse_args()

    if args.wordlist:
        load_wordlist(pathlib.Path(args.wordlist))
    else:
        load_wordlist()

    if args.self_test:
        return self_test(args.k or 2)

    prefix_words = args.prefix.split() if args.prefix else None
    k = args.k
    if prefix_words is None:
        data = pathlib.Path(__file__).resolve().parent.parent / "data" / "phrase_1001_redacted.txt"
        line = next(ln for ln in data.read_text().splitlines()
                    if ln and not ln.startswith("#"))
        tokens = line.split()
        hidden = sum(1 for t in tokens if t.startswith("█"))
        prefix_words = [t for t in tokens if not t.startswith("█")]
        k = k or hidden
    if k is None:
        sys.exit("specify --k or use the repo's redacted file")

    if args.tools:
        print_tools(prefix_words, k)
        return 0

    bits = 11 * k - 8
    target_address = args.address
    if target_address is None:
        mpath = pathlib.Path(__file__).resolve().parent.parent / "data" / "manifest.json"
        if mpath.exists():
            import json
            man = json.loads(mpath.read_text())
            target_address = man["entries"][str(man["target_index"])]["eth_address"]
    print(f"known words: {len(prefix_words)}/24 · hidden: {k} · valid candidates: 2^{bits} = {2**bits:,}")
    print(f"target address: {target_address}")
    print(f"note: 2^{bits} valid phrases share this prefix — "
          "only the address identifies the right one")
    found, secs, tried = search(prefix_words, k, args.limit, target_address=target_address)
    if found:
        print(f"\nCANDIDATE FOUND after {tried:,} combinations in {secs:.1f}s:\n{found}")
        print("verify against the published address in data/manifest.json before claiming.")
    else:
        print(f"\nno candidate in {tried:,} combinations ({secs:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
