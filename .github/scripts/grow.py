"""Make the 3D contribution bars rise from the floor in a wave, again and again.

github-profile-3d-contrib grows every bar at once, in three seconds, which
is easy to miss. This rewrites each bar's animation in the drawn SVG:

  * a wave: bars start one after another, first week to last;
  * taller bars take a little longer to rise;
  * each one overshoots slightly and settles, like it landed;
  * the city stands, sinks back to the floor in a ripple, and rises again.

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


HOLD = 2.6        # seconds the city stands complete
FALL, FALL_SWEEP = 0.7, 0.9      # each bar sinks in 0.7s, in a ripple 0.9s long
REST = 0.6        # a beat on the empty floor before it rises again
SPLINES_LOOP = ("0 0 1 1; 0.25 0.9 0.35 1; 0.45 0 0.55 1; 0 0 1 1; "
                "0.55 0 0.9 0.45; 0 0 1 1")


def grow(svg: str, loop: bool = True) -> str:
    tags = list(TAG.finditer(svg))
    # One bar = an animateTransform (its rise) and the height animations after it.
    bars, current = [], None
    for m in tags:
        kind, attrs = m.group(1), m.group(2)
        if 'attributeName="transform"' in attrs and kind == "animateTransform":
            vals = VALUES.search(attrs).group(1).split(";")
            x, y0 = _nums(vals[0])
            _, y1 = _nums(vals[-1])
            current = {"x": x, "rise": y0 - y1, "tags": [m]}
            bars.append(current)
        elif 'attributeName="height"' in attrs and current is not None:
            current["tags"].append(m)
    if not bars:
        return svg
    xs = [b["x"] for b in bars]
    lo, hi = min(xs), max(xs)
    tallest = max(b["rise"] for b in bars) or 1

    # One cycle for every bar, so the whole city rises and sinks together.
    risen = START + SWEEP + BASE_DUR + EXTRA_DUR
    cycle = risen + HOLD + FALL_SWEEP + FALL + REST

    edits = {}
    for b in bars:
        frac = (b["x"] - lo) / ((hi - lo) or 1)
        delay = START + SWEEP * frac
        dur = BASE_DUR + EXTRA_DUR * (b["rise"] / tallest)
        sink = risen + HOLD + FALL_SWEEP * frac
        total = cycle if loop else delay + dur
        times = [0, delay, delay + 0.72 * dur, delay + dur] + ([sink, sink + FALL, total] if loop else [])
        if not loop:
            times = [0, delay, delay + 0.72 * dur, total]
        keytimes = ";".join(f"{t_ / total:.4f}" for t_ in times)
        for m in b["tags"]:
            kind, attrs, close = m.groups()
            vals = VALUES.search(attrs).group(1).split(";")
            start, end = vals[0], vals[-1]
            if kind == "animateTransform":
                x, y0 = _nums(start)
                _, y1 = _nums(end)
                over = f"{_fmt(x)} {_fmt(y1 - OVERSHOOT * (y0 - y1))}"
            else:
                h0, h1 = float(start), float(end)
                over = _fmt(h1 + OVERSHOOT * (h1 - h0))
            seq = [start, start, over, end] + ([end, start, start] if loop else [])
            new_attrs = VALUES.sub(f'values="{";".join(seq)}"', attrs, count=1)
            new_attrs = re.sub(r'\s(dur|keyTimes|calcMode|keySplines|begin|fill|repeatCount)="[^"]*"', "", new_attrs)
            new_attrs += (f' dur="{total:.2f}s" keyTimes="{keytimes}" calcMode="spline" '
                          f'keySplines="{SPLINES_LOOP if loop else SPLINES}" begin="0s" '
                          + ('repeatCount="indefinite"' if loop else 'repeatCount="1" fill="freeze"'))
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
