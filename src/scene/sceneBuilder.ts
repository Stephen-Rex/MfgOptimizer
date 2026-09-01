// src/scene/sceneBuilder.ts
import * as THREE from "three";
import type { ScenePayload } from "../types/scene";
import { floorMaterial, gridColor } from "./materials";
import {
  createMachineObject,
  createLightingObject,
  createCraneObject,
  createConduitObject,
  createWorkflowObject,
} from "./objectFactory";

export interface BuiltScene {
  scene: THREE.Scene;
  rootGroup: THREE.Group;
}

function addLights(scene: THREE.Scene) {
  const ambient = new THREE.AmbientLight(0xffffff, 0.7);
  scene.add(ambient);

  const directional = new THREE.DirectionalLight(0xffffff, 1.0);
  directional.position.set(100, 200, 100);
  scene.add(directional);
}

function addFloor(scene: THREE.Scene, widthFt: number, heightFt: number, showGrid: boolean) {
  const floorGeom = new THREE.PlaneGeometry(widthFt, heightFt);
  const floor = new THREE.Mesh(floorGeom, floorMaterial);
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(widthFt / 2, 0, heightFt / 2);
  scene.add(floor);

  if (showGrid) {
    const grid = new THREE.GridHelper(
      Math.max(widthFt, heightFt),
      Math.max(Math.floor(Math.max(widthFt, heightFt) / 10), 2),
      gridColor,
      gridColor
    );
    grid.position.set(widthFt / 2, 0.05, heightFt / 2);
    scene.add(grid);
  }
}

export function buildSceneFromPayload(scenePayload: ScenePayload): BuiltScene {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x111827);

  addLights(scene);
  addFloor(
    scene,
    scenePayload.floor.width_ft,
    scenePayload.floor.height_ft,
    scenePayload.display.show_grid
  );

  const rootGroup = new THREE.Group();
  rootGroup.name = "layout_root";

  if (scenePayload.display.show_machines) {
    scenePayload.objects.machines.forEach((m) => {
      rootGroup.add(createMachineObject(m));
    });
  }

  if (scenePayload.display.show_lighting) {
    scenePayload.objects.lighting.forEach((l) => {
      rootGroup.add(createLightingObject(l));
    });
  }

  if (scenePayload.display.show_cranes) {
    scenePayload.objects.cranes.forEach((cr) => {
      rootGroup.add(createCraneObject(cr));
    });
  }

  if (scenePayload.display.show_electrical) {
    scenePayload.objects.conduits.forEach((c) => {
      rootGroup.add(createConduitObject(c));
    });
  }

  if (scenePayload.display.show_workflow) {
    scenePayload.objects.workflow_paths.forEach((wf) => {
      rootGroup.add(createWorkflowObject(wf));
    });
  }

  scene.add(rootGroup);

  return {
    scene,
    rootGroup,
  };
}
