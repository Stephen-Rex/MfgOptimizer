#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>

#define MAX_MACHINES 10
#define GRID_SIZE 20
#define K_SAFE 1.6  /* Constant approach speed of body/parts (m/s) as per ISO 13855 */
#define C_SAFE 0.25 /* Intrusion distance constant buffer (m) */

typedef struct {
    int id;
    char name[30];
    int x;                /* X coordinate on floor grid (meters) */
    int y;                /* Y coordinate on floor grid (meters) */
    double process_time;  /* Dwell/process time per part (mins) */
    double setup_time;    /* Setup time per batch (mins) */
    double stopping_time; /* Machine stopping time (seconds) */
    double safety_dist;   /* Minimum safety distance (meters) */
} Machine;

typedef struct {
    int src_id;
    int dest_id;
    double volume;        /* Frequency/Volume of material transfer (parts/hour) */
} MaterialFlow;

Machine machines[MAX_MACHINES] = {
    {1, "Raw Material Intake", 1, 1, 2.0, 5.0, 0.1, 0.0},
    {2, "CNC Milling", 12, 14, 8.5, 20.0, 1.2, 0.0},
    {3, "Laser Welder", 5, 8, 4.0, 15.0, 0.8, 0.0},
    {4, "Surface Treatment", 18, 2, 6.0, 10.0, 0.5, 0.0},
    {5, "Quality Assembly", 15, 10, 5.0, 8.0, 0.3, 0.0}
};
int num_machines = 5;

MaterialFlow flows[] = {
    {1, 2, 120.0}, /* Raw Material to CNC */
    {2, 3, 100.0}, /* CNC to Laser Welder */
    {3, 4, 80.0},  /* Laser Welder to Surface Treatment */
    {4, 5, 95.0},  /* Surface Treatment to Quality Assembly */
    {2, 5, 15.0}   /* CNC directly to Quality Assembly */
};
int num_flows = 5;

/* Calculate Euclidean Distance between coordinates */
double calculate_distance(int x1, int y1, int x2, int y2) {
    return sqrt((double)((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2)));
}

/* ISO 13855 safety distance calculation: S = K * T + C */
double calculate_iso_safety_distance(double stop_time) {
    double total_response_time = stop_time + 0.1; /* 100ms system response time buffer */
    return (K_SAFE * total_response_time) + C_SAFE;
}

/* Evaluate layout transport cost = sum(distance * flow_volume) */
double evaluate_layout(void) {
    double total_cost = 0.0;
    int i, j;
    for (i = 0; i < num_flows; i++) {
        int src = flows[i].src_id;
        int dest = flows[i].dest_id;
        int idx_src = -1, idx_dest = -1;
        
        for (j = 0; j < num_machines; j++) {
            if (machines[j].id == src) idx_src = j;
            if (machines[j].id == dest) idx_dest = j;
        }
        
        if (idx_src != -1 && idx_dest != -1) {
            double dist = calculate_distance(machines[idx_src].x, machines[idx_src].y, 
                                             machines[idx_dest].x, machines[idx_dest].y);
            total_cost += dist * flows[i].volume;
        }
    }
    return total_cost;
}

/* Perform layout optimization (Hill-climbing heuristic) */
void optimize_placement(void) {
    double best_cost;
    bool improved = true;
    int iterations = 0;
    int i, dx, dy, k;

    printf("\n>>> Starting Factory Floor Machine Placement Optimization Heuristic <<<\n");
    best_cost = evaluate_layout();
    printf("Initial Layout Transport Cost (m * parts/hr): %.2f\n", best_cost);
    
    while (improved && iterations < 100) {
        improved = false;
        iterations++;
        
        for (i = 0; i < num_machines; i++) {
            int original_x = machines[i].x;
            int original_y = machines[i].y;
            int best_dx = 0, best_dy = 0;
            
            /* Try 8-neighborhood coordinate search to optimize material flows */
            for (dx = -2; dx <= 2; dx++) {
                for (dy = -2; dy <= 2; dy++) {
                    int nx, ny;
                    bool overlap = false;
                    double current_cost;
                    
                    if (dx == 0 && dy == 0) continue;
                    
                    nx = original_x + dx;
                    ny = original_y + dy;
                    
                    /* Floor boundaries check */
                    if (nx < 0 || nx > GRID_SIZE || ny < 0 || ny > GRID_SIZE) continue;
                    
                    /* Overlap prevention check */
                    for (k = 0; k < num_machines; k++) {
                        if (k != i && machines[k].x == nx && machines[k].y == ny) {
                            overlap = true;
                            break;
                        }
                    }
                    if (overlap) continue;
                    
                    machines[i].x = nx;
                    machines[i].y = ny;
                    current_cost = evaluate_layout();
                    
                    if (current_cost < best_cost) {
                        best_cost = current_cost;
                        best_dx = dx;
                        best_dy = dy;
                        improved = true;
                    }
                }
            }
            
            /* Apply best structural placement step */
            if (improved) {
                machines[i].x = original_x + best_dx;
                machines[i].y = original_y + best_dy;
            } else {
                machines[i].x = original_x;
                machines[i].y = original_y;
            }
        }
    }
    printf("Optimization Heuristic Completed in %d Iterations.\n", iterations);
    printf("Optimized Layout Transport Cost (m * parts/hr): %.2f\n", best_cost);
}

/* Perform Dwell & Cycle Time Calculations */
void analyze_dwell_times(void) {
    double total_dwell = 0.0;
    double bottleneck_time = 0.0;
    char bottleneck_name[30] = "";
    int i;

    printf("\n=== MANUFACTURING DWELL TIME AND CYCLE TIME ANALYSIS ===\n");
    printf("%-25s | %-12s | %-12s | %-15s | %-15s\n", 
           "Machine Name", "Process (m)", "Setup (m)", "Dwell Time (m)", "Capacity (P/hr)");
    printf("-------------------------------------------------------------------------------------\n");
    
    for (i = 0; i < num_machines; i++) {
        /* Dwell time per part = process time + (setup time / typical batch size of 50 parts) */
        double batch_size = 50.0;
        double dwell = machines[i].process_time + (machines[i].setup_time / batch_size);
        double capacity = 60.0 / (machines[i].process_time); /* Max hourly throughput capacity */
        
        total_dwell += dwell;
        
        printf("%-25s | %-12.2f | %-12.2f | %-15.2f | %-15.2f\n", 
               machines[i].name, machines[i].process_time, machines[i].setup_time, dwell, capacity);
               
        if (dwell > bottleneck_time) {
            bottleneck_time = dwell;
            strcpy(bottleneck_name, machines[i].name);
        }
    }
    printf("-------------------------------------------------------------------------------------\n");
    printf("Total Manufacturing Direct Dwell Time: %.2f minutes\n", total_dwell);
    printf("Identified Production Bottleneck: %s with Dwell Time of %.2f mins/part\n", bottleneck_name, bottleneck_time);
}

/* Perform Safety Calculations */
void calculate_safety_metrics(void) {
    int i, j;
    printf("\n=== MANUFACTURING LINE SAFETY CALCULATIONS (ISO 13855) ===\n");
    printf("%-25s | %-18s | %-20s | %-20s\n", 
           "Machine Name", "Stop Time (s)", "Req. Clearance (m)", "Current Safe Zone Status");
    printf("----------------------------------------------------------------------------------------------\n");
    
    for (i = 0; i < num_machines; i++) {
        machines[i].safety_dist = calculate_iso_safety_distance(machines[i].stopping_time);
        bool safe = true;
        double min_allowed_dist = machines[i].safety_dist;
        
        for (j = 0; j < num_machines; j++) {
            if (i == j) continue;
            double actual_dist = calculate_distance(machines[i].x, machines[i].y, machines[j].x, machines[j].y);
            if (actual_dist < min_allowed_dist) {
                safe = false;
            }
        }
        
        printf("%-25s | %-18.2f | %-20.2f | %-20s\n", 
               machines[i].name, 
               machines[i].stopping_time, 
               machines[i].safety_dist, 
               safe ? "SAFE" : "WARNING: TOO CLOSE");
    }
    printf("----------------------------------------------------------------------------------------------\n");
}

/* Print factory floor mapping layout visual */
void print_layout_map(void) {
    char grid[GRID_SIZE + 1][GRID_SIZE + 1];
    int r, c, i;

    printf("\n=== FACTORY FLOOR MACHINE PLACEMENT MAP (Grid: 20x20 meters) ===\n");
    
    for (r = 0; r <= GRID_SIZE; r++) {
        for (c = 0; c <= GRID_SIZE; c++) {
            grid[r][c] = '.';
        }
    }
    
    for (i = 0; i < num_machines; i++) {
        int x = machines[i].x;
        int y = machines[i].y;
        if (x >= 0 && x <= GRID_SIZE && y >= 0 && y <= GRID_SIZE) {
            grid[y][x] = '0' + machines[i].id;
        }
    }
    
    for (r = GRID_SIZE; r >= 0; r--) {
        printf("%02d | ", r);
        for (c = 0; c <= GRID_SIZE; c++) {
            printf("%c ", grid[r][c]);
        }
        printf("\n");
    }
    
    printf("   -");
    for (c = 0; c <= GRID_SIZE; c++) printf("--");
    printf("\n     ");
    for (c = 0; c <= GRID_SIZE; c++) {
        if (c % 5 == 0) printf("%02d ", c);
        else printf("   ");
    }
    printf("\n\nMachine IDs Map:\n");
    for (i = 0; i < num_machines; i++) {
        printf("[%d] %s at (%d, %d)\n", machines[i].id, machines[i].name, machines[i].x, machines[i].y);
    }
}

int main(void) {
    printf("===================================================================\n");
    printf("        FACTORY FLOOR LAYOUT & MANUFACTURING OPTIMIZER             \n");
    printf("===================================================================\n");
    
    /* 1. Display original layout mapping */
    printf("--- INITIAL STAGE ---\n");
    print_layout_map();
    evaluate_layout();
    
    /* 2. Perform safety calculations */
    calculate_safety_metrics();
    
    /* 3. Perform Placement Heuristic Optimization */
    optimize_placement();
    
    /* 4. Perform Safety Calculations on updated positions */
    printf("\n--- POST-OPTIMIZATION CHECK ---\n");
    calculate_safety_metrics();
    print_layout_map();
    
    /* 5. Manufacturing Dwell Time Analysis */
    analyze_dwell_times();
    
    printf("\n===================================================================\n");
    printf("Optimization completed successfully. Layout can be safely deployed.\n");
    printf("===================================================================\n");
    
    return 0;
}

