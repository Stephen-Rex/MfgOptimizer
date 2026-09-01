// src/renderers/render3d.ts
import * as THREE from "three";
import type { ScenePayload } from "../types/scene";
import { buildSceneFromPayload } from "../scene/sceneBuilder";

export interface RendererHandle {
  dispose: () => void;
}

export function render3DScene(
  container: HTMLDivElement,
  scenePayload: ScenePayload
): RendererHandle {
  const width = container.clientWidth || 900;
  const height = container.clientHeight || 600;

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio);
  container.innerHTML = "";
  container.appendChild(renderer.domElement);

  const { scene } = buildSceneFromPayload(scenePayload);

  const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 5000);

  const floorW = scenePayload.floor.width_ft;
  const floorH = scenePayload.floor.height_ft;

  camera.position.set(
    floorW * 0.9,
    Math.max(floorW, floorH) * 0.9,
    floorH * 0.9
  );
  camera.lookAt(new THREE.Vector3(floorW / 2, 0, floorH / 2));

  let animationId = 0;

  const animate = () => {
    animationId = window.requestAnimationFrame(animate);
    renderer.render(scene, camera);
  };

  animate();

  const onResize = () => {
    const w = container.clientWidth || 900;
    const h = container.clientHeight || 600;

    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  };

  window.addEventListener("resize", onResize);

  return {
    dispose: () => {
      window.cancelAnimationFrame(animationId);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      container.innerHTML = "";
    },
  };
}
