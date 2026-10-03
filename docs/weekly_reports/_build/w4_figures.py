"""Week 4 data-driven charts: label counts and split distributions, from the Network 1 manifest.

Run from repo root (after build_network1): python docs/weekly_reports/_build/w4_figures.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "reports" / "week2" / "network1_v1_manifest.json"
W4 = ROOT / "docs" / "weekly_reports" / "week04_network1"

BLUE, GREEN, BRICK, GREY = "#2a78d6", "#1a9850", "#d6604d", "#9aa0a6"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#ffffff"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK,
                     "axes.titlecolor": INK, "axes.titlesize": 12, "axes.titleweight": "bold",
                     "axes.titlelocation": "left", "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                     "savefig.facecolor": SURFACE})


def _clean(ax, axis="x"):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(axis=axis, color=GRID, linewidth=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)


def fmt(n):
    return f"{n/1e6:.2f}M" if n >= 1e6 else f"{n/1e3:.0f}k" if n >= 1e3 else str(n)


def main():
    W4.mkdir(parents=True, exist_ok=True)
    m = json.loads(MANIFEST.read_text())
    lc = m["label_counts"]

    # W4_03 label counts
    fig, ax = plt.subplots(figsize=(8, 2.6))
    labels = ["ACTIVE", "INACTIVE"]
    vals = [lc.get("ACTIVE", 0), lc.get("INACTIVE", 0)]
    colors = [GREEN, BRICK]
    y = [1, 0]
    ax.barh(y, vals, color=colors, height=0.6, edgecolor=SURFACE, linewidth=2)
    ax.set_yticks(y, labels)
    for yi, v in zip(y, vals):
        ax.text(v, yi, "  " + fmt(v) + f"  ({v:,})", va="center", ha="left", color=INK2, fontsize=10)
    ax.set_xlim(0, max(vals) * 1.3)
    ax.set_title(f"Network 1 labels — {fmt(m['rows'])} drug–protein pairs")
    ax.set_xlabel("labelled pairs")
    _clean(ax)
    fig.text(0.01, 0.02, f"{m['distinct_compounds']:,} compounds · {m['distinct_proteins']:,} proteins · "
             f"{m['distinct_scaffold_groups']:,} scaffold groups. Source: reports/week2/network1_v1_manifest.json",
             color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig(W4 / "W4_03_label_counts.png", dpi=150); plt.close(fig)

    # W4_05 split distributions (stacked train/calib/test per split)
    splits = ["split_random", "split_drugcold", "split_targetcold", "split_temporal"]
    names = ["Random", "Drug-cold", "Target-cold", "Temporal"]
    parts = ["train", "calib", "test"]
    pcolors = {"train": BLUE, "calib": "#f4a582", "test": GREEN}
    fig, ax = plt.subplots(figsize=(9, 3.4))
    import numpy as np
    y = np.arange(len(splits))[::-1]
    for i, sp in enumerate(splits):
        d = m["split_distributions"][sp]
        total = sum(v for k, v in d.items() if k in parts)
        left = 0
        for p in parts:
            v = d.get(p, 0)
            w = v / total * 100 if total else 0
            ax.barh(y[i], w, left=left, color=pcolors[p], height=0.62, edgecolor=SURFACE, linewidth=1.5)
            if w > 7:
                ax.text(left + w / 2, y[i], f"{p}\n{fmt(v)}", va="center", ha="center", color="#fff", fontsize=8.5, fontweight="bold")
            left += w
    ax.set_yticks(y, names)
    ax.set_xlim(0, 100); ax.set_xlabel("share of labelled pairs (%)")
    excl = m["split_distributions"]["split_temporal"].get("nan", 0) or m["split_distributions"]["split_temporal"].get("<NA>", 0)
    ax.set_title("The four splits: train / calibration / test")
    _clean(ax)
    fig.text(0.01, 0.02, "Each split holds out different pairs; calibration is carved from each split's own train. "
             "Temporal excludes undated pairs. Leakage check: " + ("PASSED" if m["leakage_check_passed"] else "FAILED"),
             color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig(W4 / "W4_05_split_distributions.png", dpi=150); plt.close(fig)
    print("wrote W4_03, W4_05 to", W4)


if __name__ == "__main__":
    main()
