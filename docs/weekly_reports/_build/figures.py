"""Charts for the weekly reports, built only from committed files in reports/stage0/.

Run from repo root: python docs/weekly_reports/_build/figures.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
STAGE0 = ROOT / "reports" / "stage0"
W3 = ROOT / "docs" / "weekly_reports" / "week03_data_pipeline"

# reference palette (dataviz skill, light mode)
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#ffffff"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK, "axes.titlecolor": INK, "axes.titlesize": 12,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def _clean(ax, grid_axis="x"):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def _title(fig, text):
    fig.suptitle(text, x=0.01, y=0.98, ha="left", fontsize=12, fontweight="bold", color=INK)


def _fmt(n):
    return f"{n/1e6:.2f}M" if n >= 1e6 else f"{n/1e3:.0f}k" if n >= 1e3 else f"{n:,}"


def _hbar(ax, labels, values, color=BLUE, notes=None):
    y = range(len(labels))[::-1]
    ax.barh(list(y), values, color=color, height=0.62, edgecolor=SURFACE, linewidth=2)
    ax.set_yticks(list(y), labels)
    for yi, v, i in zip(y, values, range(len(values))):
        txt = _fmt(v) + (f"  {notes[i]}" if notes else "")
        ax.text(v, yi, "  " + txt, va="center", ha="left", color=INK2, fontsize=9)
    ax.set_xlim(0, max(values) * 1.35)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: _fmt(x) if x else "0"))
    _clean(ax)


def family_counts():
    fam = pd.read_csv(STAGE0 / "family_l1_counts.csv").sort_values("pairs", ascending=False)
    top = fam.head(8)
    other = fam.iloc[8:]
    n_cls = int((other.family_l1 != "Multiple").sum())
    labels = top.family_l1.tolist() + [f"Other ({n_cls} classes + 'Multiple')"]
    pairs = top.pairs.tolist() + [int(other.pairs.sum())]
    prots = top.proteins.tolist() + [int(other.proteins.sum())]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    _hbar(ax, labels, pairs, notes=[f"· {p:,} proteins" for p in prots])
    _title(fig, "Drug–protein pairs by protein family (level 1)")
    ax.set_xlabel("compound–protein pairs with ≥1 measurement")
    fig.text(0.01, 0.01, "ChEMBL 37, human single-protein targets. Source: reports/stage0/family_l1_counts.csv",
             color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.93)); fig.savefig(W3 / "W3_03_family_counts.png", dpi=150); plt.close(fig)


def data_sources():
    s = pd.read_csv(STAGE0 / "d4_sources.csv").sort_values("rows", ascending=False)
    names = {7: "PubChem BioAssay", 1: "Scientific literature", 37: "BindingDB patents",
             16: "GSK kinase set (PKIS)", 15: "DrugMatrix", 38: "SureChEMBL patents"}
    top = s[s.act_src_id.isin(names)].copy()
    rest = s[~s.act_src_id.isin(names)]
    labels = [names[i] for i in top.act_src_id] + [f"Other ({len(rest)} sources)"]
    rows = top.rows.tolist() + [int(rest.rows.sum())]
    miss = (top.missing_doc_year / top.rows).tolist() + [rest.missing_doc_year.sum() / rest.rows.sum()]
    notes = ["· no publication year" if m > 0.99 else ("· year partly missing" if m > 0.05 else "") for m in miss]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    _hbar(ax, labels, rows, notes=notes)
    _title(fig, "Where the 8.3M activity records come from")
    ax.set_xlabel("activity rows")
    fig.text(0.01, 0.01, "Records with no year cannot be used in a time-based (temporal) split. Source: reports/stage0/d4_sources.csv",
             color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.93)); fig.savefig(W3 / "W3_04_data_sources.png", dpi=150); plt.close(fig)


def overlap():
    o = pd.read_csv(STAGE0 / "d3_overlap.csv").set_index("comparison")
    naive = int(o.loc["A_naive_all_vs_all", "pairs_both"])
    indep = int(o.loc["C_independent_vs_independent", "pairs_both"])
    fig, ax = plt.subplots(figsize=(8, 3.2))
    _hbar(ax, ["Naive: all records vs all records", "Independent: each DB minus\nrecords copied from the other"],
          [naive, indep])
    _title(fig, f"ChEMBL ∩ BindingDB shared pairs: the naive count is ~{naive/indep:.0f}× inflated")
    ax.set_xlabel("drug–protein pairs found in both databases (InChIKey × UniProt)")
    fig.text(0.01, 0.01, "52% of BindingDB human rows are copied from ChEMBL; ChEMBL imports BindingDB patent data. Source: reports/stage0/d3_overlap.csv",
             color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 0.92)); fig.savefig(W3 / "W3_05_overlap_naive_vs_independent.png", dpi=150); plt.close(fig)


def confounding():
    c = pd.read_csv(STAGE0 / "pchembl_source_confounding.csv")
    c = c[(c.pchembl_n >= 50_000) & ~c.family_l2.str.contains("no L2")].sort_values("shift_when_excluding_pubchem")
    y = range(len(c))
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for yi, (_, r) in zip(y, c.iterrows()):
        ax.plot([r.median_all, r.median_excl_pubchem], [yi, yi], color=GRID, linewidth=3, zorder=1)
    ax.scatter(c.median_all, list(y), s=70, color=ORANGE, zorder=2, label="All sources", edgecolor=SURFACE, linewidth=2)
    ax.scatter(c.median_excl_pubchem, list(y), s=70, color=BLUE, zorder=3, label="Excluding PubChem screens",
               edgecolor=SURFACE, linewidth=2, marker="D")
    labels = [f"{f}  ({s:.0%} PubChem)" for f, s in zip(c.family_l2, c.pubchem_share)]
    ax.set_yticks(list(y), labels)
    for yi, (_, r) in zip(y, c.iterrows()):
        if r.shift_when_excluding_pubchem >= 0.5:
            ax.text(r.median_excl_pubchem + 0.08, yi, f"+{r.shift_when_excluding_pubchem:.1f}", va="center",
                    color=INK2, fontsize=9)
    ax.axvline(6, color=INK2, linestyle="--", linewidth=0.8)
    ax.text(6.03, -0.9, "pChEMBL 6 = 1 µM", color=INK2, fontsize=8)
    ax.set_ylim(-1.2, len(c) - 0.5)
    ax.set_xlabel("median pChEMBL (higher = more potent)")
    _title(fig, "Screening data drags some families' measured potency down")
    fig.legend(loc="upper left", bbox_to_anchor=(0.005, 0.935), ncol=2, frameon=False, fontsize=9)
    _clean(ax)
    fig.text(0.01, 0.01, "Families with ≥50k pChEMBL values. A per-family threshold must control for data source. Source: reports/stage0/pchembl_source_confounding.csv",
             color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.93)); fig.savefig(W3 / "W3_06_pubchem_confounding.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    W3.mkdir(parents=True, exist_ok=True)
    family_counts(); data_sources(); overlap(); confounding()
    print("charts written to", W3)
