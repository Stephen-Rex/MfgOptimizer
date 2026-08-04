#include <stdio.h>
#include <string.h>
#include <math.h>
#include "optimizer.h"

// Helper function for line intersection: Orientation test (Counter-Clockwise check)
static int ccw(Point a, Point b, Point c) {
    double val = (c.y - a.y) * (b.x - a.x) - (b.y - a.y) * (c.x - a.x);
    if (fabs(val) < 1e-9) return 0; // Collinear
    return (val > 0) ? 1 : -1;
}

// Helper function to check if point q lies on segment pr
static int on_segment(Point p, Point q, Point r) {
    if (q.x <= fmax(p.x, r.x) && q.x >= fmin(p.x, r.x) &&
        q.y <= fmax(p.y, r.y) && q.y >= fmin(p.y, r.y))
        return 1;
    return 0;
}

// Helper function implementing line segment intersection logic
static int intersect_segments(Point p1, Point q1, Point p2, Point q2) {
    int o1 = ccw(p1, q1, p2);
    int o2 = ccw(p1, q1, q2);
    int o3 = ccw(p2, q2, p1);
    int o4 = ccw(p2, q2, q1);

    // General case
    if (o1 != o2 && o3 != o4)
        return 1;

    // Special Cases for Collinear segments
    if (o1 == 0 && on_segment(p1, p2, q1)) return 1;
    if (o2 == 0 && on_segment(p1, q2, q1)) return 1;
    if (o3 == 0 && on_segment(p2, p1, q2)) return 1;
    if (o4 == 0 && on_segment(p2, q1, q2)) return 1;

    return 0; // No intersection found
}

// 1. Checks 2D overlapping rectangular bounding boxes with standoff paddings
int check_safety_overlaps(MachineInstance* machines, int machine_count, SafetyViolation* violations, int max_violations) {
    int violation_count = 0;
    for (int i = 0; i < machine_count; i++) {
        machines[i].safety_violation = 0;
    }

    for (int i = 0; i < machine_count; i++) {
        for (int j = i + 1; j < machine_count; j++) {
            MachineInstance m1 = machines[i];
            MachineInstance m2 = machines[j];

            // Expand machine 1 bounding box by its safety standoff margin
            double m1_min_x = m1.x - (m1.width / 2.0) - m1.safety_standoff;
            double m1_max_x = m1.x + (m1.width / 2.0) + m1.safety_standoff;
            double m1_min_y = m1.y - (m1.height / 2.0) - m1.safety_standoff;
            double m1_max_y = m1.y + (m1.height / 2.0) + m1.safety_standoff;

            // Expand machine 2 bounding box by its safety standoff margin
            double m2_min_x = m2.x - (m2.width / 2.0) - m2.safety_standoff;
            double m2_max_x = m2.x + (m2.width / 2.0) + m2.safety_standoff;
            double m2_min_y = m2.y - (m2.height / 2.0) - m2.safety_standoff;
            double m2_max_y = m2.y + (m2.height / 2.0) + m2.safety_standoff;

            // Perform bounding-box collision detection
            int overlap_x = (m1_min_x < m2_max_x) && (m1_max_x > m2_min_x);
            int overlap_y = (m1_min_y < m2_max_y) && (m1_max_y > m2_min_y);

            if (overlap_x && overlap_y) {
                machines[i].safety_violation = 1;
                machines[j].safety_violation = 1;

                if (violation_count < max_violations) {
                    strcpy(violations[violation_count].machine_id_1, m1.id);
                    strcpy(violations[violation_count].machine_id_2, m2.id);
                    violations[violation_count].overlap_distance = fabs(m1.x - m2.x);
                    sprintf(violations[violation_count].description, 
                            "Safety stand-off overlap between '%s' and '%s'", m1.name, m2.name);
                    violation_count++;
                }
            }
        }
    }
    return violation_count;
}

// 2. Checks intersections between human flow polyline segments and robot flow polylines
int check_flow_intersections(FlowPath* paths, int path_count, SafetyViolation* violations, int max_violations) {
    int violation_count = 0;

    for (int i = 0; i < path_count; i++) {
        for (int j = i + 1; j < path_count; j++) {
            FlowPath p1 = paths[i];
            FlowPath p2 = paths[j];

            // Verify if one path represents human activity and the other represents autonomous machinery
            int is_human_1 = (strcasecmp(p1.type, "human") == 0);
            int is_robot_2 = (strcasecmp(p2.type, "robot") == 0 || strcasecmp(p2.type, "autonomous") == 0);
            int is_human_2 = (strcasecmp(p2.type, "human") == 0);
            int is_robot_1 = (strcasecmp(p1.type, "robot") == 0 || strcasecmp(p1.type, "autonomous") == 0);

            if ((is_human_1 && is_robot_2) || (is_human_2 && is_robot_1)) {
                // Examine all polyline segments for mutual spatial crossings
                for (int s1 = 0; s1 < p1.point_count - 1; s1++) {
                    for (int s2 = 0; s2 < p2.point_count - 1; s2++) {
                        Point a1 = p1.points[s1];
                        Point b1 = p1.points[s1+1];
                        Point a2 = p2.points[s2];
                        Point b2 = p2.points[s2+1];

                        if (intersect_segments(a1, b1, a2, b2)) {
                            if (violation_count < max_violations) {
                                strcpy(violations[violation_count].machine_id_1, p1.id);
                                strcpy(violations[violation_count].machine_id_2, p2.id);
                                violations[violation_count].overlap_distance = 0.0;
                                sprintf(violations[violation_count].description, 
                                        "Unprotected intersection: Human Flow Path (%s) and Robot Flow Path (%s)", p1.id, p2.id);
                                violation_count++;
                            }
                        }
                    }
                }
            }
        }
    }
    return violation_count;
}

// 3. Identifies the production bottleneck based on the lowest effective capacity
int calculate_bottlenecks(MachineInstance* machines, int machine_count, FlowPath* paths, int path_count) {
    if (machine_count == 0) return -1;

    double min_throughput = 9999999.0;
    int bottleneck_index = -1;

    for (int i = 0; i < machine_count; i++) {
        machines[i].is_bottleneck = 0;
        // Capacity = units/hour corrected by yield
        double throughput = machines[i].volume_per_hour * machines[i].yield_percentage;
        if (throughput < min_throughput) {
            min_throughput = throughput;
            bottleneck_index = i;
        }
    }

    if (bottleneck_index != -1) {
        machines[bottleneck_index].is_bottleneck = 1;
    }

    return bottleneck_index;
}

// 4. Verifies that heavy machines requiring crane access are placed within crane bounding boxes
int check_crane_requirements(MachineInstance* machines, int machine_count, CraneZone* cranes, int crane_count, SafetyViolation* violations, int max_violations) {
    int violation_count = 0;

    for (int i = 0; i < machine_count; i++) {
        if (machines[i].crane_required) {
            int inside_crane = 0;
            for (int j = 0; j < crane_count; j++) {
                CraneZone c = cranes[j];
                double cx1 = fmin(c.x1, c.x2);
                double cx2 = fmax(c.x1, c.x2);
                double cy1 = fmin(c.y1, c.y2);
                double cy2 = fmax(c.y1, c.y2);

                if (machines[i].x >= cx1 && machines[i].x <= cx2 &&
                    machines[i].y >= cy1 && machines[i].y <= cy2) {
                    inside_crane = 1;
                    break;
                }
            }

            if (!inside_crane) {
                machines[i].safety_violation = 1;
                if (violation_count < max_violations) {
                    strcpy(violations[violation_count].machine_id_1, machines[i].id);
                    strcpy(violations[violation_count].machine_id_2, "");
                    violations[violation_count].overlap_distance = 0.0;
                    sprintf(violations[violation_count].description, 
                            "Machine '%s' requires overhead crane but is not inside a Crane Zone bounding box", machines[i].name);
                    violation_count++;
                }
            }
        }
    }
    return violation_count;
}
