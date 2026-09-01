// src/scene/objectFactory.ts
import * as THREE from "three";
import type {
  CraneSceneObject,
  ConduitSceneObject,
  LightingSceneObject,
  MachineSceneObject,
  WorkflowPathSceneObject,
} from "../types/scene";
import {
  machineMaterial,
  machineEdgeMaterial,
  craneMaterial,
  craneEdgeMaterial,
  lightMaterial,
  conduitMaterialByType,
  workflowMaterial,
  workflowPointMaterial,
} from "./materials";

function attachUserData(obj: THREE.Object3D, data: Record<string, unknown>) {
  obj.userData = {
    ...(obj.userData ?? {}),
    ...data,
  };
}

export function createMachineObject(machine: MachineSceneObject): THREE.Group {
  const group = new THREE.Group();
  group.name = machine.id;

  const box = new THREE.BoxGeometry(machine.width, machine.height, machine.depth);
  const mesh = new THREE.Mesh(box, machineMaterial);
  mesh.position.set(machine.x, machine.height / 2, machine.y);

  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(box),
    machineEdgeMaterial
  );
  edges.position.copy(mesh.position);

  attachUserData(mesh, {
    object_type: "machine",
    object_id: machine.id,
  });
  attachUserData(edges, {
    object_type: "machine",
    object_id: machine.id,
  });

  group.add(mesh);
  group.add(edges);

  return group;
}

export function createLightingObject(light: LightingSceneObject): THREE.Group {
  const group = new THREE.Group();
  group.name = light.id;

  const sphere = new THREE.Mesh(
    new THREE.SphereGeometry(1.2, 12, 12),
    lightMaterial
  );
  sphere.position.set(light.x, light.z, light.y);

  attachUserData(sphere, {
    object_type: "lighting",
    object_id: light.id,
  });

  group.add(sphere);
  return group;
}

export function createCraneObject(crane: CraneSceneObject): THREE.Group {
  const group = new THREE.Group();
  group.name = crane.id;

  const geom = new THREE.BoxGeometry(
    Math.max(crane.width, 0.1),
    Math.max(crane.height, 0.1),
    Math.max(crane.depth, 0.1)
  );

  const mesh = new THREE.Mesh(geom, craneMaterial);
  mesh.position.set(crane.x, crane.z, crane.y);

  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(geom),
    craneEdgeMaterial
  );
  edges.position.copy(mesh.position);

  attachUserData(mesh, {
    object_type: "crane",
    object_id: crane.id,
  });
  attachUserData(edges, {
    object_type: "crane",
    object_id: crane.id,
  });

  group.add(mesh);
  group.add(edges);
  return group;
}

export function createConduitObject(conduit: ConduitSceneObject): THREE.Group {
  const group = new THREE.Group();
  group.name = conduit.id;

  if (!conduit.points || conduit.points.length < 2) {
    return group;
  }

  const pts = conduit.points.map(
    (p) => new THREE.Vector3(p.x, p.z, p.y)
  );
  const geom = new THREE.BufferGeometry().setFromPoints(pts);
  const line = new THREE.Line(
    geom,
    conduitMaterialByType(conduit.metadata.utility_type)
  );

  attachUserData(line, {
    object_type: "conduit",
    object_id: conduit.id,
  });

  group.add(line);

  conduit.points.forEach((p, idx) => {
    const pointMesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.6, 8, 8),
      new THREE.MeshStandardMaterial({ color: 0xffffff })
    );
    pointMesh.position.set(p.x, p.z, p.y);

    attachUserData(pointMesh, {
      object_type: "conduit",
      object_id: conduit.id,
      sub_index: idx,
    });

    group.add(pointMesh);
  });

  return group;
}

export function createWorkflowObject(workflow: WorkflowPathSceneObject): THREE.Group {
  const group = new THREE.Group();
  group.name = workflow.id;

  if (!workflow.points || workflow.points.length < 2) {
    return group;
  }

  const pts = workflow.points.map(
    (p) => new THREE.Vector3(p.x, p.z, p.y)
  );
  const geom = new THREE.BufferGeometry().setFromPoints(pts);
  const line = new THREE.Line(geom, workflowMaterial);

  attachUserData(line, {
    object_type: "workflow_path",
    object_id: workflow.id,
  });

  group.add(line);

  workflow.points.forEach((p, idx) => {
    const pointMesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.8, 10, 10),
      workflowPointMaterial
    );
    pointMesh.position.set(p.x, p.z, p.y);

    attachUserData(pointMesh, {
      object_type: "workflow_path",
      object_id: workflow.id,
      sub_index: idx,
    });

    group.add(pointMesh);
  });

  return group;
}
