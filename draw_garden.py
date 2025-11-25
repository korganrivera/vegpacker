# draw_garden.py
import matplotlib
matplotlib.use('Agg')   # non-interactive backend
import matplotlib.pyplot as plt

rows = [
    [("sweetcorn#1", 360)],
    [("sweetcorn#2", 360)],
    [("dried beans#1", 360)],
    [("shelling peas#1", 360)],
    [("broccoli", 342), ("green onions", 6), ("bush green beans (B2)", 12)],
    [("snap peas", 290), ("onion bulbs", 55), ("bush green beans (B1)", 15)],
    [("potatoes", 288), ("dried beans#2", 72)],
    [("sweetcorn#3", 264), ("cucumbers", 84), ("bush green beans (B3)", 12)],
    [("tomatoes", 216), ("asparagus", 144)],
    [("kale", 240), ("cabbage", 108), ("bush green beans (B4)", 12)],
    [("lettuce", 240), ("garlic", 56), ("sweet potatoes", 60)],
    [("bush green beans (A)", 75), ("carrots", 75), ("shelling peas#2", 72),
     ("peppers", 48), ("winter squash", 36), ("celery", 30), ("summer squash", 24)],
]

fig, ax = plt.subplots(figsize=(14,9))
y_positions = list(range(len(rows), 0, -1))
height = 0.8

for y, row in zip(y_positions, rows):
    x = 0
    for label, length in row:
        ax.barh(y, length, left=x, height=height)  # default colors used
        cx = x + length/2
        if length >= 30:
            ax.text(cx, y, f"{label}\n{length} in", ha='center', va='center', fontsize=7)
        else:
            ax.text(cx, y+0.25, f"{label} ({length} in)", ha='center', va='bottom', fontsize=6)
        x += length

ax.set_xlim(0, 360)
ax.set_ylim(0.5, len(rows)+0.5)
ax.set_yticks(y_positions)
ax.set_yticklabels([f"Row {i}" for i in range(1,13)][::-1])
ax.set_xlabel("Length along row (inches)")
ax.set_title("Garden layout — 12 rows (each 360 in long)")
ax.grid(axis='x', linestyle=':', linewidth=0.4)
plt.tight_layout()
plt.savefig("garden_rows.png", dpi=150, bbox_inches='tight')
print("Saved garden_rows.png")

