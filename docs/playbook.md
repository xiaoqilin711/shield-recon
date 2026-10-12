# Anti-bot shield reconnaissance: a field playbook

A reusable set of techniques for answering two questions about any mobile app
with an anti-bot shield:

1. **Where** does the shield actually live?
2. **What** is it, and what does it check?

These techniques were distilled from a real engagement (de-identified case study
in [`case-study.md`](case-study.md)) in which an automated client stopped working
after the vendor "added a shield". They apply to hybrid apps — a native shell
hosting H5/WebView pages — where most modern anti-bot logic ends up.

## Technique 1 — "Absence as a signal" (locate by grep)

Do **not** assume the shield is compiled into the app. Grep the decompiled app
for the things a shield *should* contain:

- the signature/encryption module names (`wasm`, `stub`, the loader, …)
- the endpoint paths of the protected action
- the anti-bot header names

Then read the hit list carefully:

- **Zero hits in business code** → the shield is shipped at runtime (CDN/H5),
  not compiled in. The absence *is* the answer.
- **Hits only in third-party libraries** → confirm they are false positives
  (e.g. an English identifier like `wasMeasured…` matching the
  case-insensitive string `wasm`). A naive "zero hits" claim is often wrong;
  always re-run and eyeball the actual matching lines.
- **The action endpoint absent, but a sibling "resource/metadata" endpoint
  present** → the resource list is native-side, the action is H5-side. That
  split is itself a strong structural clue.

## Technique 2 — Classify the shield into layers

A hybrid app's shield is rarely one thing. Draw the split:

| Layer | Physical location | Typical contents |
|---|---|---|
| Native | APK: dex + `.so` | legacy signature, device-risk SDK, native bridge |
| Runtime | CDN, downloaded at run time | shield JS + WebAssembly signature/encryption blobs |

Consequences:

- The vendor can "add a shield" by **rotating CDN assets only** — no new APK.
- A client that re-syncs those assets automatically stays current against
  *rotations* but breaks against *structural* changes (new exports, new fields,
  new environment checks).
- If the interesting WebAssembly blobs are **not** in your deliverables, treat
  the missing files as information: they are the part the vendor is protecting.

## Technique 3 — Confirm standard primitives before reversing

Custom-looking native crypto is very often a standard primitive in disguise.
Before re-implementing anything:

1. Extract the routine's constants (init vectors, round tables) from `.rodata`.
2. Diff them against MD5/SHA-1/SHA-256/SHA-384/SHA-512 IVs and the AES S-box.
3. Check the output size against common digest lengths.

The `shieldrecon` CLI in this repo automates exactly this:

```bash
shieldrecon identify 0123456789abcdeffedcba9876543210   # -> md5 (exact)
shieldrecon guess 6a09e667bb67ae853c6ef372a54ff53a510e527f9b05688c1f83d9ab5be0cd19
```

In the case study, a routine family named `aesInit` / `aesTransform` / `gaes`
turned out to be plain MD5 — a full day of reversing saved by a 10-second diff.

## Technique 4 — Enumerate the device-risk surface

A commercial device-risk SDK's true breadth is usually visible in its
*orchestration* class, not its public API:

- an enum of on-demand check types, and
- a mapping from each type to a `checkXxxStatus` method,
- often bridged into a native library (the real logic lives in the `.so`).

List every check type. Typical members: emulator, root, multi-open, HTTP/HTTPS/
VPN proxy, screen-sharing, virtual environment, Win11 emulator, accessibility
services, Magisk, microphone, call state, auto-click.

Then compare that list against what any automated client actually fakes. A
client that forges 4 fields out of 18 is the whole story of "why it broke".

## Technique 5 — Read the (broken) client to learn what the vendor added

A dead bot is a free diff against the current shield:

- **Version drift** — the client pins an old app version while the app moves
  on. The exact gap tells you *when* the shield changed.
- **Oracle reuse** — the client runs the vendor's own WebAssembly as a black-box
  oracle instead of reversing it. Its fragility (anti-emulation, environment
  binding) is precisely what a "shield upgrade" would target.
- **Fake coverage** — the client's forged environment fields reveal which
  checks existed when it was written; the vendor's current check list reveals
  what got added since.

## When each technique fails

- **Grep** misses string-obfuscated or dynamically-constructed identifiers —
  the shield still lives there, you just can't see it by name.
- **Layer classification** breaks if the vendor compiles the WASM *into* the
  APK (the "absence" signal disappears).
- **Primitive diffing** only catches *standard* primitives; a truly custom
  construction won't match any table.
- **Enumeration** relies on readable decompilation; fully-obfuscated SDKs hide
  the check list behind native calls.

## Anti-patterns

- Publishing a working bot or decompiled app code — that is not a portfolio, it
  is proprietary code plus an attack surface.
- Re-deriving by hand what a 10-second constant diff would have identified.
- Trusting a remembered grep result; re-run it and read the actual lines.
