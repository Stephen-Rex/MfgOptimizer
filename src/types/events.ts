// src/types/events.ts

export type FrontendEventType =
  | "select_object"
  | "move_machine"
  | "move_light"
  | "update_crane_box"
  | "update_conduit_vertex"
  | "update_workflow_point"
  | "set_tool_mode"
  | "set_view_mode"
  | "set_camera_state"
  | "noop";

export interface FrontendEventPayload {
  event_id: number;
  event_type: FrontendEventType;
  view_mode: "2d" | "3d";
  object_type?: string;
  object_id?: string;
  payload: Record<string, unknown>;
}

export interface ComponentResultPayload {
  component_ready: boolean;
  event_available: boolean;
  event_payload: FrontendEventPayload | null;
  status: string;
}
