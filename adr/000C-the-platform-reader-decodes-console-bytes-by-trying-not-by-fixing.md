# 000C — The platform reader decodes console bytes by TRYING, not by fixing one encoding

> **UNNUMBERED.** `000` + `C` is a placeholder. ADR numbers are the Commander's; this file is
> renamed to its issued number in its own commit, so that a seal is never also a rename. The same
> convention was used for ADR 0047 at task B2's PHASE 0.

## Context

`src/harness/measurement_platform.py` is the **sealed reader for `frozen_parameters` row 9** — the
one frozen row that is *read from the machine rather than chosen*. It obtains several row 9 facts by
shelling out to PowerShell, among them the active power scheme, whose name is **localised** (`高性能`
on the row 9 platform).

`_powershell()` called `subprocess.run(..., text=True)` with **no `encoding=`**, so Python decoded
the child's bytes with the locale codepage — `cp936` here.

**The bug is that what the child emits depends on the PARENT process, and both were measured:**

| parent | bytes emitted by the nested PowerShell | decoded with cp936 |
|---|---|---|
| `bash` / `cmd` | **GBK** (`b'\xb5\xe7\xd4\xb4...'`) | correct — `高性能` |
| **PowerShell** | **UTF-8** (`b'\xe7\x94\xb5\xe6\xba\x90...'`) | **`UnicodeDecodeError`** |

Under a PowerShell parent the failure surfaced as `UnicodeDecodeError` inside `subprocess`, then
`AttributeError: 'NoneType' object has no attribute 'strip'` at `active_power_scheme()`. **Row 9
could not be read and G-3 could not be adjudicated from that parent at all.**

Found at task B2's PHASE 1, while reading row 9 for the v0.8 seal, and recorded as **DEVIATIONS
D-007** before any fix was attempted.

### This is the SECOND instance of the defect class, and the first was fixed a seal earlier

At the **v0.7** seal, `smoke/g10/spike.py` had the identical defect: `subprocess(..., text=True)`
with no `encoding=`, decoding subprocess output under cp936. There it threw `UnicodeDecodeError`
six times and **discarded all fourteen subgates' diagnostic output** — the verdict survived because
it rested on `returncode`, but a failing subgate would have had nowhere to state its case. It was
fixed with `encoding="utf-8", errors="replace"`, and `smoke/` being manifest-excluded, the fix cost
no reseal.

That the same class recurred, in a **covered** file, one seal later is the fact worth recording.
Both instances share a single root: **asking `subprocess` to guess a text encoding on Windows.**

## Decision

**`_powershell()` captures BYTES. A new `_decode_console()` tries each candidate encoding STRICTLY,
in order — `utf-8`, then `locale.getencoding()` — and takes the first that decodes cleanly. If none
does, it RAISES `PlatformError`.**

### Why not the obvious fix — `encoding="utf-8", errors="replace"`, as G-10 received

**Because it was measured, and it is wrong here.** Applied literally it repairs the PowerShell
parent and **silently corrupts the `bash` parent**, which is the shell every one of the seven G-3
runs and every row 9 read has actually used:

| decoding | `bash` parent | PowerShell parent |
|---|---|---|
| `text=True`, no encoding (the defect) | correct | **crash** |
| `encoding="utf-8", errors="replace"` | **silent U+FFFD garbage** | correct |
| **strict fallback chain (this ADR)** | **correct** | **correct** |

The two failures are not equivalent and must not be traded for one another. A crash is
**fail-closed**: it yields no row 9 rather than a wrong one. `errors="replace"` is **fail-open**: it
would write `������` into a sealed platform fact that no later reader could distinguish from a
machine genuinely named that. **In the code that reads the sealed measurement platform, the quiet
wrong answer is the worse failure** — which is the same reasoning `performance_cpus()` already
applies when it refuses to guess a P/E core mask, and the same reasoning ADR 0046 applied when it
refused to let an exhausted authorizer be reported as a denial.

G-10's `errors="replace"` remains correct **there**: it captures human-readable diagnostics, where a
mangled character costs legibility and nothing else. The difference is what the string is *for*.

### Why the order is `utf-8` first

GBK lead bytes for CJK (`0x81`–`0xFE` followed by `0x40`–`0xFE`) are rejected by a strict UTF-8
decode on the first character — `b'\xb5\xe7'` fails immediately — so UTF-8-first cannot mis-claim
GBK input. UTF-8 input, conversely, is accepted before the locale codepage is ever reached. The
ordering makes the common cases deterministic rather than probabilistic.

### Why it raises instead of replacing when nothing decodes

The module's opening docstring already fixes the rule: *"a mismatch between what the machine says
and what a human wrote down is **reported, not reconciled**."* A value it cannot read is refused, in
the same fail-closed style as `require_ac_power()` and `performance_cpus()`.

## Consequences

- **`src/harness/measurement_platform.py` is a COVERED file, so this forces a reseal.** It is
  applied at the v0.8 seal, together with the pre-existing drift in `campaign.py` and `runner.py`.
- **Row 9 is now parent-independent, and that is measured:** read under a `bash` parent and under a
  PowerShell parent, the two records are **byte-identical, 37 leaves, 0 differing**, with
  `power_scheme_name` = U+9AD8 U+6027 U+80FD and no replacement character under either.
- No row 9 value previously sealed is in doubt. The defect either produced the correct value or
  crashed; it never produced a wrong one. The seven G-3 medians and every prior row 9 read were
  taken through the `bash` path, which was always correct.
- `tests/test_environment_coherence.py` pins the contract five ways, including a **structural AST
  check that `_powershell` passes neither `text=` nor `encoding=` to `subprocess.run`**, and a test
  that pins the *rejected* alternative — that `errors="replace"` on locale bytes yields U+FFFD — so
  that nobody re-applies it believing it to be the smaller change.

## Status

Proposed — 2026-08-07, at task B2 STEP 2. Fixes DEVIATIONS **D-007**. Second instance of the
`subprocess`-guesses-the-encoding class; the first was `smoke/g10/spike.py`, fixed at the v0.7 seal.
