# Submissions

A winning solution is an on-chain sweep. Nothing has to be submitted for the prize.

This directory is for the *record*: if you recovered phrase #1001, open a PR that adds
`submissions/<github-handle>.md` with:

```markdown
# <github-handle>

- Phrase found: <date UTC>
- Method: (btcrecover / hashcat / custom; algorithm and any pruning)
- Hardware: (GPU model x count, driver, tool version)
- Measured rate: <candidates/s>
- Wall clock: <hours>
- Sweep tx: <explorer link>
```

Claims without an on-chain sweep transaction are listed as unverified. Claims that do not
reproduce (method + rate + time must be consistent with the address) are rejected.

Do not paste the recovered phrase into this repository. The sweep transaction is the proof.
