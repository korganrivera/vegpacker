#!/usr/bin/env python3
import csv
import os
import sys
from collections import defaultdict

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

ROW_LEN = 360
BED_WIDTH = 36
DEFAULT_INPUT = "output/garden_scaled_layout.csv"
DEFAULT_OUTPUT = "output/garden_scaled_rows.png"
DEFAULT_PLANTS = "plants.csv"
SMALL_LABEL_THRESHOLD = 45
NOTES_WIDTH = 130

PALETTE = [
    "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
    "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
    "#393B79", "#637939", "#8C6D31", "#843C39", "#7B4173",
    "#3182BD", "#E6550D", "#31A354", "#756BB1", "#636363",
    "#6BAED6", "#FDAE6B", "#74C476", "#9E9AC8", "#969696",
    "#9ECAE1", "#FDBF6F", "#A1D99B", "#BCBDDC", "#BDBDBD",
]

PLANT_ALPHA = 0.28
SEGMENT_ALPHA = 0.82


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


def load_plants(path):
    plants = {}

    with open(path, newline="") as file:
        reader = csv.DictReader(file)
        required = {"plant", "spacing_in", "planting_style"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")

        for record in reader:
            crop = record["plant"].strip()
            plants[crop] = {
                "spacing": float(record["spacing_in"]),
                "style": record["planting_style"].strip().lower(),
            }

    return plants


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


def text_color_for_fill(color):
    hex_color = color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "black" if luminance > 0.58 else "white"


def text_box_for_fill(color):
    text_color = text_color_for_fill(color)
    if text_color == "black":
        return text_color, {"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "none", "alpha": 0.78}
    return text_color, {"boxstyle": "round,pad=0.18", "facecolor": "black", "edgecolor": "none", "alpha": 0.52}


def draw_circles(ax, left, row_bottom, length, crop, plants, color):
    plant = plants.get(crop)
    if plant is None:
        return

    spacing = plant["spacing"]
    style = plant["style"]
    radius = spacing / 2

    if spacing <= 0:
        return

    if style == "trellis":
        y_positions = [row_bottom + BED_WIDTH / 2]
    else:
        count_across = max(1, int(BED_WIDTH // spacing))
        used_width = count_across * spacing
        y_start = row_bottom + (BED_WIDTH - used_width) / 2 + radius
        y_positions = [y_start + i * spacing for i in range(count_across)]

    x = left + radius
    while x <= left + length - radius + 0.001:
        for y in y_positions:
            ax.add_patch(Circle((x, y), radius, facecolor="white", alpha=PLANT_ALPHA, edgecolor="black", linewidth=0.18))
        x += spacing


def draw(rows, plants, output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    fig_height = max(6, len(rows) * 0.45)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    color_map = build_color_map(rows)

    for row_index, row in enumerate(rows):
        x = 0
        row_bottom = (len(rows) - row_index - 1) * BED_WIDTH
        row_center = row_bottom + BED_WIDTH / 2
        small_labels = []
        for label, length, crop in row:
            color = color_map[crop]
            ax.add_patch(Rectangle((x, row_bottom), length, BED_WIDTH, facecolor=color, alpha=SEGMENT_ALPHA, edgecolor="white", linewidth=0.9))
            draw_circles(ax, x, row_bottom, length, crop, plants, color)
            cx = x + length / 2
            text_color, bbox = text_box_for_fill(color)
            if length >= 60:
                ax.text(cx, row_center, f"{label}\n{length:g} in", ha="center", va="center", fontsize=7, color=text_color, bbox=bbox)
            elif length >= SMALL_LABEL_THRESHOLD:
                ax.text(cx, row_center, f"{label}\n{length:g}", ha="center", va="center", fontsize=6, color=text_color, bbox=bbox)
            else:
                small_labels.append(f"{label} {length:g}")
            x += length

        if small_labels:
            ax.text(
                ROW_LEN + 8,
                row_center,
                "; ".join(small_labels),
                ha="left",
                va="center",
                fontsize=6,
                color="black",
                bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "#dddddd", "alpha": 0.9},
            )

    ax.axvline(ROW_LEN, color="#444444", linewidth=0.8)
    ax.set_xlim(0, ROW_LEN + NOTES_WIDTH)
    ax.set_ylim(0, len(rows) * BED_WIDTH)
    y_ticks = [(len(rows) - i - 0.5) * BED_WIDTH for i in range(len(rows))]
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f"Row {i}" for i in range(1, len(rows) + 1)])
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Length along row (inches)")
    ax.set_title(f"Garden layout - {len(rows)} rows ({ROW_LEN} in each)")
    ax.grid(axis="x", linestyle=":", linewidth=0.4)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    output_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    plants_path = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_PLANTS

    rows = load_rows(input_path)
    plants = load_plants(plants_path)
    draw(rows, plants, output_path)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
