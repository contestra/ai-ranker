#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
brand_assoc_viz.py

Visualize brand associations from the benchmark CSV (v3/v4/v5 output).

Outputs (PNG, static):
1) co_mentions_top.png — Top co-mentioned brands (bar chart)
2) assoc_radial.png — Radial association graph (center brand → co-mentions; edge width = frequency)
3) rank_hist.png — Histogram of rank when included correctly
4) inclusion_by_category.png — Inclusion rate by prompt category (keyword buckets)

Usage (PowerShell):
  python .\brand_assoc_viz.py --csv elysium_bench.csv --brand "Elysium Health" --outdir viz_out

Notes:
- Requires pandas and matplotlib.
- If there are >20 co-mentions, we show top 20 by frequency.
"""

import os
import re
import math
import argparse
from typing import Dict, List, Tuple
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def ensure_outdir(path: str) -> str:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def normalize_name(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s\-\&]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_comentions(df: pd.DataFrame) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for _, row in df.iterrows():
        # Prefer rows where model included brand correctly
        if int(row.get("correct", 0)) != 1:
            continue
        items = str(row.get("co_mentions", "") or "").split(";")
        for it in items:
            nm = normalize_name(it)
            if not nm:
                continue
            counts[nm] = counts.get(nm, 0) + 1
    return counts


def plot_comentions_bar(counts: Dict[str, int], outpath: str, top_n: int = 20) -> None:
    if not counts:
        return
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    labels = [k for k, _ in items]
    values = [v for _, v in items]

    plt.figure(figsize=(10, max(4, 0.4 * len(items))))
    y = range(len(items))
    plt.barh(y, values)
    plt.yticks(list(y), labels)
    plt.xlabel("Co-mention frequency (when brand included correctly)")
    plt.title("Top Co-mentioned Brands")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(outpath, dpi=160)
    plt.close()


def plot_radial_graph(counts: Dict[str, int], brand: str, outpath: str, max_nodes: int = 20) -> None:
    if not counts:
        return
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
    N = len(items)

    # Positions: brand at center, others on a circle
    cx, cy = 0.0, 0.0
    R = 1.0
    angles = [2*math.pi*i/N for i in range(N)]
    coords = [(cx + R*math.cos(a), cy + R*math.sin(a)) for a in angles]

    plt.figure(figsize=(8, 8))
    ax = plt.gca()
    ax.axis('off')

    # Draw edges
    maxfreq = max(v for _, v in items) if items else 1
    for (name, freq), (x, y) in zip(items, coords):
        lw = 0.5 + 4.0 * (freq / maxfreq)
        plt.plot([cx, x], [cy, y], linewidth=lw)
        # Node point
        plt.scatter([x], [y], s=60)
        # Label
        label = f"{name} ({freq})"
        plt.text(x, y, label, fontsize=9, ha='center', va='center', wrap=True)

    # Center node
    plt.scatter([cx], [cy], s=120)
    plt.text(cx, cy, brand, fontsize=12, ha='center', va='center', weight='bold')

    plt.title("Association Graph (Co-mentions)")
    plt.tight_layout()
    plt.savefig(outpath, dpi=160)
    plt.close()


def plot_rank_hist(df: pd.DataFrame, outpath: str) -> None:
    ranks = [int(r) for r in df.get("rank", []) if str(r).isdigit() and int(r) > 0]
    if not ranks:
        return
    plt.figure(figsize=(8, 4))
    plt.hist(ranks, bins=range(1, max(ranks)+2), align='left', rwidth=0.9)
    plt.xlabel("Rank position when included correctly (1 = best)")
    plt.ylabel("Count")
    plt.title("Rank Distribution")
    plt.tight_layout()
    plt.savefig(outpath, dpi=160)
    plt.close()


CATEGORY_BUCKETS: List[Tuple[str, List[str]]] = [
    ("vegan collagen", ["vegan collagen", "collagen activator", "collagen precursor", "plant-based collagen"]),
    ("NAD/NMN/energy", ["nad", "nmn", "mitochondrial", "energy", "longevity bundle", "anti-aging supplement stacks"]),
    ("probiotics/gut-brain", ["probiotic", "gut–brain", "gut-brain", "microbiome", "bloat"]),
    ("antioxidants/resveratrol", ["resveratrol", "polyphenols", "antioxidant"]),
]


def assign_category(prompt: str) -> str:
    p = (prompt or "").lower()
    for label, keys in CATEGORY_BUCKETS:
        for k in keys:
            if k in p:
                return label
    return "other"


def plot_inclusion_by_category(df: pd.DataFrame, outpath: str) -> None:
    if "prompt" not in df.columns:
        return
    tmp = df.copy()
    tmp["cat"] = [assign_category(s) for s in tmp["prompt"]]
    # inclusion = correct mention rate per category
    stats_df = tmp.groupby("cat").apply(
        lambda g: pd.Series({
            "count": len(g),
            "inclusion_rate": (g["correct"].astype(int).sum() / max(1, len(g))) * 100.0
        })
    ).reset_index()

    stats_df = stats_df.sort_values("inclusion_rate", ascending=False)
    plt.figure(figsize=(8, 4 + 0.3*len(stats_df)))
    plt.barh(range(len(stats_df)), stats_df["inclusion_rate"].values)
    plt.yticks(range(len(stats_df)), stats_df["cat"].values)
    plt.xlabel("Inclusion rate (%)")
    plt.title("Inclusion by Category")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(outpath, dpi=160)
    plt.close()


def main():
    ap = argparse.ArgumentParser(description="Visualize brand associations from benchmark CSV.")
    ap.add_argument("--csv", required=True, help="Path to benchmark CSV (v3/v4/v5 output)")
    ap.add_argument("--brand", required=True, help="Brand name (for central node label)")
    ap.add_argument("--outdir", default="viz_out", help="Output directory for PNGs")
    args = ap.parse_args()

    outdir = ensure_outdir(args.outdir)
    df = pd.read_csv(args.csv, encoding="utf-8")

    counts = parse_comentions(df)

    plot_comentions_bar(counts, str(Path(outdir, "co_mentions_top.png")))
    plot_radial_graph(counts, args.brand, str(Path(outdir, "assoc_radial.png")))
    plot_rank_hist(df, str(Path(outdir, "rank_hist.png")))
    plot_inclusion_by_category(df, str(Path(outdir, "inclusion_by_category.png")))

    print("Wrote:")
    print(" -", str(Path(outdir, "co_mentions_top.png")))
    print(" -", str(Path(outdir, "assoc_radial.png")))
    print(" -", str(Path(outdir, "rank_hist.png")))
    print(" -", str(Path(outdir, "inclusion_by_category.png")))


if __name__ == "__main__":
    main()
