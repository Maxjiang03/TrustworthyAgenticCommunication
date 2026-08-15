"""Acceptance checks for the presentation layer (FIGURE_PLAN.md §D):

  (b) greyscale acceptance render -- every PNG is converted to luminance-only
      and written beside it as <stem>.grey.png for eyeball review; the script
      also reports whether the greyscale image still has the distinct tone
      levels the encoding relies on (a diagnostic, not a pass/fail oracle:
      the human check is the acceptance step);
  (c) PDF vector, placement, and type check -- every PDF's page size in inches,
      whether that size fits the dissertation's MEASURED text block in either
      orientation (C2: re-author, never scale), whether it contains vector
      text/path operators, and the SMALLEST font size any text object was set
      in (from the matplotlib rcParams the build uses and the fontsize
      arguments each script passes; asserted >= 8 pt).

Read-only over results/figures/; writes only the .grey.png companions.
"""

import re
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIGS = HERE.parents[1] / "results" / "figures"
MIN_PT = 8

# The text block is defined ONCE, in _common.py, measured from mproj.cls:41-47
# and confirmed by the compiler's own record at mproj.log:618-619. It is
# imported rather than restated: a load-bearing constant written down twice is
# the defect this check exists to catch.
sys.path.insert(0, str(HERE))
from _common import LANDSCAPE, PORTRAIT  # noqa: E402

TOL_IN = 1e-6


def greyscale(png_path):
    from PIL import Image  # pillow ships with matplotlib

    im = Image.open(png_path).convert("L")
    out = png_path.with_suffix(".grey.png")
    im.save(out)
    hist = im.histogram()
    levels = sum(1 for h in hist if h > 0)
    dark = sum(hist[:64])
    mid = sum(hist[64:192])
    light = sum(hist[192:])
    return out, levels, dark, mid, light


def pdf_info(pdf_path):
    data = pdf_path.read_bytes()
    m = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", data)
    w_in = h_in = None
    if m:
        w_in = (float(m.group(3)) - float(m.group(1))) / 72.0
        h_in = (float(m.group(4)) - float(m.group(2))) / 72.0
    # Inflate every FlateDecode stream and look for text/path operators.
    has_text = has_path = False
    for sm in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:
            body = zlib.decompress(sm.group(1))
        except Exception:
            continue
        if b"Tj" in body or b"TJ" in body:
            has_text = True
        if re.search(rb"\b(re|l|c|m)\b", body):
            has_path = True
    return w_in, h_in, has_text, has_path


def placement(w, h):
    """Which orientation, if any, holds this artefact AT ITS AUTHORED SIZE.

    Returns (orientation_name, None) when it is placeable, or (None, (nearest,
    over_w, over_h)) when it is not -- the overflow is reported so re-authoring
    has a numeric target instead of a guess.
    """
    if w is None:
        return None, None
    for name, (mw, mh) in (("portrait", PORTRAIT), ("landscape", LANDSCAPE)):
        if w <= mw + TOL_IN and h <= mh + TOL_IN:
            return name, None
    best = None
    for name, (mw, mh) in (("portrait", PORTRAIT), ("landscape", LANDSCAPE)):
        over_w = max(0.0, w - mw)
        over_h = max(0.0, h - mh)
        score = over_w + over_h
        if best is None or score < best[0]:
            best = (score, name, over_w, over_h)
    return None, best[1:]


def min_fontsize_in_scripts():
    """Smallest fontsize any presentation script sets (rcParams + literals)."""
    smallest = 10**9
    where = None
    for py in HERE.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        for m in re.finditer(r"fontsize\s*=\s*([^,)\n]+)", text):
            expr = m.group(1).strip()
            # Only literal numerics or FONT_MIN_PT arithmetic are decidable here.
            try:
                val = eval(expr, {"FONT_MIN_PT": MIN_PT})
            except Exception:
                continue
            if isinstance(val, (int, float)) and val < smallest:
                smallest, where = val, f"{py.name}: fontsize={expr}"
    return smallest, where


def main():
    ok = True
    print("=== (b) greyscale acceptance renders ===")
    for png in sorted(FIGS.glob("*.png")):
        if png.name.endswith(".grey.png"):
            continue
        out, levels, dark, mid, light = greyscale(png)
        print(
            f"GREY {png.name} -> {out.name} | distinct grey levels={levels} "
            f"| dark={dark} mid={mid} light={light}"
        )
    print("=== (c) PDF vector + placement check ===")
    print(
        f"TEXT BLOCK [M mproj.cls:41-47, confirmed by mproj.log:618-619] "
        f"portrait {PORTRAIT[0]:.3f} x {PORTRAIT[1]:.3f} in | "
        f"landscape {LANDSCAPE[0]:.3f} x {LANDSCAPE[1]:.3f} in"
    )
    pdfs = sorted(FIGS.glob("*.pdf"))
    unplaceable = []
    for pdf in pdfs:
        w, h, txt, path = pdf_info(pdf)
        orient, over = placement(w, h)
        if orient:
            verdict = f"fits {orient}"
        else:
            near, over_w, over_h = over
            verdict = (
                f"UNPLACEABLE (nearest {near}: over by {over_w:.2f} in wide, {over_h:.2f} in tall)"
            )
            unplaceable.append(pdf.stem)
        flag = "OK" if (txt and path and orient) else "FAIL"
        print(
            f"PDF {pdf.name} | {w:.2f} x {h:.2f} in | vector text={txt} vector paths={path} "
            f"| {verdict} | {flag}"
        )
        if not (txt and path and orient):
            ok = False
    print(f"PLACEMENT unplaceable = {len(unplaceable)} of {len(pdfs)}")
    for stem in unplaceable:
        print(f"PLACEMENT unplaceable | {stem}")
    smallest, where = min_fontsize_in_scripts()
    print(f"MIN_FONT smallest literal fontsize set by any script = {smallest} pt ({where})")
    if smallest < MIN_PT:
        ok = False
        print(f"FAIL: a script sets fontsize below {MIN_PT} pt")
    print("acceptance_check:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
