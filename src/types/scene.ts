// src/types/scene.ts

export type SceneViewMode = "2d" | "3d";

export interface SceneProject {
  designer_name: string;
  dwg_title: string;
  dwg_num: string;
  sheet_size: string;
}

export interface SceneFloor {
  width_ft: number;
  height_ft: number;
  path_width_ft: number;
}

export interface SceneDisplay {
  view_mode: SceneViewMode;
  renderer: string;
  show_machines: boolean;
  show_lighting: boolean;
  show_cranes: boolean;
  show_workflow: boolean;
  show_electrical: boolean;
  show_safety: boolean;
  show_contour: boolean;
  show_decibel: boolean;
  show_grid: boolean;
  show_labels: boolean;
  snap_enabled: boolean;
  snap_ft: number;
  tool_mode: string;
}

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface SceneCamera {
  position: Vec3;
  target: Vec3;
  projection: "orthographic" | "perspective";
}

export interface SceneSelection {
  selected_object_type: string;
  selected_object_id: string;
  selected_sub_index: number;
  selection_revision: number;
}

export interface SceneCounts {
  machines: number;
  lighting: number;
  conduits: number;
  cranes: number;
  machine_flows: number;
}

export interface MachineSceneObject {
  id: string;
  object_type: "machine";
  label: string;
  x: number;
  y: number;
  z: number;
  width: number;
  depth: number;
  height: number;
  rotation_deg: number;
  standoff: number;
  metadata: {
    make: string;
    model: string;
    type: string;
    volume: number;
    yield_pct: number;
    crane_required: boolean;
    decibel: number;
    human_intervention_required: boolean;
    preferred_utility_zone: string;
    process_family: string;
    value_added_primary: boolean;
    water_hookup: boolean;
    vapor_port: string;
    amperage: number;
    wattage: number;
    tool_heads: number;
  };
  raw: Record<string, unknown>;
}

export interface LightingSceneObject {
  id: string;
  object_type: "lighting";
  label: string;
  x: number;
  y: number;
  z: number;
  width: number;
  depth: number;
  height: number;
  metadata: {
    make: string;
    brand: string;
    type: string;
    wattage: number;
    kelvin: number;
    lumens: number;
    lux_target: number;
    dimmable: boolean;
  };
  raw: Record<string, unknown>;
}

export interface CraneSceneObject {
  id: string;
  object_type: "crane";
  label: string;
  ll_x: number;
  ll_y: number;
  ur_x: number;
  ur_y: number;
  x: number;
  y: number;
  z: number;
  width: number;
  depth: number;
  height: number;
  metadata: {
    make: string;
    model: string;
    max_lift_weight: number;
    max_lift_speed: number;
    max_transversal_speed: number;
    amperage: number;
    wattage: number;
  };
  raw: Record<string, unknown>;
}

export interface ConduitPoint {
  x: number;
  y: number;
  z: number;
}

export interface ConduitSceneObject {
  id: string;
  object_type: "conduit";
  label: string;
  points: ConduitPoint[];
  metadata: {
    label: string;
    utility_type: string;
    depth_in: number;
    warning_tape: boolean;
    dim_visible: boolean;
  };
  raw: Record<string, unknown>;
}

export interface WorkflowPathPoint {
  index: number;
  x: number;
  y: number;
  z: number;
  standoff: number;
  speed: number;
}

export interface WorkflowPathSceneObject {
  id: string;
  object_type: "workflow_path";
  label: string;
  points: WorkflowPathPoint[];
  metadata: {
    movement_mode: string;
    path_width_ft: number;
    workflow_dim_visible: boolean;
    workflow_dim_show_length: boolean;
    workflow_dim_show_metadata: boolean;
  };
  raw: Record<string, unknown>;
}

export interface MachineFlowSceneObject {
  id: string;
  object_type: "machine_flow";
  label: string;
  from_machine_id: string;
  to_machine_id: string;
  metadata: {
    part_family: string;
    process_step_order: number;
    flow_rate_per_hr: number;
    transfer_mode: string;
    lot_size: number;
    buffer_max_units: number;
    value_added_step: boolean;
    mandatory_adjacency: boolean;
    preferred_max_distance_ft: number;
    notes: string;
  };
  raw: Record<string, unknown>;
}

export interface SceneObjects {
  machines: MachineSceneObject[];
  lighting: LightingSceneObject[];
  conduits: ConduitSceneObject[];
  cranes: CraneSceneObject[];
  workflow_paths: WorkflowPathSceneObject[];
  machine_flows: MachineFlowSceneObject[];
}

export interface ScenePayload {
  schema_version: string;
  scene_revision: number;
  project: SceneProject;
  floor: SceneFloor;
  display: SceneDisplay;
  camera: SceneCamera;
  selection: SceneSelection;
  objects: SceneObjects;
  counts: SceneCounts;
}
