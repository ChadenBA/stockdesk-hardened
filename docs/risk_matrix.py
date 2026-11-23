#!/usr/bin/env python3
"""Risk matrix generator - single source of truth: docs/risk-scores.csv.

Writes docs/risk-matrix.svg (three 5x5 likelihood x impact matrices: as found,
after the merge, after the admin actions), fills the generated tables in
docs/RISK-PRIORITISATION.md, and fails if a priority in the RISKS.md summary
does not match the band of its score. Python 3 standard library only.

    python3 docs/risk_matrix.py
"""
import csv
import html
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent

# Score bands (L x I, 1-25) -> level, priority, status colour (reserved
# status palette: critical / serious / warning / good) and in-fill ink.
BANDS = [
    (15, "Intolerable", "P0", "#d03b3b", "#ffffff"),
    (10, "High", "P1", "#ec835a", "#ffffff"),
    (5, "Low", "P2", "#fab219", "#0b0b0b"),
    (1, "Tolerable", "P3", "#0ca30c", "#ffffff"),
]
STATES = [
    ("L", "I", "As found", "inherent risk"),
    ("L_merge", "I_merge", "After this repository is merged", "code changes only"),
    ("L_admin", "I_admin", "After the admin actions", "rotation, RBAC, clean-up"),
]


def band(score):
    for floor, level, prio, fill, ink in BANDS:
        if score >= floor:
            return level, prio, fill, ink
    raise ValueError(score)


def load():
    with open(DOCS / "risk-scores.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("L", "I", "L_merge", "I_merge", "L_admin", "I_admin"):
            r[k] = int(r[k])
            assert 1 <= r[k] <= 5, f"{r['id']} {k} out of range"
    return rows


def esc(s):
    return html.escape(s, quote=True)


def svg(rows):
    cell, gap, top, left = 82, 2, 96, 74
    grid = 5 * cell
    panel_w = left + grid + 34
    width, height = panel_w * 3 + 8, top + grid + 118
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d" '
        'font-family="Inter, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">',
        '<title id="t">StockDesk risk matrix: likelihood x impact, as found, after the merge, after the admin actions</title>',
        '<desc id="d">Three 5 by 5 matrices. Each risk ID sits in the cell of its likelihood (rows, 1 to 5) '
        'and impact (columns, 1 to 5). Cell colour is the level of the score likelihood x impact: '
        'tolerable 1-4, low 5-9, high 10-14, intolerable 15-25. The same data is in docs/RISK-PRIORITISATION.md as tables.</desc>',
        "<style>",
        ".bg{fill:#fcfcfb}.ink{fill:#0b0b0b}.ink2{fill:#52514e}.muted{fill:#898781}",
        ".h{font-size:15px;font-weight:600}.sub{font-size:12px}.ax{font-size:11px}.id{font-size:11px;font-weight:600}.sc{font-size:10px}",
        "@media (prefers-color-scheme: dark){.bg{fill:#1a1a19}.ink{fill:#f0efec}.ink2{fill:#c3c2b7}}",
        "</style>",
        f'<rect class="bg" width="{width}" height="{height}" rx="8"/>',
    ]
    for p, (lk, ik, title, subtitle) in enumerate(STATES):
        x0 = p * panel_w + 8
        counts = {}
        for r in rows:
            prio = band(r[lk] * r[ik])[1]
            counts[prio] = counts.get(prio, 0) + 1
        tally = "  ·  ".join(f"{pr}: {counts.get(pr, 0)}" for pr in ("P0", "P1", "P2", "P3"))
        out.append(f'<text class="ink h" x="{x0 + left}" y="26">{p + 1}. {esc(title)}</text>')
        out.append(f'<text class="ink2 sub" x="{x0 + left}" y="44">{esc(subtitle)}</text>')
        out.append(f'<text class="ink2 sub" x="{x0 + left}" y="62">{esc(tally)}</text>')
        for li in range(5, 0, -1):          # likelihood: 5 at the top
            for ii in range(1, 6):          # impact: 1 on the left
                cx = x0 + left + (ii - 1) * cell
                cy = top + (5 - li) * cell
                score = li * ii
                level, prio, fill, ink = band(score)
                ids = [r["id"] for r in rows if r[lk] == li and r[ik] == ii]
                tip = f"L{li} x I{ii} = {score} ({level}, {prio})"
                if ids:
                    tip += ": " + "; ".join(f'{r["id"]} {r["risk"]}' for r in rows if r["id"] in ids)
                opacity = "1" if ids else "0.18"
                out.append(f"<g><title>{esc(tip)}</title>")
                out.append(f'<rect x="{cx + gap / 2}" y="{cy + gap / 2}" width="{cell - gap}" '
                           f'height="{cell - gap}" rx="4" fill="{fill}" fill-opacity="{opacity}"/>')
                sc_cls = "" if ids else "muted "
                sc_fill = f' fill="{ink}"' if ids else ""
                out.append(f'<text class="{sc_cls}sc" x="{cx + 7}" y="{cy + 14}"{sc_fill}>{score}</text>')
                for n, start in enumerate(range(0, len(ids), 3)):
                    line = " ".join(ids[start:start + 3])
                    out.append(f'<text class="id" x="{cx + cell / 2}" y="{cy + 36 + n * 14}" '
                               f'text-anchor="middle" fill="{ink}">{esc(line)}</text>')
                out.append("</g>")
        # axes
        for li in range(1, 6):
            out.append(f'<text class="muted ax" x="{x0 + left - 8}" y="{top + (5 - li) * cell + cell / 2 + 4}" '
                       f'text-anchor="end">{li}</text>')
        for ii in range(1, 6):
            out.append(f'<text class="muted ax" x="{x0 + left + (ii - 1) * cell + cell / 2}" '
                       f'y="{top + grid + 16}" text-anchor="middle">{ii}</text>')
        out.append(f'<text class="ink2 ax" x="{x0 + left + grid / 2}" y="{top + grid + 36}" '
                   'text-anchor="middle">Impact (1 negligible - 5 critical) →</text>')
        ymid = top + grid / 2
        out.append(f'<text class="ink2 ax" x="{x0 + 30}" y="{ymid}" text-anchor="middle" '
                   f'transform="rotate(-90 {x0 + 30} {ymid})">Likelihood (1 rare - 5 near certain) →</text>')
    # legend: colour + name + range + priority, never colour alone
    lx, ly = 8 + left, top + grid + 66
    for n, (floor, level, prio, fill, _ink) in enumerate(BANDS):
        rng = {15: "15-25", 10: "10-14", 5: "5-9", 1: "1-4"}[floor]
        x = lx + n * 300
        out.append(f'<rect x="{x}" y="{ly}" width="14" height="14" rx="3" fill="{fill}"/>')
        out.append(f'<text class="ink sub" x="{x + 22}" y="{ly + 11}">{level} {rng} = {prio}</text>')
    out.append(f'<text class="muted sc" x="{lx}" y="{ly + 36}">Faded cell = no risk there. '
               'Generated by docs/risk_matrix.py from docs/risk-scores.csv.</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def tables(rows):
    lines = ["| ID | Risk | L | I | Score | Level | Why this likelihood | Why this impact |",
             "|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (-r["L"] * r["I"], -r["I"], int(r["id"][1:]))):
        s = r["L"] * r["I"]
        level, prio, *_ = band(s)
        lines.append(f'| {r["id"]} | {r["risk"]} | {r["L"]} | {r["I"]} | **{s}** | {level} ({prio}) '
                     f'| {r["why_likelihood"]} | {r["why_impact"]} |')
    lines += ["", "**Residual risk** (same scale, re-scored after each set of actions):", "",
              "| ID | As found | After merge | After admin actions | What is left, and who |",
              "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: int(r["id"][1:])):
        cells = []
        for lk, ik, *_ in STATES:
            s = r[lk] * r[ik]
            cells.append(f"{s} {band(s)[1]}")
        lines.append(f'| {r["id"]} | {cells[0]} | {cells[1]} | {cells[2]} | {r["left_to"]} |')
    return "\n".join(lines)


def check_risks_md(rows):
    text = (ROOT / "RISKS.md").read_text(encoding="utf-8")
    declared = dict(re.findall(r"^\| (R\d+) \| (P\d) \|", text, flags=re.M))
    errors = []
    for r in rows:
        expected = band(r["L"] * r["I"])[1]
        if declared.get(r["id"]) != expected:
            errors.append(f'{r["id"]}: RISKS.md says {declared.get(r["id"])}, score says {expected}')
    return errors


def main():
    rows = load()
    (DOCS / "risk-matrix.svg").write_text(svg(rows), encoding="utf-8")
    doc = DOCS / "RISK-PRIORITISATION.md"
    text = doc.read_text(encoding="utf-8")
    block = "<!-- generated:start -->\n" + tables(rows) + "\n<!-- generated:end -->"
    new, n = re.subn(r"<!-- generated:start -->.*?<!-- generated:end -->",
                     lambda _m: block, text, flags=re.S)
    if n != 1:
        print("generated markers not found in RISK-PRIORITISATION.md", file=sys.stderr)
        return 1
    doc.write_text(new, encoding="utf-8")
    errors = check_risks_md(rows)
    for e in errors:
        print("MISMATCH", e, file=sys.stderr)
    print(f"{len(rows)} risks; svg + tables written; RISKS.md priorities consistent: {not errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
