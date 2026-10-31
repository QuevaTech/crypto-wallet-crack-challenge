#!/usr/bin/env python3
"""Generate offline (service-free) flat badges in the repo's palette."""
import pathlib

BG = "#16141a"
EDGE = "#2a2730"
FG = "#f2ead9"
GOLD = "#c8a63f"
EMBER = "#d87e37"
MUTED = "#8d867a"

BADGES = [
    ("candidates", "candidates", "2^47", EMBER),
    ("known-words", "known words", "19/24", GOLD),
    ("nist", "NIST SP 800-90B", "15/15 PASS", GOLD),
    ("prize", "prize", "1 USD", GOLD),
]

CH_W = 6.1  # approx mono advance at 10px


def badge(label: str, value: str, accent: str) -> str:
    lw = round(len(label) * CH_W + 18)
    vw = round(len(value) * CH_W + 18)
    w = lw + vw
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="24" role="img" aria-label="{label}: {value}">
  <rect width="{w}" height="24" rx="3" fill="{BG}"/>
  <rect x="0.5" y="0.5" width="{w-1}" height="23" rx="3" fill="none" stroke="{EDGE}"/>
  <text x="9" y="16" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10"
        letter-spacing="0.10em" fill="{MUTED}">{label.upper()}</text>
  <text x="{lw}" y="16" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10"
        letter-spacing="0.06em" fill="{accent}">{value}</text>
</svg>
'''


def main() -> None:
    out = pathlib.Path(__file__).resolve().parent.parent / "assets"
    out.mkdir(parents=True, exist_ok=True)
    for name, label, value, accent in BADGES:
        path = out / f"badge-{name}.svg"
        path.write_text(badge(label, value, accent))
        print(path.name, path.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
