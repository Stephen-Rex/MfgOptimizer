#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>

#define MAX_MACHINES 15
#define GRID_SIZE_X 20
#define GRID_SIZE_Y 20

typedef struct {
    int id;
    char name[30];
    double x;             /* Center X coordinate */
    double y;             /* Center Y coordinate */
    double dim_x;         /* Geometric Width */
    double dim_y;         /* Geometric Height */
    double so_px;         /* Positive X Standoff */
    double so_nx;         /* Negative X Standoff */
    double so_py;         /* Positive Y Standoff */
    double so_ny;         /* Negative Y Standoff */
    double process_time;
    double setup_time;
} Machine;

typedef struct {
    int src_id;
    int dest_id;
    double volume;
} MaterialFlow;

Machine machines[] = {
    {1, "Raw Material Intake", 3.0, 2.0, 3.0, 2.0, 1.0, 1.0, 1.0, 1.0, 2.0, 5.0},
    {2, "CNC Milling", 12.0, 14.0, 4.0, 4.0, 1.5, 1.5, 1.5, 1.5, 8.5, 20.0},
    {3, "Laser Welder", 5.0, 8.0, 3.0, 3.0, 1.2, 1.2, 1.2, 1.2, 4.0, 15.0},
    {4, "Surface Treatment", 17.0, 3.0, 5.0, 3.0, 1.0, 1.0, 1.0, 1.0, 6.0, 10.0},
    {5, "Quality Assembly", 15.0, 10.0, 3.5, 2.5, 0.8, 0.8, 0.8, 0.8, 5.0, 8.0}
};
int num_machines = 5;

MaterialFlow flows[] = {
    {1, 2, 120.0},
    {2, 3, 100.0},
    {3, 4, 80.0},
    {4, 5, 95.0},
    {2, 5, 15.0}
};
int num_flows = 5;

double calculate_center_distance(double x1, double y1, double x2, double y2) {
    return sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
}

bool check_safe_overlap(double x1, double y1, double w1, double h1, double px1, double nx1, double py1, double ny1,
                        double x2, double y2, double w2, double h2, double px2, double nx2, double py2, double ny2) {
    double min_x1 = x1 - w1 / 2.0 - nx1;
    double max_x1 = x1 + w1 / 2.0 + px1;
    double min_y1 = y1 - h1 / 2.0 - ny1;
    double max_y1 = y1 + h1 / 2.0 + py1;
    
    double min_x2 = x2 - w2 / 2.0 - nx2;
    double max_x2 = x2 + w2 / 2.0 + px2;
    double min_y2 = y2 - h2 / 2.0 - ny2;
    double max_y2 = y2 + h2 / 2.0 + py2;
    
    return min_x1 < max_x2 && max_x1 > min_x2 && min_y1 < max_y2 && max_y1 > min_y2;
}

bool is_safe_out_of_bounds(double x, double y, double w, double h, double px, double nx, double py, double ny) {
    return (x - w/2.0 - nx < 0.0) || (x + w/2.0 + px > GRID_SIZE_X) || (y - h/2.0 - ny < 0.0) || (y + h/2.0 + py > GRID_SIZE_Y);
}

/* Helper functions for 2D Line Segment Intersection Math */
int get_orientation(double px, double py, double qx, double qy, double rx, double ry) {
    double val = (qy - py) * (rx - qx) - (qx - px) * (ry - qy);
    if (fabs(val) < 1e-7) return 0;  /* Collinear */
    return (val > 0.0) ? 1 : 2;      /* Clockwise or Counterclockwise */
}

bool on_segment(double px, double py, double qx, double qy, double rx, double ry) {
    return qx <= fmax(px, rx) && qx >= fmin(px, rx) &&
           qy <= fmax(py, ry) && qy >= fmin(py, ry);
}

bool do_intersect(double x1, double y1, double x2, double y2,
                  double x3, double y3, double x4, double y4) {
    /* Exclude flows that connect to the exact same machine center (sequential processes) */
    if ((x1 == x3 && y1 == y3) || (x1 == x4 && y1 == y4) ||
        (x2 == x3 && y2 == y3) || (x2 == x4 && y2 == y4)) {
        return false;
    }

    int o1 = get_orientation(x1, y1, x2, y2, x3, y3);
    int o2 = get_orientation(x1, y1, x2, y2, x4, y4);
    int o3 = get_orientation(x3, y3, x4, y4, x1, y1);
    int o4 = get_orientation(x3, y3, x4, y4, x2, y2);

    if (o1 != o2 && o3 != o4) return true;

    if (o1 == 0 && on_segment(x1, y1, x3, y3, x2, y2)) return true;
    if (o2 == 0 && on_segment(x1, y1, x4, y4, x2, y2)) return true;
    if (o3 == 0 && on_segment(x3, y3, x1, y1, x4, y4)) return true;
    if (o4 == 0 && on_segment(x3, y3, x2, y2, x4, y4)) return true;

    return false;
}

/* Cost evaluator utilizing high penalties for overlaps, boundary violations, and path crossings */
double evaluate_layout_with_penalties(void) {
    double transport_cost = 0.0;
    double penalty = 0.0;
    int i, j, k;

    /* 1. Calculate weighted material transport cost */
    for (i = 0; i < num_flows; i++) {
        int src = flows[i].src_id;
        int dest = flows[i].dest_id;
        int idx_src = -1, idx_dest = -1;
        for (j = 0; j < num_machines; j++) {
            if (machines[j].id == src) idx_src = j;
            if (machines[j].id == dest) idx_dest = j;
        }
        if (idx_src != -1 && idx_dest != -1) {
            double dist = calculate_center_distance(machines[idx_src].x, machines[idx_src].y, 
                                                    machines[idx_dest].x, machines[idx_dest].y);
            transport_cost += dist * flows[i].volume;
        }
    }

    /* 2. Overlap and out-of-bounds containment penalties */
    for (i = 0; i < num_machines; i++) {
        if (is_safe_out_of_bounds(machines[i].x, machines[i].y, machines[i].dim_x, machines[i].dim_y,
                                  machines[i].so_px, machines[i].so_nx, machines[i].so_py, machines[i].so_ny)) {
            penalty += 10000.0;
        }
        for (j = i + 1; j < num_machines; j++) {
            if (check_safe_overlap(machines[i].x, machines[i].y, machines[i].dim_x, machines[i].dim_y,
                                   machines[i].so_px, machines[i].so_nx, machines[i].so_py, machines[i].so_ny,
                                   machines[j].x, machines[j].y, machines[j].dim_x, machines[j].dim_y,
                                   machines[j].so_px, machines[j].so_nx, machines[j].so_py, machines[j].so_ny)) {
                penalty += 20000.0;
            }
        }
    }

    /* 3. Segment intersection crossings penalties */
    for (i = 0; i < num_flows; i++) {
        int src_a = flows[i].src_id;
        int dest_a = flows[i].dest_id;
        int idx_src_a = -1, idx_dest_a = -1;
        for (k = 0; k < num_machines; k++) {
            if (machines[k].id == src_a) idx_src_a = k;
            if (machines[k].id == dest_a) idx_dest_a = k;
        }
        if (idx_src_a == -1 || idx_dest_a == -1) continue;

        double ax1 = machines[idx_src_a].x;
        double ay1 = machines[idx_src_a].y;
        double ax2 = machines[idx_dest_a].x;
        double ay2 = machines[idx_dest_a].y;

        for (j = i + 1; j < num_flows; j++) {
            int src_b = flows[j].src_id;
            int dest_b = flows[j].dest_id;
            int idx_src_b = -1, idx_dest_b = -1;
            for (k = 0; k < num_machines; k++) {
                if (machines[k].id == src_b) idx_src_b = k;
                if (machines[k].id == dest_b) idx_dest_b = k;
            }
            if (idx_src_b == -1 || idx_dest_b == -1) continue;

            double bx1 = machines[idx_src_b].x;
            double by1 = machines[idx_src_b].y;
            double bx2 = machines[idx_dest_b].x;
            double by2 = machines[idx_dest_b].y;

            if (do_intersect(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2)) {
                penalty += 15000.0;
            }
        }
    }

    return transport_cost + penalty;
}

void optimize_placement(void) {
    double best_cost = evaluate_layout_with_penalties();
    bool improved = true;
    int iterations = 0;
    int i;
    double dx, dy;
    
    while (improved && iterations < 100) {
        improved = false;
        iterations++;
        for (i = 0; i < num_machines; i++) {
            double original_x = machines[i].x;
            double original_y = machines[i].y;
            double best_dx = 0.0, best_dy = 0.0;
            
            /* Wider search radius coordinates exploration */
            for (dx = -3.0; dx <= 3.0; dx += 0.5) {
                for (dy = -3.0; dy <= 3.0; dy += 0.5) {
                    if (dx == 0.0 && dy == 0.0) continue;
                    
                    machines[i].x = original_x + dx;
                    machines[i].y = original_y + dy;
                    
                    double current_cost = evaluate_layout_with_penalties();
                    if (current_cost < best_cost) {
                        best_cost = current_cost;
                        best_dx = dx;
                        best_dy = dy;
                        improved = true;
                    }
                }
            }
            machines[i].x = original_x + best_dx;
            machines[i].y = original_y + best_dy;
        }
    }
}

int main(void) {
    double init_cost = evaluate_layout_with_penalties();
    optimize_placement();
    double opt_cost = evaluate_layout_with_penalties();
    
    FILE *fp = fopen("layout_output.json", "w");
    if (!fp) return 1;
    
    fprintf(fp, "{\n");
    fprintf(fp, "  \"initial_transport_cost\": %.2f,\n", init_cost);
    fprintf(fp, "  \"optimized_transport_cost\": %.2f,\n", opt_cost);
    
    double total_dwell = 0.0;
    double bottleneck_time = -1.0;
    char bottleneck_name[30] = "";
    int i;
    for(i=0; i<num_machines; i++) {
        double dwell = machines[i].process_time + (machines[i].setup_time / 50.0);
        total_dwell += dwell;
        if(dwell > bottleneck_time) {
            bottleneck_time = dwell;
            strcpy(bottleneck_name, machines[i].name);
        }
    }
    
    fprintf(fp, "  \"dwell_time_analysis\": {\n");
    fprintf(fp, "    \"total_dwell_time\": %.2f,\n", total_dwell);
    fprintf(fp, "    \"bottleneck_machine\": \"%s\",\n", bottleneck_name);
    fprintf(fp, "    \"bottleneck_dwell_time\": %.2f\n", bottleneck_time);
    fprintf(fp, "  },\n");
    
    fprintf(fp, "  \"machines\": [\n");
    for (i = 0; i < num_machines; i++) {
        bool safe = true;
        
        /* Confirm absolute compliance on final optimal placement */
        if (is_safe_out_of_bounds(machines[i].x, machines[i].y, machines[i].dim_x, machines[i].dim_y,
                                  machines[i].so_px, machines[i].so_nx, machines[i].so_py, machines[i].so_ny)) {
            safe = false;
        } else {
            for (int j = 0; j < num_machines; j++) {
                if (i != j && check_safe_overlap(machines[i].x, machines[i].y, machines[i].dim_x, machines[i].dim_y,
                                                 machines[i].so_px, machines[i].so_nx, machines[i].so_py, machines[i].so_ny,
                                                 machines[j].x, machines[j].y, machines[j].dim_x, machines[j].dim_y,
                                                 machines[j].so_px, machines[j].so_nx, machines[j].so_py, machines[j].so_ny)) {
                    safe = false;
                    break;
                }
            }
        }
        
        fprintf(fp, "    {\n");
        fprintf(fp, "      \"id\": %d,\n", machines[i].id);
        fprintf(fp, "      \"name\": \"%s\",\n", machines[i].name);
        fprintf(fp, "      \"optimized_x\": %.2f,\n", machines[i].x);
        fprintf(fp, "      \"optimized_y\": %.2f,\n", machines[i].y);
        fprintf(fp, "      \"is_safe\": %s\n", safe ? "true" : "false");
        fprintf(fp, "    }%s\n", (i == num_machines - 1) ? "" : ",");
    }
    fprintf(fp, "  ]\n");
    fprintf(fp, "}\n");
    fclose(fp);
    return 0;
}
