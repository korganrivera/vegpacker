#!/usr/bin/env python3
"""
garden_scale_pack_flexsplit.py

Same solver as before but allows unlimited splitting into 360" full chunks + one remainder
(per-crop), subject to the practical cap that a crop cannot be split into more pieces than NUM_ROWS.
Uses exact packing (DFS / branch-and-bound) to test feasibility for each candidate multiplier x.
"""

from math import ceil, floor
import sys

# ------------- User-editable parameters -------------
NUM_ROWS = 12
ROW_LEN = 360                     # inches per row
BED_WIDTH = 36                    # inches (3 ft)
EPS = 1e-9                        # floating tolerance for binary search
MAX_ITERS = 60                    # binary search iterations
# ---------------------------------------------------

# per-person baseline list (name, count_per_person, spacing_in_inches, trellised_flag)
PER_PERSON = [
    ("asparagus", 25, 9, False),
    ("broccoli", 15, 18, False),
    ("bush green beans", 50, 6, False),
    ("cabbage", 10, 12, False),
    ("carrots", 120, 3, False),
    ("celery", 10, 6, False),
    ("corn, sweet", 100, 12, False),
    ("cucumbers", 4, 12, True),
    ("dried beans", 50, 6, True),
    ("garlic", 50, 4, False),
    ("green onions", 15, 3, False),
    ("kale", 40, 12, False),
    ("lettuce/other greens", 40, 12, False),
    ("onion bulbs", 50, 5, False),
    ("peppers", 7, 12, False),
    ("potatoes", 50, 12, False),
    #("shelling peas", 100, 3, True),
    ("snap peas", 40, 5, True),
    ("summer squash", 2, 12, False),
    ("sweet potatoes", 8, 12, False),
    ("tomatoes (>50% paste)", 12, 12, True),
    ("winter squash", 4, 12, False),
]

CAPACITY = NUM_ROWS * ROW_LEN


# ---------------- Utility functions ----------------

def compute_crop_total_length(count, spacing, trellised):
    """
    Given an integer count, spacing in inches, and trellised flag,
    return the total linear inches required along rows for this crop.
    """
    if trellised:
        return count * spacing
    cols = max(1, BED_WIDTH // spacing)
    rows_needed = ceil(count / cols)
    return rows_needed * spacing


def make_pieces_for_crop_flexible(total_length):
    """
    Convert a total_length (in inches) into pieces:
      - floor(total_length / ROW_LEN) full ROW_LEN chunks
      - plus one remainder if needed.
    Enforce that number_of_pieces <= NUM_ROWS (practical cap).
    Return list of piece lengths or None if impossible (too many pieces).
    """
    if total_length <= 0:
        return []
    full_chunks = int(total_length // ROW_LEN)
    rem = int(total_length % ROW_LEN)
    pieces = [ROW_LEN] * full_chunks
    if rem > 0:
        pieces.append(rem)
    # Practical safety: don't allow more pieces than rows (would be pointless)
    if len(pieces) > NUM_ROWS:
        return None
    return pieces


# Exact packing (DFS / backtracking)
def pack_pieces_exact(pieces, num_rows=NUM_ROWS, row_len=ROW_LEN):
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
def feasible_for_x(x, per_person_list=PER_PERSON):
    """
    Given multiplier x (float), compute scaled counts = ceil(orig * x),
    compute pieces (multiple full 360" chunks + remainder), check capacity and attempt exact packing.
    """
    scaled_counts = {}
    pieces = []  # (length,label)
    total_length = 0

    for name, per_count, spacing, trellised in per_person_list:
        sc = int(ceil(per_count * x))
        scaled_counts[name] = sc
        total_len = compute_crop_total_length(sc, spacing, trellised)
        piece_list = make_pieces_for_crop_flexible(total_len)
        if piece_list is None:
            return False, {"reason": f"Crop '{name}' would require {int(total_len/ROW_LEN + (1 if total_len%ROW_LEN else 0))} pieces which exceeds {NUM_ROWS} rows - infeasible at this x."}
        # label pieces
        if len(piece_list) == 1:
            pieces.append((int(piece_list[0]), name))
        else:
            for idx, L in enumerate(piece_list, start=1):
                pieces.append((int(L), f"{name}#{idx}"))
        total_length += total_len

    if total_length > CAPACITY:
        return False, {"reason": f"Total required length {total_length} in exceeds garden capacity {CAPACITY} in."}

    feasible, rows = pack_pieces_exact(pieces, NUM_ROWS, ROW_LEN)
    if not feasible:
        return False, {"reason": "No packing found for these pieces (exact search failed).", "pieces": pieces}
    waste = CAPACITY - total_length
    return True, {"scaled_counts": scaled_counts, "pieces": pieces, "rows": rows, "total_length": total_length, "waste": waste}


# ---------- Binary search for maximum x ----------
def find_max_x(per_person_list=PER_PERSON):
    lo = 0.0
    hi = 1.0
    f_hi, _ = feasible_for_x(hi, per_person_list)
    while f_hi:
        lo = hi
        hi *= 2.0
        if hi > 1e6:
            break
        f_hi, _ = feasible_for_x(hi, per_person_list)

    best_result = None

    for it in range(MAX_ITERS):
        mid = (lo + hi) / 2.0
        feasible, result = feasible_for_x(mid, per_person_list)
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
        for name, per_count, spacing, trellised in per_person_list:
            sc = explicit_counts[name]
            total_len = compute_crop_total_length(sc, spacing, trellised)
            piece_list = make_pieces_for_crop_flexible(total_len)
            if piece_list is None:
                return False, {"reason": f"Crop '{name}' requires too many pieces (> {NUM_ROWS})"}
            if len(piece_list) == 1:
                pieces.append((piece_list[0], name))
            else:
                for idx, L in enumerate(piece_list, start=1):
                    pieces.append((L, f"{name}#{idx}"))
            total_length += total_len
        if total_length > CAPACITY:
            return False, {"reason": "Total length exceeds capacity"}
        feasible, rows = pack_pieces_exact(pieces, NUM_ROWS, ROW_LEN)
        if not feasible:
            return False, {"reason": "No packing found for final integer counts."}
        return True, {"scaled_counts": explicit_counts, "pieces": pieces, "rows": rows, "total_length": total_length, "waste": CAPACITY - total_length}

    ok_final, final_result = feasible_for_counts(final_scaled)
    if not ok_final:
        # fallback to best_result found during search
        return lo, best_result
    return x_final, final_result


# ----------------- Run and output -------------------

def main():
    print("Garden scaling and packing solver (flexible splitting)")
    print(f"Rows: {NUM_ROWS}, Row length: {ROW_LEN} in, Capacity: {CAPACITY} in\n")
    x_final, result = find_max_x(PER_PERSON)
    if result is None:
        print("No feasible packing found (unexpected).")
        return

    print(f"Final multiplier x = {x_final:.12f}")
    print(f"Total used length = {result['total_length']} in of {CAPACITY} in; waste = {result['waste']} in\n")

    print("Scaled counts (per crop):")
    for name, per_count, spacing, trellised in PER_PERSON:
        sc = result['scaled_counts'][name]
        print(f" - {name:30s} -> {sc:4d} plants; spacing={spacing:3d} in; trellised={trellised}")

    print("\nPiece breakdown (crop pieces used):")
    for length, label in result['pieces']:
        print(f" - {label:30s} : {length} in")

    print("\nRow-by-row assignment:\n")
    rows = result['rows']
    for i, r in enumerate(rows, start=1):
        used = sum(length for (_label, length) in r)
        rem = ROW_LEN - used
        print(f"Row {i} : used {used} in, remaining {rem} in")
        for label, length in r:
            print(f"    {label} — {length} in")
        print()

    print("Done.")

if __name__ == "__main__":
    main()

