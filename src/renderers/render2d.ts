// src/renderers/render2d.ts
import * as THREE from "three";
import type { ScenePayload } from "../types/scene";
import { buildSceneFromPayload } from "../scene/sceneBuilder";

export interface RendererHandle {
  dispose: () => void;
}

export function render2DScene(
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

  const floorW = scenePayload.floor.width_ft;
  const floorH = scenePayload.floor.height_ft;
  const aspect = width / height;
  const frustumSize = Math.max(floorW, floorH) * 1.15;

  const camera = new THREE.OrthographicCamera(
    (-frustumSize * aspect) / 2,
    (frustumSize * aspect) / 2,
    frustumSize / 2,
    -frustumSize / 2,
    0.1,
    2000
  );

  camera.position.set(floorW / 2, 300, floorH / 2);
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
    const newAspect = w / h;

    camera.left = (-frustumSize * newAspect) / 2;
    camera.right = (frustumSize * newAspect) / 2;
    camera.top = frustumSize / 2;
    camera.bottom = -frustumSize / 2;
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
