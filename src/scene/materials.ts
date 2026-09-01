// src/scene/materials.ts
import * as THREE from "three";

export const floorMaterial = new THREE.MeshStandardMaterial({
  color: 0x1f2937,
  roughness: 0.95,
  metalness: 0.05,
});

export const gridColor = 0x374151;

export const machineMaterial = new THREE.MeshStandardMaterial({
  color: 0x2563eb,
  roughness: 0.6,
  metalness: 0.15,
});

export const machineEdgeMaterial = new THREE.LineBasicMaterial({
  color: 0xdbeafe,
});

export const craneMaterial = new THREE.MeshBasicMaterial({
  color: 0xf59e0b,
  transparent: true,
  opacity: 0.2,
});

export const craneEdgeMaterial = new THREE.LineBasicMaterial({
  color: 0xfbbf24,
});

export const lightMaterial = new THREE.MeshStandardMaterial({
  color: 0xfef08a,
  emissive: 0xfff7ae,
  emissiveIntensity: 0.6,
});

export function conduitMaterialByType(utilityType: string): THREE.LineBasicMaterial {
  const lut: Record<string, number> = {
    electrical: 0xef4444,
    water: 0x3b82f6,
    drainage: 0x10b981,
    network: 0xa855f7,
    hvac: 0xf59e0b,
  };

  return new THREE.LineBasicMaterial({
    color: lut[utilityType] ?? 0x9ca3af,
  });
}

export const workflowMaterial = new THREE.LineBasicMaterial({
  color: 0xe5e7eb,
});

export const workflowPointMaterial = new THREE.MeshStandardMaterial({
  color: 0xffffff,
});
