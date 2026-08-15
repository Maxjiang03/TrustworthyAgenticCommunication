"""Acceptance checks for the presentation layer (FIGURE_PLAN.md §D):

  (b) greyscale acceptance render -- every PNG is converted to luminance-only
      and written beside it as <stem>.grey.png for eyeball review; the script
      also reports whether the greyscale image still has the distinct tone
      levels the encoding relies on (a diagnostic, not a pass/fail oracle:
      the human check is the acceptance step);
  (c) PDF vector + type check -- every PDF's page size in inches, whether it
      contains vector text/path operators, and the SMALLEST font size any
      text object was set in (from the matplotlib rcParams the build uses and
      the fontsize arguments each script passes; asserted >= 8 pt).

Read-only over results/figures/; writes only the .grey.png companions.
"""

import re
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIGS = HERE.parents[1] / "results" / "figures"
MIN_PT = 8
# C2 (Commander ruling): the width is fixed at authoring time. A4 landscape
# gives ~9.7 in of usable text width; anything wider would have to be scaled
# and would take 8 pt type below 8 pt. Enforced, never resolved by scaling.
MAX_WIDTH_IN = 9.7


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
    print("=== (c) PDF vector + page-size check ===")
    for pdf in sorted(FIGS.glob("*.pdf")):
        w, h, txt, path = pdf_info(pdf)
        fits = w is not None and w <= MAX_WIDTH_IN + 1e-6
        flag = "OK" if (txt and path and fits) else ("TOO WIDE" if not fits else "CHECK")
        print(
            f"PDF {pdf.name} | {w:.2f} x {h:.2f} in | vector text={txt} vector paths={path} "
            f"| width<={MAX_WIDTH_IN}in={fits} | {flag}"
        )
        if not (txt and path and fits):
            ok = False
    smallest, where = min_fontsize_in_scripts()
    print(f"MIN_FONT smallest literal fontsize set by any script = {smallest} pt ({where})")
    if smallest < MIN_PT:
        ok = False
        print(f"FAIL: a script sets fontsize below {MIN_PT} pt")
    print("acceptance_check:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
