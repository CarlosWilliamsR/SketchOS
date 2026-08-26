// 3D viewport for the validator dashboard.
//
// Parses an uploaded `.obj`, renders its meshes over a SketchUp-style
// reference grid, overlays per-object AABB boxes (green pass / red violation),
// and auto-fits the camera to the model. Y-up throughout: report min/max map
// directly onto THREE.Box3 with no axis swap.

import { useEffect, useMemo } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, Edges } from '@react-three/drei';
import * as THREE from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { computePerObjectAABBs, colorForBox } from '../lib/obj.js';

const MESH_COLOR = '#cfd3d7';

function reportToBox3(report) {
  const a = report?.aabb;
  if (!a?.min || !a?.max) return null;
  return new THREE.Box3(
    new THREE.Vector3(a.min.x, a.min.y, a.min.z),
    new THREE.Vector3(a.max.x, a.max.y, a.max.z),
  );
}

function parseObj(text) {
  const loader = new OBJLoader();
  const group = loader.parse(text);
  const material = new THREE.MeshStandardMaterial({
    color: MESH_COLOR,
    roughness: 0.6,
    metalness: 0.0,
  });
  group.traverse((object) => {
    if (object.isMesh) object.material = material;
  });
  return group;
}

function CameraFit({ box }) {
  const camera = useThree((state) => state.camera);
  const controls = useThree((state) => state.controls);

  useEffect(() => {
    if (!box) return;
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    if (!Number.isFinite(maxDim) || maxDim < 1e-6) return;

    const fitDistance = (maxDim * 1.2) / (2 * Math.tan((camera.fov * Math.PI) / 360));
    const offset = new THREE.Vector3(1, 0.6, 1).normalize().multiplyScalar(fitDistance * 1.4);
    camera.position.copy(center).add(offset);
    camera.near = Math.max(0.001, fitDistance / 100);
    camera.far = fitDistance * 100;
    camera.updateProjectionMatrix();

    if (controls) {
      controls.target.copy(center);
      controls.update();
    }
  }, [box, camera, controls]);

  return null;
}

function Model({ objText, report }) {
  const group = useMemo(() => parseObj(objText), [objText]);
  const boxes = useMemo(() => computePerObjectAABBs(objText, report), [objText, report]);
  const fitBox = useMemo(
    () => reportToBox3(report) ?? new THREE.Box3().setFromObject(group),
    [report, group],
  );
  const gridY = useMemo(() => (fitBox ? fitBox.min.y - 0.01 : -0.01), [fitBox]);

  const overlays = useMemo(() => {
    const violating = new Set((report?.violations ?? []).map((v) => v.object));
    return boxes.map(({ name, box }) => {
      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());
      return {
        key: name ?? '__global__',
        geometry: new THREE.BoxGeometry(size.x, size.y, size.z),
        position: center,
        color: colorForBox(name, violating),
      };
    });
  }, [boxes, report]);

  return (
    <>
      <primitive object={group} />
      {overlays.map((overlay) => (
        <Edges
          key={overlay.key}
          geometry={overlay.geometry}
          position={overlay.position}
          color={overlay.color}
          lineWidth={2}
        />
      ))}
      <CameraFit box={fitBox} />
      <Grid
        position={[0, gridY, 0]}
        infiniteGrid
        cellSize={1}
        sectionSize={5}
        cellColor="#4a4d52"
        sectionColor="#2f3134"
        fadeDistance={80}
        fadeStrength={1}
      />
    </>
  );
}

export default function GeometryScene({ objText, report }) {
  return (
    <Canvas
      camera={{ position: [10, 8, 10], fov: 45, near: 0.1, far: 10000 }}
      gl={{ antialias: true }}
    >
      <color attach="background" args={['#0b0f19']} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[10, 20, 5]} intensity={1.2} />
      <Model objText={objText} report={report} />
      <OrbitControls makeDefault enableDamping dampingFactor={0.1} />
    </Canvas>
  );
}
