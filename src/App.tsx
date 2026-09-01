// src/App.tsx

import React, { useEffect, useMemo, useState } from "react";
import {
  readInitialProps,
  registerStreamlitRenderListener,
  sendEventToStreamlit,
  sendNoopReady,
  setFrameHeight,
} from "./bridge/streamlitBridge";
import type { ScenePayload } from "./types/scene";
import type { FrontendEventPayload } from "./types/events";

function safeSceneSummary(scene: ScenePayload | null) {
  if (!scene) {
    return {
      projectLabel: "No scene payload",
      viewMode: "2d",
      machines: 0,
      conduits: 0,
      cranes: 0,
      machineFlows: 0,
    };
  }

  return {
    projectLabel: `${scene.project.dwg_num} — ${scene.project.dwg_title}`,
    viewMode: scene.display.view_mode,
    machines: scene.counts.machines,
    conduits: scene.counts.conduits,
    cranes: scene.counts.cranes,
    machineFlows: scene.counts.machine_flows,
  };
}

export default function App() {
  const initial = useMemo(() => readInitialProps(), []);
  const [scene, setScene] = useState<ScenePayload | null>(initial.scene_payload);
  const [heightPx, setHeightPx] = useState<number>(initial.height_px);
  const [showDebug, setShowDebug] = useState<boolean>(initial.show_debug);
  const [componentKey, setComponentKey] = useState<string>(initial.component_key);
  const [lastEventId, setLastEventId] = useState<number>(0);

  useEffect(() => {
    registerStreamlitRenderListener((detail) => {
      const args = detail.args ?? {};
      if (args.scene_payload) {
        setScene(args.scene_payload as ScenePayload);
      }
      if (typeof args.height_px !== "undefined") {
        setHeightPx(Number(args.height_px));
      }
      if (typeof args.show_debug !== "undefined") {
        setShowDebug(Boolean(args.show_debug));
      }
      if (typeof args.component_key !== "undefined") {
        setComponentKey(String(args.component_key));
      }
    });
  }, []);

  useEffect(() => {
    sendNoopReady();
    setFrameHeight(heightPx + 80);
  }, [heightPx]);

  const summary = safeSceneSummary(scene);

  const emitSelectFirstMachine = () => {
    if (!scene || scene.objects.machines.length === 0) return;

    const first = scene.objects.machines[0];
    const eventPayload: FrontendEventPayload = {
      event_id: lastEventId + 1,
      event_type: "select_object",
      view_mode: scene.display.view_mode,
      object_type: "machine",
      object_id: first.id,
      payload: {},
    };

    setLastEventId(eventPayload.event_id);
    sendEventToStreamlit(eventPayload);
  };

  return (
    <div
      style={{
        width: "100%",
        minHeight: `${heightPx}px`,
        boxSizing: "border-box",
        padding: "12px",
        background: "#111827",
        color: "#E5E7EB",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <div
        style={{
          border: "1px solid #374151",
          borderRadius: "8px",
          padding: "16px",
          background: "#0F172A",
        }}
      >
        <h2 style={{ marginTop: 0 }}>Three.js Frontend Starter</h2>
        <p style={{ marginBottom: "8px" }}>
          Component Key: <strong>{componentKey}</strong>
        </p>
        <p style={{ marginBottom: "8px" }}>
          Project: <strong>{summary.projectLabel}</strong>
        </p>
        <p style={{ marginBottom: "8px" }}>
          View Mode: <strong>{summary.viewMode}</strong>
        </p>
        <p style={{ marginBottom: "8px" }}>
          Machines: <strong>{summary.machines}</strong> | Conduits:{" "}
          <strong>{summary.conduits}</strong> | Cranes:{" "}
          <strong>{summary.cranes}</strong> | Machine Flows:{" "}
          <strong>{summary.machineFlows}</strong>
        </p>

        <div
          style={{
            marginTop: "16px",
            padding: "16px",
            minHeight: `${Math.max(300, heightPx - 180)}px`,
            border: "1px dashed #4B5563",
            borderRadius: "8px",
            background: "#1F2937",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center",
          }}
        >
          <div>
            <h3 style={{ marginTop: 0 }}>Render Surface Placeholder</h3>
            <p>
              This is the starter frontend shell. Replace this area next with the
              real Three.js scene renderer for 2D and 3D modes.
            </p>
            <button
              type="button"
              onClick={emitSelectFirstMachine}
              style={{
                marginTop: "12px",
                padding: "10px 16px",
                borderRadius: "6px",
                border: "none",
                background: "#2563EB",
                color: "white",
                cursor: "pointer",
              }}
            >
              Test: Select First Machine
            </button>
          </div>
        </div>

        {showDebug && (
          <details style={{ marginTop: "16px" }}>
            <summary>Scene Payload Debug</summary>
            <pre
              style={{
                marginTop: "12px",
                maxHeight: "300px",
                overflow: "auto",
                background: "#020617",
                padding: "12px",
                borderRadius: "6px",
                fontSize: "12px",
              }}
            >
              {JSON.stringify(scene, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}
