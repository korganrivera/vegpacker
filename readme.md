# VegPack — rectangle & hex packing for vegetable spacing

A small C utility that computes how to pack circular planting spaces (e.g., for cabbages, tomatoes, etc.) into the minimum-width rectangle given a fixed bed height.  
It evaluates three packing patterns — regular grid, flat-topped hex, and pointy-topped hex — for each crop (radius + count), picks the best packing width, then packs those resulting widths into larger shipping/bed rectangles of fixed width (`LARGE_RECT_WIDTH`). Finally it reports how many large rectangles are required and the wasted space.

---

## Summary

- Language: C (ANSI/C compatible)
- Purpose: Given plant radii and counts, compute the minimum rectangle widths needed for three common 2D packings, then bin-pack those widths into fixed-size larger rectangles.
- Outputs:
  - Per-crop best packing type and width
  - Adjusted widths split into pieces ≤ `LARGE_RECT_WIDTH`
  - How many large rectangles used and total wasted space
  - A simple textual packing layout (widths per large rectangle)

The program intentionally targets garden/bed layout and small-scale packing problems rather than industrial-level optimizations.

---

## Build

Requires a standard C compiler (gcc/clang). No external dependencies.

```bash
gcc -O3 -std=c99 vegpack.c -o vegpack -lm
```

For debugging:

```bash
gcc -std=c99 -O0 -g -Wall -Wextra vegpack.c -o vegpack_dbg -lm
```

---

## Run

The program is self-contained: radii/counts are defined in `main()` as arrays. Build and run:

```bash
./vegpack
```

Sample console output (trimmed):

```
Best rectangle widths for each circle packing:

Radius: 4.50, Number of Circles: 25
flat-topped packing: width=36.000
...
Adjusted best widths for packing:
36.00 72.00 18.00 ...

Proceeding with rectangle packing...

Total large rectangles used: 5
Total wasted space: 32.00 (1.78%)
Packing details:
72.00 36.00
36.00 18.00
...
```

---

## What the program does (detailed)

1. **Per-crop packing calculation (`compute_min_width`)**
   - Inputs: circle `radius`, strip `height` (in same units), and `num_circles`.
   - Evaluates:
     - **Regular grid**: orthogonal rows & columns (`2r` spacing).
     - **Flat-topped hex**: rows offset like `o-o o-o` with vertical spacing `r * sqrt(3)`.
     - **Pointy-topped hex**: columns staggered with similar geometry.
   - For the hex styles the code computes how many rows/columns fit in the given `height` and increases `width` until capacity ≥ `num_circles`.
   - Returns the minimum width across the three patterns (and prints which packing was smallest).

2. **Split oversized widths (`adjust_best_widths`)**
   - Any best-width larger than `LARGE_RECT_WIDTH` is split into full `LARGE_RECT_WIDTH` pieces plus a smaller remainder.

3. **Pack the resulting strips into larger rectangles (`pack_rectangles`)**
   - A simple first-fit-decreasing style packing:
     - Sort descending.
     - Try to place the next strip into the first large rectangle with enough remaining space; otherwise start a new large rectangle.
   - Reports number of large rectangles used and total wasted space.

---

## Key constants (top of source)

Edit and recompile to change behavior:

```c
#define LARGE_RECT_WIDTH 360  // width of large rectangles (units consistent with radii/height)
#define HEIGHT 36             // height of each large rectangle (same units)
```

- All radii/counts in `main()` must use the same linear units. Radii are treated as *circle radii* (not diameters).
- The code assumes packing strips run along the width dimension; `HEIGHT` is the vertical dimension available for stacking rows/columns.

---

## Code notes & assumptions

- Radii are used directly; effective diameter is `2 * r`.
- Flat-topped hex vertical spacing uses `2 * r` for alternating rows (implementation approximates pattern via integer row counts).
- Pointy hex spacing calculation uses `sqrt(3) * r` approximations for inter-row/column offsets.
- The algorithm uses integer arithmetic for counting how many circles fit per row/column based on current trial width; widths are increased in discrete increments (usually `2*r` or `r*sqrt(3)` steps implicitly).
- `compute_min_width` currently iterates by growing width until capacity suffices — straightforward and robust for moderate numbers but not optimized for extreme scale.
- Binning into `LARGE_RECT_WIDTH` uses a greedy first-fit-decreasing approach; this is fast and often good, but not guaranteed optimal (bin-packing is NP-hard).

---

## When to tweak parameters

- **Change `HEIGHT`** to represent taller/shorter garden beds or bed-rows.
- **Change `LARGE_RECT_WIDTH`** to match shipping pallet width, bed roll length, or greenhouse bench width.
- If you need metric/imperial clarity, annotate radii/height units in `main()` (e.g., inches, feet, meters). The code makes no conversions.

---

## Accuracy & improvements (ideas)

If you want more realistic or more optimal packing, consider:
- Replacing the "grow width until capacity" approach with analytical formulas for number-per-width for each packing —