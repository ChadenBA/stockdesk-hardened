#!/usr/bin/env python3
"""Risk tables generator - single source of truth: docs/risk-scores.csv.

Fills the generated tables in docs/RISK-PRIORITISATION.md and RISKS.md
(summary by level: as found, after the merge, after the admin actions), and
fails if a priority in the RISKS.md summary does not match the band of its
score. Python 3 standard library only.

    python3 docs/risk_table.py
"""
import csv
import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent

# Score bands (likelihood x impact, 1-25) -> level, priority.
BANDS = [(15, "Intolerable", "P0", "15-25"), (10, "High", "P1", "10-14"),
         (5, "Low", "P2", "5-9"), (1, "Tolerable", "P3", "1-4")]
STATES = [("L", "I"), ("L_merge", "I_merge"), ("L_admin", "I_admin")]


def band(score):
    for floor, level, prio, _rng in BANDS:
        if score >= floor:
            return level, prio
    raise ValueError(score)


def load():
    with open(DOCS / "risk-scores.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("L", "I", "L_merge", "I_merge", "L_admin", "I_admin"):
            r[k] = int(r[k])
            assert 1 <= r[k] <= 5, f"{r['id']} {k} out of range"
    return rows


def summary(rows):
    """Which risks sit at each level, as found / after merge / after admin actions."""
    lines = ["| Level | Score | As found | After this repo is merged | After the admin actions |",
             "|---|---|---|---|---|"]
    for _floor, level, prio, rng in BANDS:
        cells = []
        for lk, ik in STATES:
            ids = [r["id"] for r in rows if band(r[lk] * r[ik])[1] == prio]
            cells.append(f"**{len(ids)}**: " + ", ".join(ids) if ids else "**0**")
        lines.append(f"| {level} ({prio}) | {rng} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def details(rows):
    lines = ["| ID | Risk | L | I | Score | Level | Why this likelihood | Why this impact |",
             "|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (-r["L"] * r["I"], -r["I"], int(r["id"][1:]))):
        s = r["L"] * r["I"]
        level, prio = band(s)
        lines.append(f'| {r["id"]} | {r["risk"]} | {r["L"]} | {r["I"]} | **{s}** | {level} ({prio}) '
                     f'| {r["why_likelihood"]} | {r["why_impact"]} |')
    lines += ["", "**Residual risk** (same scale, re-scored after each set of actions):", "",
              "| ID | As found | After merge | After admin actions | What is left, and who |",
              "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: int(r["id"][1:])):
        cells = [f"{r[lk] * r[ik]} {band(r[lk] * r[ik])[1]}" for lk, ik in STATES]
        lines.append(f'| {r["id"]} | {cells[0]} | {cells[1]} | {cells[2]} | {r["left_to"]} |')
    return "\n".join(lines)


def fill(path, name, content):
    text = path.read_text(encoding="utf-8")
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    new, n = re.subn(re.escape(start) + r".*?" + re.escape(end),
                     lambda _m: f"{start}\n{content}\n{end}", text, flags=re.S)
    if n != 1:
        raise SystemExit(f"markers '{name}' not found in {path.name}")
    path.write_text(new, encoding="utf-8")


def check_risks_md(rows):
    text = (ROOT / "RISKS.md").read_text(encoding="utf-8")
    declared = dict(re.findall(r"^\| (R\d+) \| (P\d) \|", text, flags=re.M))
    return [f'{r["id"]}: RISKS.md says {declared.get(r["id"])}, score says {band(r["L"] * r["I"])[1]}'
            for r in rows if declared.get(r["id"]) != band(r["L"] * r["I"])[1]]


def main():
    rows = load()
    table = summary(rows)
    fill(DOCS / "RISK-PRIORITISATION.md", "summary", table)
    fill(DOCS / "RISK-PRIORITISATION.md", "generated", details(rows))
    fill(ROOT / "RISKS.md", "summary", table)
    errors = check_risks_md(rows)
    for e in errors:
        print("MISMATCH", e, file=sys.stderr)
    print(f"{len(rows)} risks; tables written; RISKS.md priorities consistent: {not errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
