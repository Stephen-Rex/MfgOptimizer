// src/bridge/streamlitBridge.ts

import type { FrontendEventPayload } from "../types/events";
import type { ScenePayload } from "../types/scene";

declare global {
  interface Window {
    Streamlit?: {
      setComponentValue: (value: unknown) => void;
      setFrameHeight: (height?: number) => void;
      RENDER_EVENT?: string;
      events?: {
        addEventListener: (
          eventName: string,
          callback: (event: CustomEvent) => void
        ) => void;
      };
    };
    __STREAMLIT_PROPS__?: unknown;
  }
}

export interface StreamlitRenderDetail {
  args?: {
    scene_payload?: ScenePayload;
    component_key?: string;
    height_px?: number;
    show_debug?: boolean;
  };
}

export function isStreamlitAvailable(): boolean {
  return typeof window !== "undefined" && !!window.Streamlit;
}

export function setFrameHeight(height?: number): void {
  if (isStreamlitAvailable()) {
    window.Streamlit?.setFrameHeight(height);
  }
}

export function sendEventToStreamlit(eventPayload: FrontendEventPayload): void {
  if (isStreamlitAvailable()) {
    window.Streamlit?.setComponentValue({
      component_ready: true,
      event_available: true,
      event_payload: eventPayload,
      status: "ok",
    });
  } else {
    // Dev fallback
    console.debug("Streamlit bridge event:", eventPayload);
  }
}

export function sendNoopReady(): void {
  if (isStreamlitAvailable()) {
    window.Streamlit?.setComponentValue({
      component_ready: true,
      event_available: false,
      event_payload: null,
      status: "ready",
    });
  }
}

export function readInitialProps(): {
  scene_payload: ScenePayload | null;
  component_key: string;
  height_px: number;
  show_debug: boolean;
} {
  const rawProps = (window.__STREAMLIT_PROPS__ ?? {}) as StreamlitRenderDetail;
  const args = rawProps.args ?? {};

  return {
    scene_payload: (args.scene_payload as ScenePayload) ?? null,
    component_key: String(args.component_key ?? "threejs_canvas"),
    height_px: Number(args.height_px ?? 700),
    show_debug: Boolean(args.show_debug ?? false),
  };
}

export function registerStreamlitRenderListener(
  callback: (detail: StreamlitRenderDetail) => void
): void {
  if (
    typeof window !== "undefined" &&
    window.Streamlit?.events &&
    window.Streamlit?.RENDER_EVENT
  ) {
    window.Streamlit.events.addEventListener(
      window.Streamlit.RENDER_EVENT,
      (event: CustomEvent) => {
        callback((event.detail ?? {}) as StreamlitRenderDetail);
      }
    );
  }
}
