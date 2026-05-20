#!/usr/bin/env python3
"""
scale_garden.py

Same solver as before but allows unlimited splitting into 360" full chunks + one remainder
(per-crop), subject to the practical cap that a crop cannot be split into more pieces than the row count.
Uses exact packing (DFS / branch-and-bound) to test feasibility for each candidate multiplier x.
"""

import argparse
import csv
from math import ceil
import os

# ------------- User-editable parameters -------------
DEFAULT_ROWS = 15
DEFAULT_ROW_LEN = 360             # inches per row
DEFAULT_BED_WIDTH = 36            # inches (3 ft)
DEFAULT_PLANTS_CSV = "plants.csv"
OUTPUT_LAYOUT_CSV = "output/garden_scaled_layout.csv"
EPS = 1e-9                        # floating tolerance for binary search
MAX_ITERS = 60                    # binary search iterations
# ---------------------------------------------------


# ---------------- Utility functions ----------------

def load_plants_csv(path):
    crops = []

    with open(path, newline="") as file:
        reader = csv.DictReader(file)
        required = {"plant", "spacing_in", "planting_style"}
        missing = required - set(reader.fieldnames or [])
        count_field = next((name for name in (reader.fieldnames or []) if name.startswith("how_much_to_plant")), None)
        if count_field is None:
            missing.add("how_much_to_plant...")
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")

        for record in reader:
            name = record["plant"].strip()
            count = int(record[count_field])
            spacing = int(float(record["spacing_in"]))
            style = record["planting_style"].strip().lower()
            if style not in {"grid", "trellis"}:
                raise ValueError(f"{path}: invalid planting_style for {name!r}: {style!r}")
            crops.append((name, count, spacing, style == "trellis"))

    return crops

def compute_crop_total_length(count, spacing, trellised, bed_width):
    """
    Given an integer count, spacing in inches, and trellised flag,
    return the total linear inches required along rows for this crop.
    """
    if trellised:
        return count * spacing
    cols = max(1, bed_width // spacing)
    rows_needed = ceil(count / cols)
    return rows_needed * spacing


def make_pieces_for_crop_flexible(total_length, num_rows, row_len):
    """
    Convert a total_length (in inches) into pieces:
      - floor(total_length / row_len) full row_len chunks
      - plus one remainder if needed.
    Enforce that number_of_pieces <= num_rows (practical cap).
    Return list of piece lengths or None if impossible (too many pieces).
    """
    if total_length <= 0:
        return []
    full_chunks = int(total_length // row_len)
    rem = int(total_length % row_len)
    pieces = [row_len] * full_chunks
    if rem > 0:
        pieces.append(rem)
    # Practical safety: don't allow more pieces than rows (would be pointless)
    if len(pieces) > num_rows:
        return None
    return pieces


# Exact packing (DFS / backtracking)
def pack_pieces_exact(pieces, num_rows, row_len):
    """
    pieces: list of (length:int, label:str)
    Try to assign each piece to one of the rows (bins) of capacity row_len.
    Uses DFS with pruning and symmetry-breaking.
    Returns: (True, rows) if feasible, where rows is list of lists of (label, length).
             (False, None) otherwise.
    """
    pieces_sorted = sorted(pieces, key=lambda x: x[0], reverse=True)
    n = len(pieces_sorted)

    rows_used = [0] * num_rows
    rows_content = [[] for _ in range(num_rows)]

    seen_states = set()

    def dfs(index):
        if index >= n:
            return True
        length, label = pieces_sorted[index]
        rem_caps = tuple(sorted([row_len - u for u in rows_used], reverse=True))
        state_key = (index, rem_caps)
        if state_key in seen_states:
            return False

        candidate_rows = []
        for r in range(num_rows):
            rem = row_len - rows_used[r]
            if rem >= length:
                candidate_rows.append((rem - length, rem, r))
        candidate_rows.sort(key=lambda x: (x[0], -x[1]))

        for _, _, r in candidate_rows:
            # symmetry: only place into the first empty row when placing into an empty row
            if rows_used[r] == 0:
                first_empty = None
                for k in range(num_rows):
                    if rows_used[k] == 0:
                        first_empty = k
                        break
                if r != first_empty:
                    continue

            rows_used[r] += length
            rows_content[r].append((label, length))

            if rows_used[r] <= row_len:
                if dfs(index + 1):
                    return True

            rows_used[r] -= length
            rows_content[r].pop()

        seen_states.add(state_key)
        return False

    ok = dfs(0)
    if ok:
        return True, rows_content
    return False, None


# ---------- Feasibility tester for given x ----------
def feasible_for_x(x, per_person_list, num_rows, row_len, bed_width):
    """
    Given multiplier x (float), compute scaled counts = ceil(orig * x),
    compute pieces (multiple full 360" chunks + remainder), check capacity and attempt exact packing.
    """
    scaled_counts = {}
    pieces = []  # (length,label)
    total_length = 0
    capacity = num_rows * row_len

    for name, per_count, spacing, trellised in per_person_list:
        sc = int(ceil(per_count * x))
        scaled_counts[name] = sc
        total_len = compute_crop_total_length(sc, spacing, trellised, bed_width)
        piece_list = make_pieces_for_crop_flexible(total_len, num_rows, row_len)
        if piece_list is None:
            piece_count = int(total_len / row_len + (1 if total_len % row_len else 0))
            return False, {"reason": f"Crop '{name}' would require {piece_count} pieces which exceeds {num_rows} rows - infeasible at this x."}
        # label pieces
        if len(piece_list) == 1:
            pieces.append((int(piece_list[0]), name))
        else:
            for idx, L in enumerate(piece_list, start=1):
                pieces.append((int(L), f"{name}#{idx}"))
        total_length += total_len

    if total_length > capacity:
        return False, {"reason": f"Total required length {total_length} in exceeds garden capacity {capacity} in."}

    feasible, rows = pack_pieces_exact(pieces, num_rows, row_len)
    if not feasible:
        return False, {"reason": "No packing found for these pieces (exact search failed).", "pieces": pieces}
    waste = capacity - total_length
    return True, {"scaled_counts": scaled_counts, "pieces": pieces, "rows": rows, "total_length": total_length, "waste": waste}


# ---------- Binary search for maximum x ----------
def find_max_x(per_person_list, num_rows, row_len, bed_width):
    lo = 0.0
    hi = 1.0
    f_hi, _ = feasible_for_x(hi, per_person_list, num_rows, row_len, bed_width)
    while f_hi:
        lo = hi
        hi *= 2.0
        if hi > 1e6:
            break
        f_hi, _ = feasible_for_x(hi, per_person_list, num_rows, row_len, bed_width)

    best_result = None

    for it in range(MAX_ITERS):
        mid = (lo + hi) / 2.0
        feasible, result = feasible_for_x(mid, per_person_list, num_rows, row_len, bed_width)
        if feasible:
            lo = mid
            best_result = result
        else:
            hi = mid
        if hi - lo < EPS:
            break

    # refine final integer vector and compute exact maximum x allowed by those ceilings
    final_scaled = {name: int(ceil(cnt * lo)) for name, cnt, _, _ in per_person_list}
    upper_bounds = []
    for name, orig_cnt, _, _ in per_person_list:
        k = final_scaled[name]
        if orig_cnt > 0:
            upper_bounds.append(k / orig_cnt)
    x_final = min(upper_bounds) if upper_bounds else lo

    # recompute result for exact integer vector
    def feasible_for_counts(explicit_counts):
        pieces = []
        total_length = 0
        capacity = num_rows * row_len
        for name, per_count, spacing, trellised in per_person_list:
            sc = explicit_counts[name]
            total_len = compute_crop_total_length(sc, spacing, trellised, bed_width)
            piece_list = make_pieces_for_crop_flexible(total_len, num_rows, row_len)
            if piece_list is None:
                return False, {"reason": f"Crop '{name}' requires too many pieces (> {num_rows})"}
            if len(piece_list) == 1:
                pieces.append((piece_list[0], name))
            else:
                for idx, L in enumerate(piece_list, start=1):
                    pieces.append((L, f"{name}#{idx}"))
            total_length += total_len
        if total_length > capacity:
            return False, {"reason": "Total length exceeds capacity"}
        feasible, rows = pack_pieces_exact(pieces, num_rows, row_len)
        if not feasible:
            return False, {"reason": "No packing found for final integer counts."}
        return True, {"scaled_counts": explicit_counts, "pieces": pieces, "rows": rows, "total_length": total_length, "waste": capacity - total_length}

    ok_final, final_result = feasible_for_counts(final_scaled)
    if not ok_final:
        # fallback to best_result found during search
        return lo, best_result
    return x_final, final_result


# ----------------- Run and output -------------------

def write_layout_csv(path, rows):
    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["row", "segment_label", "length_in", "crop"])
        for row_number, row in enumerate(rows, start=1):
            for label, length in row:
                crop = label.rsplit("#", 1)[0] if "#" in label else label
                writer.writerow([row_number, label, length, crop])


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scale plant counts proportionally and pack them into a fixed number of garden rows."
    )
    parser.add_argument("csv_path", nargs="?", default=DEFAULT_PLANTS_CSV, help="Input plants CSV.")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS, help=f"Number of rows to fit. Default: {DEFAULT_ROWS}.")
    parser.add_argument("--row-len", type=int, default=DEFAULT_ROW_LEN, help=f"Length of each row in inches. Default: {DEFAULT_ROW_LEN}.")
    parser.add_argument("--bed-width", type=int, default=DEFAULT_BED_WIDTH, help=f"Bed width in inches. Default: {DEFAULT_BED_WIDTH}.")
    parser.add_argument("--output", default=OUTPUT_LAYOUT_CSV, help=f"Output layout CSV. Default: {OUTPUT_LAYOUT_CSV}.")
    return parser.parse_args()


def main():
    args = parse_args()
    capacity = args.rows * args.row_len
    per_person_list = load_plants_csv(args.csv_path)

    print("Garden scaling and packing solver (flexible splitting)")
    print(f"Input CSV: {args.csv_path}")
    print(f"Rows: {args.rows}, Row length: {args.row_len} in, Capacity: {capacity} in\n")
    x_final, result = find_max_x(per_person_list, args.rows, args.row_len, args.bed_width)
    if result is None:
        print("No feasible packing found (unexpected).")
        return

    print(f"Final multiplier x = {x_final:.12f}")
    print(f"Total used length = {result['total_length']} in of {capacity} in; waste = {result['waste']} in\n")

    print("Scaled counts (per crop):")
    for name, per_count, spacing, trellised in per_person_list:
        sc = result['scaled_counts'][name]
        print(f" - {name:30s} -> {sc:4d} plants; spacing={spacing:3d} in; trellised={trellised}")

    print("\nPiece breakdown (crop pieces used):")
    for length, label in result['pieces']:
        print(f" - {label:30s} : {length} in")

    print("\nRow-by-row assignment:\n")
    rows = result['rows']
    write_layout_csv(args.output, rows)
    for i, r in enumerate(rows, start=1):
        used = sum(length for (_label, length) in r)
        rem = args.row_len - used
        print(f"Row {i} : used {used} in, remaining {rem} in")
        for label, length in r:
            print(f"    {label} — {length} in")
        print()

    print(f"Wrote {args.output}")
    print("Done.")

if __name__ == "__main__":
    main()
