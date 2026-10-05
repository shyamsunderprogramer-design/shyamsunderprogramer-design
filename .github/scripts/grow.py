"""Make the 3D contribution bars rise from the floor in a wave.

github-profile-3d-contrib grows every bar at once, in three seconds, which
is easy to miss. This rewrites each bar's animation in the drawn SVG:

  * a wave: bars start one after another, first week to last;
  * taller bars take a little longer to rise;
  * each one overshoots slightly and settles, like it landed.

A bar is held on the floor until its turn, inside one timeline from 0s, so
nothing shows at full height before it rises. Usage:
    python grow.py file.svg [file.svg ...]
"""

import re
import sys

START, SWEEP = 0.4, 3.2          # first bar starts at 0.4s, the last 3.2s later
BASE_DUR, EXTRA_DUR = 0.9, 0.9   # a short bar rises in 0.9s, the tallest in 1.8s
OVERSHOOT = 0.10                 # rises 10% past its height, then settles
SPLINES = "0 0 1 1; 0.25 0.9 0.35 1; 0.45 0 0.55 1"

TAG = re.compile(r'<(animateTransform|animate)\b([^>]*?)(/?)>')
VALUES = re.compile(r'values="([^"]*)"')


def _nums(text):
    return [float(v) for v in text.replace(";", " ").split()]


def _fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def grow(svg: str) -> str:
    tags = list(TAG.finditer(svg))
    # One bar = an animateTransform (its rise) and the height animations after it.
    bars, current = [], None
    for m in tags:
        kind, attrs = m.group(1), m.group(2)
        if 'attributeName="transform"' in attrs and kind == "animateTransform":
            x, y0, _, y1 = _nums(VALUES.search(attrs).group(1))
            current = {"x": x, "rise": y0 - y1, "tags": [m]}
            bars.append(current)
        elif 'attributeName="height"' in attrs and current is not None:
            current["tags"].append(m)
    if not bars:
        return svg
    xs = [b["x"] for b in bars]
    lo, hi = min(xs), max(xs)
    tallest = max(b["rise"] for b in bars) or 1

    edits = {}
    for b in bars:
        delay = START + SWEEP * ((b["x"] - lo) / ((hi - lo) or 1))
        dur = BASE_DUR + EXTRA_DUR * (b["rise"] / tallest)
        total = delay + dur
        keytimes = f"0;{delay / total:.4f};{(delay + 0.72 * dur) / total:.4f};1"
        for m in b["tags"]:
            kind, attrs, close = m.groups()
            values = VALUES.search(attrs).group(1)
            start, end = values.split(";")
            if kind == "animateTransform":
                x, y0 = _nums(start)
                _, y1 = _nums(end)
                over = f"{_fmt(x)} {_fmt(y1 - OVERSHOOT * (y0 - y1))}"
            else:
                h0, h1 = float(start), float(end)
                over = _fmt(h1 + OVERSHOOT * (h1 - h0))
            new_values = f"{start};{start};{over};{end}"
            new_attrs = VALUES.sub(f'values="{new_values}"', attrs, count=1)
            new_attrs = re.sub(r'\s(dur|keyTimes|calcMode|keySplines|begin|fill)="[^"]*"', "", new_attrs)
            new_attrs += (f' dur="{total:.2f}s" keyTimes="{keytimes}" calcMode="spline" '
                          f'keySplines="{SPLINES}" begin="0s" fill="freeze"')
            edits[m.start()] = (m.end(), f"<{kind}{new_attrs}{close}>")

    out, pos = [], 0
    for start in sorted(edits):
        end, text = edits[start]
        out.append(svg[pos:start])
        out.append(text)
        pos = end
    out.append(svg[pos:])
    return "".join(out)


if __name__ == "__main__":
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            svg = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(grow(svg))
        print(f"wave animation: {path}")
