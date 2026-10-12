# Case study: locating a runtime anti-bot shield (de-identified)

> **Status**: static code analysis — no hooking, no packet capture, no runtime
> verification. Conclusions that cannot be proven from code alone are marked
> **[inferred]**.
> **De-identification**: the vendor, brand, domains, endpoints, keys, and
> identifiers from the engagement are not reproduced here. Field names and the
> signature structure are described structurally, not verbatim.

## The brief

A client with an automated purchasing client ("the bot") reported: *"our script
used to run daily, but the platform added a shield and now it fails; we need the
protocol re-engineered."*

Two deliverables arrived: a decompiled copy of the target Android app, and a
Python port of the bot. The task was to explain three things: how the old flow
worked, what the new shield changed, and **where the new shield actually is**.

## First surprise: the deliverables ran deeper than they looked

The "small script + one-page note" turned out to be:

1. A decompiled app with **~16,000 Java files** — the whole app laid bare.
2. A bot whose `data/` directory (three WebAssembly blobs) was **not** delivered.

I initially read the second point as "incomplete delivery", then realized the
missing files *were* the finding: the hardest-to-reverse part (the signature
WebAssembly) is exactly what was withheld.

## Round 1 — Map the bot

The bot was a classic three-stage service: scheduler → risk-control warmup →
burst of concurrent purchase requests. All the interesting logic sat in its
`crypto/` package, not in the request loop.

## Round 2 — Find the signing bridge

The purchase request carried three signing headers plus an encrypted body
parameter. They were produced by a JS-bridge handler in the app: the H5 page
called back into native, which returned a timestamp header, a signature header,
and a hard-coded info header, then encrypted the body. The signature header came
from a native library through a `mixK(timestamp, deviceId, version)` call.

Note the third argument: the app passed an **empty string** for `version`, while
the bot passed a pinned version string. This detail would later bite.

## Round 3 — The signature was already reversed: it was MD5

The delivered native-library notes showed the signature routine was standard
MD5 behind custom names. The legacy signature was, structurally:

```
sig = md5(sorted(concat(platform_tag, ts, device_id, version)) + r)[:26] + r
```

where `r` is a single character drawn from a ~37-symbol alphabet. Two
weaknesses jump out: the input is a plain sorted concatenation (no secret), and
the entire random space is ~37 values, so the signature is trivially verifiable.

The `version` discrepancy from Round 2 now mattered: the app computed the
signature with `version = ""`, the bot with `version = "<old version>"`.
Running both through the reference implementation produced **different
signatures for identical inputs** — a concrete demonstration that the bot's
signature had drifted out of step with the app.

## Round 4 — The encrypted body had two generations

The request body was encrypted into a single parameter. There were two
implementations:

- **Generation 1**: hard-coded AES-CBC with a fixed key/IV. The bot's source
  still contained these constants as **dead code** — it no longer used them.
- **Generation 2**: encryption through the runtime WebAssembly module.

**[inferred]** The vendor moved from a hard-coded AES key (too easy to extract —
the bot author had extracted it) to a WebAssembly black box.

## Round 5 — The device-risk SDK's true surface was much bigger

The shield's device-risk SDK was initialized once in the app. Its *public* API
exposed a handful of checks, but its *orchestration* class enumerated **~18
on-demand check types** — emulator, root, multi-open, HTTP/HTTPS/VPN proxy,
screen-sharing, virtual environment, Win11 emulator, accessibility services,
Magisk, microphone, call state, auto-click — bridged into a native library (the
real logic lived in the `.so`).

The bot's forged detection result covered **4 of those 18**. That gap alone
explains why the bot died once the checks were actually enforced.

## Round 6 — Oracle reuse, and its fragility

For the newer signature/encryption, the bot did **not** reverse the algorithm.
It ran the vendor's own WebAssembly as a black-box oracle: the blob called back
into JavaScript (`window.eval`, `Date.now`, …), and the bot answered those
callbacks with a fake WebView sandbox whose canvas/WebGL calls returned empty
values, patched with precomputed hashes.

This is the structural fragility a shield upgrade targets: bind the signature to
a real environment, and every oracle-reusing client breaks at once.

## Pivot — the shield was not in the APK

Grep across all ~16,000 decompiled files:

| Search | Hits |
|---|---|
| the purchase action endpoint | **0** (only the bot references it) |
| a sibling "resource list" endpoint | 1 (native-side metadata endpoint) |
| WebAssembly module names / loader names | **0** in business code |
| `wasm` (case-insensitive) | a few, all third-party library false positives |

Meanwhile the bot's updater plainly fetched the shield JS, the WebAssembly
module, and a "signature" blob from a CDN, versioned by a dated shield tag.

**Conclusion: the real signing lives in runtime-downloaded WebAssembly on the
CDN, not in the APK.** The native layer keeps only the legacy signature and the
device-risk SDK. "Adding a shield" is therefore just a CDN asset rotation — no
new APK required — which is also why the bot shipped with an auto-updater.

## Result

- **The old flow**: native bridge → three signing headers + encrypted body →
  risk warmup → concurrent purchase requests.
- **Where the shield is**: split between a native layer (legacy signature +
  device-risk SDK, logic in `.so`) and a runtime layer (shield JS + WebAssembly
  signature/encryption, served from CDN).
- **What the upgrade changed** [evidence-backed]: the encrypted body moved from
  hard-coded AES to WebAssembly; shield assets became versioned runtime
  downloads; the encryption scheme became switchable.
- **Why the bot broke** [inferred, three non-exclusive mechanisms]: (A) the
  WebAssembly export/interface changed; (B) the header/body field structure
  changed; (C) the risk SDK added environment checks the fake WebView failed.

## Honest boundaries

1. The three WebAssembly blobs were not delivered — their internals were not,
   and cannot be, reversed from these artifacts.
2. No live packet capture: which body-encryption generation is actually used,
   and the exact `version` value, remain [inferred].
3. No before/after diff of the shield: the exact breaking mechanism is not
   pinned down.
4. This is a **static** analysis; nothing here was verified at runtime.

## Retrospective

Three real turning points:

1. Reading "missing files" as *information*, not *incompleteness*.
2. Using grep to falsify the assumption "the shield is in the APK".
3. Placing the bot's 4 fake fields next to the SDK's 18 checks.

One line for the field: **before reaching for the algorithm, grep for the things
that should exist but don't — the absence list is the strongest clue to which
layer the vendor hid the shield in.**
