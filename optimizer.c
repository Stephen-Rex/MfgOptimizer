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

double calculate_center_distance(double x1, double y1, double x2, double y2) {
    return sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
}

void get_point_on_polyline(double s, double grid_x, double grid_y, double *out_x, double *out_y) {
    double vx[4], vy[4];
    vx[0] = 3.0; vy[0] = 3.0;
    vx[1] = 3.0; vy[1] = grid_y - 3.0;
    vx[2] = grid_x - 3.0; vy[2] = grid_y - 3.0;
    vx[3] = grid_x - 3.0; vy[3] = 3.0;
    
    double seg_lens[3];
    int i;
    for (i = 0; i < 3; i++) {
        seg_lens[i] = sqrt((vx[i+1]-vx[i])*(vx[i+1]-vx[i]) + (vy[i+1]-vy[i])*(vy[i+1]-vy[i]));
    }
    
    double current_s = 0.0;
    for (i = 0; i < 3; i++) {
        if (s <= current_s + seg_lens[i]) {
            double ratio = (s - current_s) / seg_lens[i];
            *out_x = vx[i] + ratio * (vx[i+1] - vx[i]);
            *out_y = vy[i] + ratio * (vy[i+1] - vy[i]);
            return;
        }
        current_s += seg_lens[i];
    }
    *out_x = vx[3];
    *out_y = vy[3];
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

    for (i = 0; i < num_machines; i++) {
        get_point_on_polyline(machines[i].s, GRID_SIZE_X, GRID_SIZE_Y, &machines[i].x, &machines[i].y);
    }

    for (i = 0; i < num_flows; i++) {
        int src = flows[i].src_id;
        int dest = flows[i].dest_id;
        int idx_src = -1, idx_dest = -1;
        for (j = 0; j < num_machines; j++) {
            if (machines[j].id == src) idx_src = j;
            if (machines[j].id == dest) idx_dest = j;
        }
        if (idx_src != -1 && idx_dest != -1) {
            double dist = calculate_center_distance(machines[idx_src].x, machines[idx_src].y, \n                                                    machines[idx_dest].x, machines[idx_dest].y);
            transport_cost += dist * flows[i].volume;
        }
    }

    for (i = 0; i < num_machines; i++) {
        if (is_safe_out_of_bounds(machines[i].x, machines[i].y, machines[i].dim_x, machines[i].dim_y,\n                                  machines[i].so_px, machines[i].so_nx, machines[i].so_py, machines[i].so_ny)) {
            penalty += 10000.0;
        }
        for (j = i + 1; j < num_machines; j++) {
            if (check_safe_overlap(machines[i].x, machines[i].y, machines[i].dim_x, machines[i].dim_y,\n                                   machines[i].so_px, machines[i].so_nx, machines[i].so_py, machines[i].so_ny,\n                                   machines[j].x, machines[j].y, machines[j].dim_x, machines[j].dim_y,\n                                   machines[j].so_px, machines[j].so_nx, machines[j].so_py, machines[j].so_ny)) {
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
        for (i = 1; i < num_machines; i++) { 
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
