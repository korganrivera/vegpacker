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
#include <ctype.h>

#define LARGE_RECT_WIDTH 360 // The width of the larger rectangles
#define HEIGHT 36
#define DEFAULT_PLANTS_CSV "plants.csv"
#define DEFAULT_LAYOUT_CSV "garden_layout.csv"
#define MAX_PLANTS 256
#define MAX_PLANT_NAME 128
#define MAX_CSV_LINE 512

typedef enum {
    PLANTING_GRID,
    PLANTING_TRELLIS
} PlantingStyle;

typedef struct {
    char name[MAX_PLANT_NAME];
    int num_circles;
    double spacing;
    double radius;
    PlantingStyle planting_style;
} Plant;

typedef struct {
    char label[MAX_PLANT_NAME + 16];
    double width;
} PlantWidth;

static void copy_text(char *dest, size_t dest_size, const char *src) {
    if (dest_size == 0) {
        return;
    }

    size_t len = strlen(src);
    if (len >= dest_size) {
        len = dest_size - 1;
    }

    memcpy(dest, src, len);
    dest[len] = '\0';
}

static void set_segment_label(char *dest, size_t dest_size, const char *label, int part_number) {
    char suffix[16];
    snprintf(suffix, sizeof(suffix), "#%d", part_number);

    size_t suffix_len = strlen(suffix);
    if (suffix_len >= dest_size) {
        dest[0] = '\0';
        return;
    }

    size_t max_label_len = dest_size - suffix_len - 1;
    size_t label_len = strlen(label);
    if (label_len > max_label_len) {
        label_len = max_label_len;
    }

    memcpy(dest, label, label_len);
    memcpy(dest + label_len, suffix, suffix_len + 1);
}

static int split_segment_label(const char *label, char *base, size_t base_size, int *part_number) {
    const char *hash = strrchr(label, '#');
    if (hash == NULL || *(hash + 1) == '\0') {
        return 0;
    }

    char *end = NULL;
    long parsed_part = strtol(hash + 1, &end, 10);
    if (end == hash + 1 || *end != '\0' || parsed_part <= 0) {
        return 0;
    }

    size_t base_len = (size_t)(hash - label);
    if (base_len >= base_size) {
        base_len = base_size - 1;
    }

    memcpy(base, label, base_len);
    base[base_len] = '\0';
    *part_number = (int)parsed_part;
    return 1;
}

static int full_width_group_length(int num_rectangles, PlantWidth packed_rects[][num_rectangles], int *packed_counts, int start_row) {
    if (packed_counts[start_row] != 1 || fabs(packed_rects[start_row][0].width - LARGE_RECT_WIDTH) > 0.001) {
        return 1;
    }

    char base[MAX_PLANT_NAME + 16];
    int first_part = 0;
    if (!split_segment_label(packed_rects[start_row][0].label, base, sizeof(base), &first_part)) {
        return 1;
    }

    int length = 1;
    for (int row = start_row + 1; row < num_rectangles; row++) {
        if (packed_counts[row] != 1 || fabs(packed_rects[row][0].width - LARGE_RECT_WIDTH) > 0.001) {
            break;
        }

        char next_base[MAX_PLANT_NAME + 16];
        int next_part = 0;
        if (!split_segment_label(packed_rects[row][0].label, next_base, sizeof(next_base), &next_part)) {
            break;
        }

        if (strcmp(base, next_base) != 0 || next_part != first_part + length) {
            break;
        }

        length++;
    }

    return length;
}

static void write_csv_field(FILE *file, const char *value) {
    int needs_quotes = 0;
    for (const char *p = value; *p != '\0'; p++) {
        if (*p == ',' || *p == '"' || *p == '\n' || *p == '\r') {
            needs_quotes = 1;
            break;
        }
    }

    if (!needs_quotes) {
        fputs(value, file);
        return;
    }

    fputc('"', file);
    for (const char *p = value; *p != '\0'; p++) {
        if (*p == '"') {
            fputc('"', file);
        }
        fputc(*p, file);
    }
    fputc('"', file);
}

static int write_layout_csv(const char *path, int num_rectangles, PlantWidth packed_rects[][num_rectangles], int *packed_counts, int large_rect_count) {
    FILE *file = fopen(path, "w");
    if (file == NULL) {
        fprintf(stderr, "Error: could not write layout CSV '%s'\n", path);
        return -1;
    }

    fprintf(file, "row,segment_label,length_in,crop\n");

    for (int i = 0; i < large_rect_count; i++) {
        for (int j = 0; j < packed_counts[i]; j++) {
            char crop[MAX_PLANT_NAME + 16];
            int part_number = 0;
            if (!split_segment_label(packed_rects[i][j].label, crop, sizeof(crop), &part_number)) {
                copy_text(crop, sizeof(crop), packed_rects[i][j].label);
            }

            fprintf(file, "%d,", i + 1);
            write_csv_field(file, packed_rects[i][j].label);
            fprintf(file, ",%.2f,", packed_rects[i][j].width);
            write_csv_field(file, crop);
            fprintf(file, "\n");
        }
    }

    fclose(file);
    return 0;
}

static char *trim_whitespace(char *value) {
    while (isspace((unsigned char)*value)) {
        value++;
    }

    if (*value == '\0') {
        return value;
    }

    char *end = value + strlen(value) - 1;
    while (end > value && isspace((unsigned char)*end)) {
        *end = '\0';
        end--;
    }

    return value;
}

static int equals_ignore_case(const char *a, const char *b) {
    while (*a != '\0' && *b != '\0') {
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) {
            return 0;
        }
        a++;
        b++;
    }

    return *a == '\0' && *b == '\0';
}

static const char *planting_style_name(PlantingStyle planting_style) {
    switch (planting_style) {
        case PLANTING_TRELLIS:
            return "trellis";
        case PLANTING_GRID:
        default:
            return "grid";
    }
}

static int parse_planting_style(const char *value, PlantingStyle *planting_style) {
    if (equals_ignore_case(value, "grid")) {
        *planting_style = PLANTING_GRID;
        return 0;
    }

    if (equals_ignore_case(value, "trellis")) {
        *planting_style = PLANTING_TRELLIS;
        return 0;
    }

    return -1;
}

static int parse_csv_fields(char *line, char **fields, int max_fields) {
    int count = 0;
    char *p = line;

    while (*p != '\0' && count < max_fields) {
        while (*p == ' ' || *p == '\t') {
            p++;
        }

        if (*p == '"') {
            p++;
            fields[count++] = p;

            char *out = p;
            while (*p != '\0') {
                if (*p == '"') {
                    if (*(p + 1) == '"') {
                        *out++ = '"';
                        p += 2;
                    } else {
                        p++;
                        break;
                    }
                } else {
                    *out++ = *p++;
                }
            }
            *out = '\0';

            while (*p != '\0' && *p != ',') {
                p++;
            }
        } else {
            fields[count++] = p;
            while (*p != '\0' && *p != ',') {
                p++;
            }
        }

        if (*p == ',') {
            *p = '\0';
            p++;
        }
    }

    return count;
}

static int load_plants_csv(const char *path, Plant *plants, int max_plants) {
    FILE *file = fopen(path, "r");
    if (file == NULL) {
        fprintf(stderr, "Error: could not open CSV file '%s'\n", path);
        return -1;
    }

    char line[MAX_CSV_LINE];
    int plant_count = 0;
    int line_number = 0;

    while (fgets(line, sizeof(line), file) != NULL) {
        line_number++;
        line[strcspn(line, "\r\n")] = '\0';

        char *trimmed_line = trim_whitespace(line);
        if (*trimmed_line == '\0' || *trimmed_line == '#') {
            continue;
        }

        char *fields[4];
        int field_count = parse_csv_fields(trimmed_line, fields, 4);
        if (field_count < 3) {
            fprintf(stderr, "Error: %s:%d needs plant,count,spacing_in,planting_style\n", path, line_number);
            fclose(file);
            return -1;
        }

        char *plant_name = trim_whitespace(fields[0]);
        char *count_text = trim_whitespace(fields[1]);
        char *spacing_text = trim_whitespace(fields[2]);
        char *style_text = field_count >= 4 ? trim_whitespace(fields[3]) : "grid";

        if (plant_count == 0 && strcmp(plant_name, "plant") == 0) {
            continue;
        }

        if (plant_count >= max_plants) {
            fprintf(stderr, "Error: %s has more than %d plants\n", path, max_plants);
            fclose(file);
            return -1;
        }

        char *end = NULL;
        long num_circles = strtol(count_text, &end, 10);
        if (end == count_text || *trim_whitespace(end) != '\0' || num_circles <= 0) {
            fprintf(stderr, "Error: %s:%d has invalid plant count '%s'\n", path, line_number, count_text);
            fclose(file);
            return -1;
        }

        end = NULL;
        double spacing = strtod(spacing_text, &end);
        if (end == spacing_text || *trim_whitespace(end) != '\0' || spacing <= 0.0) {
            fprintf(stderr, "Error: %s:%d has invalid spacing '%s'\n", path, line_number, spacing_text);
            fclose(file);
            return -1;
        }

        PlantingStyle planting_style = PLANTING_GRID;
        if (parse_planting_style(style_text, &planting_style) != 0) {
            fprintf(stderr, "Error: %s:%d has invalid planting style '%s' (expected grid or trellis)\n", path, line_number, style_text);
            fclose(file);
            return -1;
        }

        copy_text(plants[plant_count].name, sizeof(plants[plant_count].name), plant_name);
        plants[plant_count].num_circles = (int)num_circles;
        plants[plant_count].spacing = spacing;
        plants[plant_count].planting_style = planting_style;
        plants[plant_count].radius = spacing / 2.0;
        plant_count++;
    }

    fclose(file);

    if (plant_count == 0) {
        fprintf(stderr, "Error: %s did not contain any plants\n", path);
        return -1;
    }

    return plant_count;
}

// Comparison function for sorting in descending order
int compare_desc(const void *a, const void *b) {
    const PlantWidth *width_a = (const PlantWidth *)a;
    const PlantWidth *width_b = (const PlantWidth *)b;
    double diff = width_b->width - width_a->width;
    if (diff > 0) return 1;
    if (diff < 0) return -1;
    return 0;
}

static void print_crop_table_header(void) {
    printf("\nCrop packing widths\n");
    printf("%-26s %-8s %7s %9s %12s %-14s\n", "Plant", "Style", "Count", "Spacing", "Width", "Method");
    printf("%-26s %-8s %7s %9s %12s %-14s\n", "-----", "-----", "-----", "-------", "-----", "------");
}

static void print_crop_table_row(const char *plant_name, PlantingStyle planting_style, int num_circles, double spacing, double best_width, const char *method) {
    printf("%-26s %-8s %7d %9.2f %12.2f %-14s\n",
           plant_name,
           planting_style_name(planting_style),
           num_circles,
           spacing,
           best_width,
           method);
}

// Function to compute the minimum width needed for circle packing
void compute_min_width(double radius, int height, int num_circles, double *best_width, char *best_pattern, size_t best_pattern_size) {
    double r = radius;
    double h = (double)height;
    int n = num_circles;
    
    // Flat-topped packing
    int rows_flat = (int)(h / (2 * r));
    if (rows_flat < 1) rows_flat = 1;
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
    if (rows_pointy < 1) rows_pointy = 1;
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

    int smallest_width = 0;

    if (width_flat < width_pointy && width_flat < width_regular) {
        smallest_width = 1;
    } else if (width_pointy < width_flat && width_pointy < width_regular) {
        smallest_width = 2;
    }

    switch (smallest_width) {
        case 1:
            copy_text(best_pattern, best_pattern_size, "flat-topped");
            break;
        case 2:
            copy_text(best_pattern, best_pattern_size, "pointy-topped");
            break;
        default:
            copy_text(best_pattern, best_pattern_size, "regular");
            break;
    }
}

// Function to pack smaller rectangles into larger rectangles
void pack_rectangles(PlantWidth *small_widths, int num_rectangles) {
    qsort(small_widths, num_rectangles, sizeof(PlantWidth), compare_desc); // Sort widths descending
    
    double remaining_space[num_rectangles]; // Track remaining space in each large rectangle
    int large_rect_count = 0;
    PlantWidth packed_rects[num_rectangles][num_rectangles]; // Store packing information
    int packed_counts[num_rectangles]; // Track count per large rectangle
    
    for (int i = 0; i < num_rectangles; i++) {
        packed_counts[i] = 0;
    }
    
    for (int i = 0; i < num_rectangles; i++) {
        int placed = 0;
        
        // Try to fit into an existing large rectangle
        for (int j = 0; j < large_rect_count; j++) {
            if (remaining_space[j] >= small_widths[i].width) {
                remaining_space[j] -= small_widths[i].width;
                packed_rects[j][packed_counts[j]++] = small_widths[i];
                placed = 1;
                break;
            }
        }
        
        // If not placed, start a new large rectangle
        if (!placed) {
            remaining_space[large_rect_count] = LARGE_RECT_WIDTH - small_widths[i].width;
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
    write_layout_csv(DEFAULT_LAYOUT_CSV, num_rectangles, packed_rects, packed_counts, large_rect_count);

    printf("\nBed summary\n");
    printf("Minimum rows by length: %d\n", (int)ceil((large_rect_count * (double)LARGE_RECT_WIDTH - total_waste) / LARGE_RECT_WIDTH));
    printf("Rows used: %d\n", large_rect_count);
    printf("Total row length: %.2f\n", large_rect_count * (double)LARGE_RECT_WIDTH);
    printf("Used length: %.2f\n", large_rect_count * (double)LARGE_RECT_WIDTH - total_waste);
    printf("Wasted length: %.2f (%.2f%%)\n", total_waste, 100.0 * total_waste / (large_rect_count * LARGE_RECT_WIDTH));
    printf("Layout CSV: %s\n", DEFAULT_LAYOUT_CSV);

    printf("\nRow layout\n");
    printf("%7s %9s %9s  %s\n", "Rows", "Used", "Left", "Segments");
    printf("%7s %9s %9s  %s\n", "----", "----", "----", "--------");
    for (int i = 0; i < large_rect_count; i++) {
        int group_length = full_width_group_length(num_rectangles, packed_rects, packed_counts, i);
        if (group_length > 1) {
            char base[MAX_PLANT_NAME + 16];
            int first_part = 0;
            split_segment_label(packed_rects[i][0].label, base, sizeof(base), &first_part);
            printf("%3d-%-3d %9.2f %9.2f  %s#%d-#%d %.2f each\n",
                   i + 1,
                   i + group_length,
                   (double)LARGE_RECT_WIDTH,
                   0.0,
                   base,
                   first_part,
                   first_part + group_length - 1,
                   (double)LARGE_RECT_WIDTH);
            i += group_length - 1;
            continue;
        }

        double used_space = LARGE_RECT_WIDTH - remaining_space[i];
        printf("%7d %9.2f %9.2f  ", i + 1, used_space, remaining_space[i]);
        for (int j = 0; j < packed_counts[i]; j++) {
            if (j > 0) {
                printf(", ");
            }
            printf("%s %.2f", packed_rects[i][j].label, packed_rects[i][j].width);
        }
        printf("\n");
    }
}

// Function to adjust best_widths array
int adjust_best_widths(PlantWidth **best_widths, int *num_radii) {
    int adjusted_count = 0;

    for (int i = 0; i < *num_radii; i++) {
        if ((*best_widths)[i].width > LARGE_RECT_WIDTH) {
            int parts = (int)((*best_widths)[i].width / LARGE_RECT_WIDTH);
            double remainder = (*best_widths)[i].width - (parts * LARGE_RECT_WIDTH);
            adjusted_count += parts + (remainder > 0.0 ? 1 : 0);
        } else {
            adjusted_count++;
        }
    }

    PlantWidth *adjusted_widths = malloc((size_t)adjusted_count * sizeof(PlantWidth));
    if (adjusted_widths == NULL) {
        fprintf(stderr, "Error: could not allocate adjusted widths\n");
        return -1;
    }

    int idx = 0;
    
    for (int i = 0; i < *num_radii; i++) {
        if ((*best_widths)[i].width > LARGE_RECT_WIDTH) {
            int parts = (int)((*best_widths)[i].width / LARGE_RECT_WIDTH);
            double remainder = (*best_widths)[i].width - (parts * LARGE_RECT_WIDTH);
            int total_parts = parts + (remainder > 0.0 ? 1 : 0);
            for (int j = 0; j < parts; j++) {
                set_segment_label(adjusted_widths[idx].label, sizeof(adjusted_widths[idx].label), (*best_widths)[i].label, j + 1);
                adjusted_widths[idx].width = LARGE_RECT_WIDTH;
                idx++;
            }
            if (remainder > 0) {
                set_segment_label(adjusted_widths[idx].label, sizeof(adjusted_widths[idx].label), (*best_widths)[i].label, total_parts);
                adjusted_widths[idx].width = remainder;
                idx++;
            }
        } else {
            adjusted_widths[idx++] = (*best_widths)[i];
        }
    }
    
    free(*best_widths);
    *best_widths = adjusted_widths;
    *num_radii = idx;
    return 0;
}

int main(int argc, char **argv) {
    const char *csv_path = (argc > 1) ? argv[1] : DEFAULT_PLANTS_CSV;
    Plant plants[MAX_PLANTS];
    int num_radii = load_plants_csv(csv_path, plants, MAX_PLANTS);
    if (num_radii < 0) {
        return 1;
    }
    
    PlantWidth *best_widths = malloc((size_t)num_radii * sizeof(PlantWidth));
    if (best_widths == NULL) {
        fprintf(stderr, "Error: could not allocate best widths\n");
        return 1;
    }

    printf("Loaded %d plants from %s\n", num_radii, csv_path);
    print_crop_table_header();
    for (int i = 0; i < num_radii; i++) {
        char method[32];
        copy_text(best_widths[i].label, sizeof(best_widths[i].label), plants[i].name);

        if (plants[i].planting_style == PLANTING_TRELLIS) {
            best_widths[i].width = plants[i].num_circles * plants[i].spacing;
            copy_text(method, sizeof(method), "single row");
        } else {
            compute_min_width(plants[i].radius, HEIGHT, plants[i].num_circles, &best_widths[i].width, method, sizeof(method));
        }

        print_crop_table_row(plants[i].name, plants[i].planting_style, plants[i].num_circles, plants[i].spacing, best_widths[i].width, method);
    }
    
    // Adjust best_widths
    if (adjust_best_widths(&best_widths, &num_radii) != 0) {
        free(best_widths);
        return 1;
    }

    pack_rectangles(best_widths, num_radii);

    free(best_widths);
    
    return 0;
}
