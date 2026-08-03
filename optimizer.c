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
    double s;             /* Cumulative distance along polyline */
    double x;             /* Calculated Cartesian X coordinate */
    double y;             /* Calculated Cartesian Y coordinate */
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
    {1, "Raw Material Intake", 0.0, 0.0, 0.0, 3.0, 2.0, 1.0, 1.0, 1.0, 1.0, 2.0, 5.0},
    {2, "CNC Milling", 10.0, 0.0, 0.0, 4.0, 4.0, 1.5, 1.5, 1.5, 1.5, 8.5, 20.0},
    {3, "Laser Welder", 20.0, 0.0, 0.0, 3.0, 3.0, 1.2, 1.2, 1.2, 1.2, 4.0, 15.0},
    {4, "Surface Treatment", 30.0, 0.0, 0.0, 5.0, 3.0, 1.0, 1.0, 1.0, 1.0, 6.0, 10.0},
    {5, "Quality Assembly", 40.0, 0.0, 0.0, 3.5, 2.5, 0.8, 0.8, 0.8, 0.8, 5.0, 8.0}
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

/* Global dynamic vertices array generated from user GUI inputs */
double polyline_x[5] = {3.00, 3.00, 10.00, 17.00, 17.00};
double polyline_y[5] = {3.00, 17.00, 17.00, 10.00, 3.00};

double calculate_center_distance(double x1, double y1, double x2, double y2) {
    return sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
}

/* Interpolate 2D Cartesian Coordinate from cumulative distance along Dynamic 5-Point Polyline */
void get_point_on_polyline(double s, double *out_x, double *out_y) {
    double seg_lens[4];
    int i;
    for (i = 0; i < 4; i++) {
        seg_lens[i] = sqrt((polyline_x[i+1]-polyline_x[i])*(polyline_x[i+1]-polyline_x[i]) + 
                           (polyline_y[i+1]-polyline_y[i])*(polyline_y[i+1]-polyline_y[i]));
    }
    
    double current_s = 0.0;
    for (i = 0; i < 4; i++) {
        if (s <= current_s + seg_lens[i]) {
            double ratio = (s - current_s) / seg_lens[i];
            *out_x = polyline_x[i] + ratio * (polyline_x[i+1] - polyline_x[i]);
            *out_y = polyline_y[i] + ratio * (polyline_y[i+1] - polyline_y[i]);
            return;
        }
        current_s += seg_lens[i];
    }
    *out_x = polyline_x[4];
    *out_y = polyline_y[4];
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

double evaluate_polyline_layout(void) {
    double transport_cost = 0.0;
    double penalty = 0.0;
    int i, j;

    /* 1. Map dynamic spacings to 2D coordinates */
    for (i = 0; i < num_machines; i++) {
        get_point_on_polyline(machines[i].s, &machines[i].x, &machines[i].y);
    }

    /* 2. Calculate material transport flow cost */
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

    /* 3. Safety Box containment and overlap checking */
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

    return transport_cost + penalty;
}

void optimize_placement(void) {
    double best_cost = evaluate_polyline_layout();
    bool improved = true;
    int iterations = 0;
    int i;
    double ds;

    while (improved && iterations < 150) {
        improved = false;
        iterations++;
        for (i = 1; i < num_machines; i++) { /* Machine 1 at s=0 is anchored */
            double original_s = machines[i].s;
            double best_ds = 0.0;
            
            for (ds = -4.0; ds <= 4.0; ds += 0.5) {
                if (ds == 0.0) continue;
                
                double candidate_s = original_s + ds;
                double min_s = machines[i-1].s + (machines[i-1].dim_x + machines[i].dim_x)/2.0;
                if (candidate_s < min_s) continue;
                
                machines[i].s = candidate_s;
                double current_cost = evaluate_polyline_layout();
                
                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_ds = ds;
                    improved = true;
                }
            }
            machines[i].s = original_s + best_ds;
        }
    }
}

int main(void) {
    double init_cost = evaluate_polyline_layout();
    optimize_placement();
    double opt_cost = evaluate_polyline_layout();
    
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

