// Fits vegetables into a rectangle in a grid pattern or one of two hex grid
// patterns. Say that the spacing of cabbages is 12 inches and I have 50
// cabbages to plant. I need to know the best way to plant them to use the
// least space. This program figures that out, given the radius needed by the
// cabbage and how many cabbages I have. Only, it does it for a whole bunch of
// vegetables, not just cabbages.


#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

#define LARGE_RECT_WIDTH 360 // The width of the larger rectangles
#define HEIGHT 36

// Comparison function for sorting in descending order
int compare_desc(const void *a, const void *b) {
    double diff = (*(double *)b - *(double *)a);
    if (diff > 0) return 1;
    if (diff < 0) return -1;
    return 0;
}

// Function to compute the minimum width needed for circle packing
void compute_min_width(double radius, int height, int num_circles, double *best_width) {
    double r = radius;
    double h = (double)height;
    int n = num_circles;
    
    // Flat-topped packing
    int rows_flat = (int)(h / (2 * r));
    int total_circles_flat = 0;
    double width_flat = 0; // Changed to double to avoid integer division issues
    while (total_circles_flat < n) {
        width_flat += 2 * r;
        total_circles_flat = 0;
        for (int i = 0; i < rows_flat; i++) {
            total_circles_flat += (i % 2 == 0) ? (int)(width_flat / (2 * r)) : (int)((width_flat - r) / (2 * r));
        }
    }
    
    // Pointy-topped packing
    int rows_pointy = (int)(h / (sqrt(3) * r));
    int columns_pointy = 1;
    int total_circles_pointy = 0;
    while (total_circles_pointy < n) {
        total_circles_pointy = 0;
        for (int i = 0; i < columns_pointy; i++) {
            total_circles_pointy += (i % 2 == 0) ? rows_pointy : (rows_pointy > 0 ? rows_pointy - 1 : 0);
        }
        columns_pointy++;
    }
    double width_pointy = (columns_pointy == 1) ? 2 * r : (2 * r + (columns_pointy - 2) * r * sqrt(3));

    // Regular grid packing
    int rows_regular = (int)(h / (2 * r));
    if (rows_regular < 1) rows_regular = 1; // Prevent division by zero
    int columns_regular = (n + rows_regular - 1) / rows_regular; // Ceiling division
    double width_regular = 2 * r * columns_regular;
    
    // Choose the minimum width
    *best_width = fmin(fmin(width_flat, width_pointy), width_regular);

    
    // Output results
    printf("\nRadius: %.2f, Number of Circles: %d\n", radius, num_circles);

    int smallest_width = 0;

    if (width_flat < width_pointy && width_flat < width_regular) {
        smallest_width = 1;
    } else if (width_pointy < width_flat && width_pointy < width_regular) {
        smallest_width = 2;
    }

    switch (smallest_width) {
        case 1:
            printf("flat-topped packing: width=%.3f\n", width_flat);
            break;
        case 2:
            printf("pointy-topped packing: width=%.3f\n", width_pointy);
            break;
        default:
            printf("regular packing: width=%.3f\n", width_regular);
            break;
    }
}

// Function to pack smaller rectangles into larger rectangles
void pack_rectangles(double *small_widths, int num_rectangles) {
    qsort(small_widths, num_rectangles, sizeof(double), compare_desc); // Sort widths descending
    
    double remaining_space[num_rectangles]; // Track remaining space in each large rectangle
    int large_rect_count = 0;
    double packed_rects[num_rectangles][num_rectangles]; // Store packing information
    int packed_counts[num_rectangles]; // Track count per large rectangle
    
    for (int i = 0; i < num_rectangles; i++) {
        packed_counts[i] = 0;
    }
    
    for (int i = 0; i < num_rectangles; i++) {
        int placed = 0;
        
        // Try to fit into an existing large rectangle
        for (int j = 0; j < large_rect_count; j++) {
            if (remaining_space[j] >= small_widths[i]) {
                remaining_space[j] -= small_widths[i];
                packed_rects[j][packed_counts[j]++] = small_widths[i];
                placed = 1;
                break;
            }
        }
        
        // If not placed, start a new large rectangle
        if (!placed) {
            remaining_space[large_rect_count] = LARGE_RECT_WIDTH - small_widths[i];
            packed_rects[large_rect_count][packed_counts[large_rect_count]++] = small_widths[i];
            large_rect_count++;
        }
    }
    
    // Calculate total wasted space
    double total_waste = 0;
    for (int i = 0; i < large_rect_count; i++) {
        total_waste += remaining_space[i];
    }
    
    // Print results
    printf("\nTotal large rectangles used: %d\n", large_rect_count);
    printf("Total wasted space: %.2f (%.2f%%)\n", total_waste, 100.0 * total_waste / (large_rect_count * LARGE_RECT_WIDTH));
    printf("\nPacking details:\n");
    for (int i = 0; i < large_rect_count; i++) {
        for (int j = 0; j < packed_counts[i]; j++) {
            printf("%.2f ", packed_rects[i][j]);
        }
        printf("\n");
    }
}

// Function to adjust best_widths array
void adjust_best_widths(double *best_widths, int *num_radii) {
    int new_num_radii = *num_radii;
    
    // Create a new array to hold adjusted widths
    double adjusted_widths[new_num_radii * 2]; // Maximum possible size
    int idx = 0;
    
    for (int i = 0; i < *num_radii; i++) {
        if (best_widths[i] > LARGE_RECT_WIDTH) {
            int parts = (int)(best_widths[i] / LARGE_RECT_WIDTH);
            double remainder = best_widths[i] - (parts * LARGE_RECT_WIDTH);
            for (int j = 0; j < parts; j++) {
                adjusted_widths[idx++] = LARGE_RECT_WIDTH;
            }
            if (remainder > 0) {
                adjusted_widths[idx++] = remainder;
            }
        } else {
            adjusted_widths[idx++] = best_widths[i];
        }
    }
    
    // Update the original array and num_radii
    for (int i = 0; i < idx; i++) {
        best_widths[i] = adjusted_widths[i];
    }
    *num_radii = idx;
}

int main() {
    double radii[] = {4.5, 9.0, 3.0, 6.0, 1.5, 3.0, 6.0, 6.0, 3.0, 2.0, 1.5, 6.0, 6.0, 2.5, 6.0, 6.0, 1.5, 2.5, 6.0, 6.0, 6.0, 6.0};
    int num_circles[] = {25, 15, 50, 10, 120, 10, 100, 4, 50, 50, 15, 40, 40, 50, 7, 50, 100, 40, 2, 8, 12, 4};
    int num_radii = sizeof(radii) / sizeof(radii[0]);
    
    double best_widths[num_radii];

    printf("Best rectangle widths for each circle packing:\n");
    for (int i = 0; i < num_radii; i++) {
        compute_min_width(radii[i], HEIGHT, num_circles[i], &best_widths[i]);
        //printf("\nRadius: %.2f, Count: %d -> Best Width: %.2f\n\n", radii[i], num_circles[i], best_widths[i]);
    }
    
    // Adjust best_widths
    adjust_best_widths(best_widths, &num_radii);

    printf("\nAdjusted best widths for packing:\n");
    for (int i = 0; i < num_radii; i++) {
        printf("%.2f ", best_widths[i]);
    }
    printf("\n");

    printf("\nProceeding with rectangle packing...\n");
    pack_rectangles(best_widths, num_radii);
    
    return 0;
}
48.0
