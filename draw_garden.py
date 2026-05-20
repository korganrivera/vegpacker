#!/usr/bin/env python3
import csv
import os
import sys
from collections import defaultdict

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROW_LEN = 360
DEFAULT_INPUT = "output/garden_scaled_layout.csv"
DEFAULT_OUTPUT = "output/garden_scaled_rows.png"

PALETTE = [
    "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
    "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
    "#393B79", "#637939", "#8C6D31", "#843C39", "#7B4173",
    "#3182BD", "#E6550D", "#31A354", "#756BB1", "#636363",
    "#6BAED6", "#FDAE6B", "#74C476", "#9E9AC8", "#969696",
    "#9ECAE1", "#FDBF6F", "#A1D99B", "#BCBDDC", "#BDBDBD",
]


def load_rows(path):
    grouped = defaultdict(list)

    with open(path, newline="") as file:
        reader = csv.DictReader(file)
        required = {"row", "segment_label", "length_in"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")

        for record in reader:
            row = int(record["row"])
            label = record["segment_label"]
            length = float(record["length_in"])
            crop = record.get("crop", label)
            grouped[row].append((label, length, crop))

    return [grouped[row] for row in sorted(grouped)]


def build_color_map(rows):
    totals = defaultdict(float)
    for row in rows:
        for _label, length, crop in row:
            totals[crop] += length

    crops = sorted(totals, key=lambda crop: (-totals[crop], crop))
    color_map = {}
    for index, crop in enumerate(crops):
        color_map[crop] = PALETTE[index % len(PALETTE)]
    return color_map


def draw(rows, output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    fig_height = max(6, len(rows) * 0.42)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    y_positions = list(range(len(rows), 0, -1))
    height = 0.8
    color_map = build_color_map(rows)

    for y, row in zip(y_positions, rows):
        x = 0
        for label, length, crop in row:
            ax.barh(y, length, left=x, height=height, color=color_map[crop], edgecolor="white", linewidth=0.8)
            cx = x + length / 2
            if length >= 45:
                ax.text(cx, y, f"{label}\n{length:g} in", ha="center", va="center", fontsize=7)
            elif length >= 20:
                ax.text(cx, y, f"{label}\n{length:g}", ha="center", va="center", fontsize=6)
            else:
                ax.text(cx, y + 0.25, f"{label} ({length:g})", ha="center", va="bottom", fontsize=6)
            x += length

    ax.set_xlim(0, ROW_LEN)
    ax.set_ylim(0.5, len(rows) + 0.5)
    ax.set_yticks(y_positions)
    ax.set_yticklabels([f"Row {i}" for i in range(1, len(rows) + 1)][::-1])
    ax.set_xlabel("Length along row (inches)")
    ax.set_title(f"Garden layout - {len(rows)} rows ({ROW_LEN} in each)")
    ax.grid(axis="x", linestyle=":", linewidth=0.4)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    output_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT

    rows = load_rows(input_path)
    draw(rows, output_path)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
