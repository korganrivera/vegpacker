# save as garden_pack_13rows.py and run: python3 garden_pack_13rows.py
import math
from math import ceil
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except Exception:
    HAVE_MPL = False

ROW_LEN = 360
NUM_ROWS = 13
CAP = ROW_LEN * NUM_ROWS
x = 0.8764044943820225  # chosen uniform multiplier

# crops: (name, original_count, spacing_in_inches, trellised_flag)
crops = [
    ("asparagus", 77, 9, False),
    ("broccoli", 46, 18, False),
    ("bush green beans", 152, 6, False),
    ("cabbage", 31, 12, False),
    ("carrots", 363, 3, False),
    ("celery", 31, 6, False),
    ("sweetcorn", 302, 12, False),
    ("garlic", 152, 4, False),
    ("green onions", 27, 3, False),
    ("kale", 71, 12, False),
    ("lettuce", 71, 12, False),
    ("onion bulbs", 89, 5, False),
    ("peppers", 13, 12, False),
    ("potatoes", 89, 12, False),
    ("summer squash", 4, 12, False),
    ("sweet potatoes", 15, 12, False),
    ("winter squash", 8, 12, False),
    ("cucumbers", 8, 12, True),
    ("dried beans", 89, 6, True),
    ("shelling peas", 177, 3, True),
    ("snap peas", 71, 5, True),
    ("tomatoes", 22, 12, True),
]

# compute scaled counts and pieces
scaled = {}
per_crop_pieces = {}   # name -> list of piece lengths (in inches)
all_pieces = []        # (length, label, crop_name)

for name, orig, spacing, trellis in crops:
    sc = int(math.ceil(orig * x))
    scaled[name] = sc
    if trellis:
        length = sc * spacing
    else:
        cols = max(1, 36 // spacing)
        rows_needed = int(math.ceil(sc / cols))
        length = rows_needed * spacing
    # break length into full 360" chunks + remainder piece (if any)
    full = length // ROW_LEN
    rem = length % ROW_LEN
    pieces = []
    for i in range(int(full)):
        pieces.append(ROW_LEN)
    if rem > 0:
        pieces.append(rem)
    # label pieces
    if len(pieces) == 1:
        per_crop_pieces[name] = pieces
        all_pieces.append((pieces[0], name, name))
    else:
        per_crop_pieces[name] = pieces[:]
        for i, p in enumerate(pieces, start=1):
            label = f"{name}#{i}"
            all_pieces.append((p, label, name))

total_length = sum(p for p,_,_ in all_pieces)

# pack pieces into rows with Best-Fit-Decreasing (works well for this scale)
pieces_sorted = sorted(all_pieces, key=lambda t: t[0], reverse=True)

rows = [[] for _ in range(NUM_ROWS)]
rows_used = [0]*NUM_ROWS

for length, label, crop in pieces_sorted:
    # best-fit: place into the row that has smallest leftover after placing
    best_row = None
    best_remain = None
    for i in range(NUM_ROWS):
        rem = ROW_LEN - rows_used[i]
        if rem >= length:
            if best_remain is None or (rem - length) < best_remain:
                best_remain = rem - length
                best_row = i
    if best_row is None:
        # fallback (shouldn't happen if total_length <= CAP)
        best_row = max(range(NUM_ROWS), key=lambda i: ROW_LEN - rows_used[i])
    rows[best_row].append((label, length, crop))
    rows_used[best_row] += length

# Print the row-by-row output in the exact format you asked for
print(f"Multiplier x = {x}\nTotal capacity = {CAP} in; total used = {total_length} in; waste = {CAP - total_length} in\n")
for i in range(NUM_ROWS):
    print(f"Row {i+1}:\n")
    for seg_label, seg_len, crop in rows[i]:
        print(f"    {seg_label} — {seg_len} in")
    print()

# Save CSV for easy import/printing
try:
    import csv
    with open("garden_13rows.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row","segment_label","length_in","crop"])
        for i in range(NUM_ROWS):
            for seg_label, seg_len, crop in rows[i]:
                w.writerow([i+1, seg_label, seg_len, crop])
    print("Wrote garden_13rows.csv")
except Exception as e:
    print("Could not write CSV:", e)

# Optionally draw PNG if matplotlib is available
if HAVE_MPL:
    fig_h = 10
    fig_w = 14
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    y_positions = list(range(NUM_ROWS, 0, -1))
    height = 0.8
    for y, row in zip(y_positions, rows):
        x_pos = 0
        for seg_label, seg_len, crop in row:
            ax.barh(y, seg_len, left=x_pos, height=height)
            cx = x_pos + seg_len/2
            if seg_len >= 30:
                txt = f"{seg_label}\n{seg_len} in"
                ax.text(cx, y, txt, ha='center', va='center', fontsize=7)
            else:
                ax.text(cx, y+0.25, f"{seg_label} ({seg_len} in)", ha='center', va='bottom', fontsize=6)
            x_pos += seg_len
    ax.set_xlim(0, ROW_LEN)
    ax.set_ylim(0.5, NUM_ROWS + 0.5)
    ax.set_yticks(y_positions)
    ax.set_yticklabels([f"Row {i}" for i in range(1, NUM_ROWS+1)][::-1])
    ax.set_xlabel("Length along row (inches)")
    ax.set_title(f"Garden layout — {NUM_ROWS} rows × {ROW_LEN} in (x={x:.6f})")
    ax.grid(axis='x', linestyle=':', linewidth=0.4)
    plt.tight_layout()
    plt.savefig("garden_13rows.png", dpi=150, bbox_inches='tight')
    print("Wrote garden_13rows.png (if matplotlib installed)")
else:
    print("matplotlib not available; PNG not produced.")

