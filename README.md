# shield-recon

Field notes and a small toolkit for **locating and classifying anti-bot shields in hybrid mobile apps**.

This repository distills one real reverse-engineering engagement into two reusable things:

1. **A playbook** ([`docs/playbook.md`](docs/playbook.md)) — transferable techniques for answering *where* a mobile app hides its anti-bot logic, and *what* it checks.
2. **A case study** ([`docs/case-study.md`](docs/case-study.md)) — a fully de-identified walkthrough of how those techniques were applied against a real (unnamed) app and its broken bot clone.

The target is deliberately anonymized: no vendor, brand, domain, endpoint, key, or identifier from the engagement is reproduced here. See **De-identification** below.

## What's inside

- `shieldrecon/primitives.py` — the one genuinely reusable tool extracted from the work: helpers to confirm whether an unknown native crypto routine is actually a standard hash, *before* you waste days reversing it by hand.
- `shieldrecon/cli.py` — `shieldrecon identify <hex>` and `shieldrecon guess <hex>`.

## Why this matters

The single most common time-sink in app RE is re-deriving something that is a standard primitive in disguise. In the case study, the signature routine was plain **MD5** behind custom names (`aesInit` / `aesTransform` / `gaes`). The tool below automates the exact check that caught it.

## Quick start

```bash
pip install -e .

# Is this extracted constant a known hash initialization vector?
shieldrecon identify 0123456789abcdeffedcba9876543210

# What hash produced this 64-hex-char digest?
shieldrecon guess 6a09e667bb67ae853c6ef372a54ff53a510e527f9b05688c1f83d9ab5be0cd19
```

Requires Python 3.9+. Standard library only.

## Methodology (the short version)

1. **Absence is a signal.** Grep the decompiled app for what a shield *should* contain (`wasm`, the signature module name, the protected endpoint). Zero hits in business code means the shield is shipped at runtime, not compiled in.
2. **Split native vs. runtime.** In a hybrid app, the real signing / device-risk often lives in a runtime-downloaded WebAssembly blob on a CDN, while the APK keeps only the legacy signature and the risk SDK.
3. **Confirm standard primitives first.** Before reversing unknown crypto, diff its constants against MD5/SHA-1/SHA-256/SHA-384/SHA-512 IVs and the AES S-box.
4. **Enumerate the risk surface.** A device-risk SDK's true breadth is visible in its orchestrator class (an enum of on-demand checks + a method-name map). Compare it against what the bot actually fakes.
5. **Version drift is a tell.** A bot that pins an old app version while the app moves on is a smoking gun for "the shield changed and the bot didn't keep up".

The full playbook is in [`docs/playbook.md`](docs/playbook.md).

## Honest boundaries

- This repo contains **no working bot, no decompiled app code, and no replayable values**. It is methodology + one small utility + a de-identified case study.
- The case study is a **static, read-the-code analysis** — no hooking, no packet capture, no runtime verification. Conclusions that cannot be proven from code alone are marked *[inferred]*.
- The tool identifies **hash primitives only** (MD5/SHA constants and digest lengths). It does not reverse cryptography.

## De-identification

The engagement target is not named. The following were generalized or removed:

- Vendor / brand / organization names → "the vendor", "a commercial device-risk SDK".
- Domains, endpoint paths, and app-specific header/field names → structural descriptions.
- Hard-coded keys, info values, and version/build tags → omitted.
- The legacy signature is described structurally (sorted concatenation + one random symbol), not verbatim.

## Layout

```
shield-recon/
├── README.md
├── LICENSE
├── pyproject.toml
├── shieldrecon/
│   ├── __init__.py
│   ├── primitives.py
│   └── cli.py
├── tests/
│   └── test_primitives.py
└── docs/
    ├── playbook.md
    └── case-study.md
```

## License

MIT
