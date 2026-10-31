#!/usr/bin/env python3
"""Measure how fast THIS machine can try BIP39 candidates, then extrapolate.

The number you get is the only number that matters for the challenge: the
README table is a model, this is a measurement on your hardware.

Usage: python tools/measure_hashrate.py [--seconds 5] [--gpu-rate N]
"""
from __future__ import annotations

import argparse
import hashlib
import time


def entropy_checksum_pass(seconds: float) -> float:
    """Rate of the cheap stage: build 256-bit entropy candidates and reject by checksum."""
    n = 0
    t0 = time.time()
    base = b"\x00" * 32
    while time.time() - t0 < seconds:
        for i in range(4096):
            ent = hashlib.sha256(base + i.to_bytes(4, "big")).digest()
            # a candidate passes only if its final 8 checksum bits line up (1/256)
            if hashlib.sha256(ent).digest()[0] == ent[0]:
                n += 1
        n += 4096
    return n / (time.time() - t0)


def seed_rate(seconds: float) -> float:
    """Rate of the expensive stage: PBKDF2-HMAC-SHA512 / 2048 (BIP39 seed)."""
    phrase = b"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    n = 0
    t0 = time.time()
    while time.time() - t0 < seconds:
        for _ in range(4):
            hashlib.pbkdf2_hmac("sha512", phrase, b"mnemonic", 2048, 64)
        n += 4
    return n / (time.time() - t0)


def human(secs: float) -> str:
    if secs < 60:
        return f"{secs:.0f} s"
    if secs < 3600:
        return f"{secs/60:.1f} min"
    if secs < 86400:
        return f"{secs/3600:.1f} h"
    if secs < 3.15e7:
        return f"{secs/86400:.1f} days"
    return f"{secs/3.15e7:,.1f} years"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--gpu-rate", type=float, default=None,
                    help="known candidates/s from hashcat/btcrecover on a GPU")
    args = ap.parse_args()

    chk = entropy_checksum_pass(args.seconds)
    pdk = seed_rate(args.seconds)
    print(f"checksum stage : {chk:,.0f} candidates/s (this CPU)")
    print(f"PBKDF2 stage   : {pdk:,.1f} seeds/s (this CPU)")
    rate = args.gpu_rate or pdk
    label = "GPU (supplied)" if args.gpu_rate else "this CPU"
    print(f"\nextrapolated with {rate:,.0f} candidates/s ({label}):")
    for k in range(2, 7):
        bits = 11 * k - 8
        print(f"  k={k}: 2^{bits:<2} = {2**bits:>20,} candidates -> {human(2**bits / rate)}")


if __name__ == "__main__":
    main()
