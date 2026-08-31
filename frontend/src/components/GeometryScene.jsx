// 3D viewport for the validator dashboard.
//
// Parses an uploaded `.obj`, renders its meshes with a PBR matte "clay"
// material + edge highlight over a SketchUp-style reference grid, overlays
// per-object AABB boxes (green pass / red violation), and auto-fits the camera.
// A HUD overlay hosts 4 camera presets, independent Z+Y section clipping
// planes, and a bottom status bar fed by SceneStatsContext.
//
// Y-up throughout: report min/max map directly onto THREE.Box3 with no axis
// swap.

import { useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Edges, Html } from '@react-three/drei';
import * as THREE from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { computePerObjectAABBs, colorForBox } from '../lib/obj.js';
import {
  CLAY_COLOR,
  EDGE_COLOR,
  CLAY_ROUGHNESS,
  CLAY_METALNESS,
  CAMERA_LERP_FACTOR,
  CAMERA_PRESETS,
  cameraPresetPosition,
  buildClippingPlanes,
  countMeshStats,
} from '../lib/viewport.js';
import {
  SceneStatsProvider,
  useSceneStats,
  SceneStatsBar,
} from '../contexts/SceneStatsContext.jsx';

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
    color: CLAY_COLOR,
    roughness: CLAY_ROUGHNESS,
    metalness: CLAY_METALNESS,
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

function Model({ group, boxes, fitBox, report }) {
  const { setStats } = useSceneStats();

  // Edge highlight: one EdgesGeometry + LineBasicMaterial overlay per mesh,
  // rendered after the clay body (renderOrder 1) in the architectural style.
  const edgeLines = useMemo(() => {
    group.updateMatrixWorld(true);
    const lines = [];
    group.traverse((mesh) => {
      if (!mesh.isMesh) return;
      lines.push({
        key: mesh.uuid,
        geometry: new THREE.EdgesGeometry(mesh.geometry),
        position: mesh.getWorldPosition(new THREE.Vector3()),
        quaternion: mesh.getWorldQuaternion(new THREE.Quaternion()),
        scale: mesh.getWorldScale(new THREE.Vector3()),
      });
    });
    return lines;
  }, [group]);

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

  const gridY = useMemo(() => (fitBox ? fitBox.min.y - 0.01 : -0.01), [fitBox]);

  // Explicit setStats on geometry load — no implicit ref-to-state sync. When
  // there is no geometry (zero meshes) we deliberately skip setStats so the
  // HUD keeps its "—" empty state instead of showing "0".
  useEffect(() => {
    const { triangles, objects } = countMeshStats(group);
    if (objects === 0) return;
    const start = performance.now();
    new THREE.Box3().setFromObject(group);
    const aabbMs = performance.now() - start;
    setStats({ triangles, objects, aabbMs });
  }, [group, setStats]);

  return (
    <>
      <primitive object={group} />
      {edgeLines.map((line) => (
        <lineSegments
          key={line.key}
          geometry={line.geometry}
          position={line.position}
          quaternion={line.quaternion}
          scale={line.scale}
          renderOrder={1}
        >
          <lineBasicMaterial color={EDGE_COLOR} />
        </lineSegments>
      ))}
      {overlays.map((overlay) => (
        <Edges
          key={overlay.key}
          geometry={overlay.geometry}
          position={overlay.position}
          color={overlay.color}
          lineWidth={2}
        />
      ))}
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

function ViewportControls({ group, center, maxDim }) {
  const { camera, controls, gl } = useThree();
  const [clipZ, setClipZ] = useState(false);
  const [clipY, setClipY] = useState(false);
  const [zConstant, setZConstant] = useState(0);
  const [yConstant, setYConstant] = useState(0);
  const [activePreset, setActivePreset] = useState(null);
  const presetTarget = useRef(null);

  const zPlane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, 0, 1), zConstant), [zConstant]);
  const yPlane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, 1, 0), yConstant), [yConstant]);

  const clipPlanes = useMemo(
    () => buildClippingPlanes({ clipZ, clipY, zPlane, yPlane }),
    [clipZ, clipY, zPlane, yPlane],
  );

  // Three.js clips per-material, not per-scene: enable local clipping and
  // assign the concatenated plane array to every mesh material.
  useEffect(() => {
    gl.localClippingEnabled = true;
    group.traverse((obj) => {
      if (!obj.isMesh) return;
      const material = obj.material;
      if (!material) return;
      material.clipping = clipPlanes.length > 0;
      material.clippingPlanes = clipPlanes;
      material.clipShadows = clipPlanes.length > 0;
      material.needsUpdate = true;
    });
  }, [gl, group, clipPlanes]);

  function selectPreset(presetId) {
    setActivePreset(presetId);
    presetTarget.current = cameraPresetPosition(presetId, center, maxDim);
  }

  // Smooth camera transition toward the selected preset (lerp per frame).
  useFrame(() => {
    if (!presetTarget.current) return;
    camera.position.lerp(presetTarget.current, CAMERA_LERP_FACTOR);
    if (controls) {
      controls.target.lerp(center, CAMERA_LERP_FACTOR);
      controls.update();
    }
  });

  return (
    <Html fullscreen pointerEvents="none">
      <div className="viewport-hud">
        <div className="camera-presets">
          {CAMERA_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className={`preset-button${activePreset === preset.id ? ' active' : ''}`}
              style={{ pointerEvents: 'auto' }}
              aria-pressed={activePreset === preset.id}
              onClick={() => selectPreset(preset.id)}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <div className="clip-controls" style={{ pointerEvents: 'auto' }}>
          <label className="clip-toggle">
            <input
              type="checkbox"
              checked={clipZ}
              onChange={(event) => setClipZ(event.target.checked)}
            />
            Z clip
          </label>
          <label className="clip-toggle">
            <input
              type="checkbox"
              checked={clipY}
              onChange={(event) => setClipY(event.target.checked)}
            />
            Y clip
          </label>
          <label className="clip-slider">
            Z cut
            <input
              type="range"
              min={-maxDim}
              max={maxDim}
              step={0.1}
              value={zConstant}
              onChange={(event) => setZConstant(Number(event.target.value))}
            />
          </label>
          <label className="clip-slider">
            Y cut
            <input
              type="range"
              min={-maxDim}
              max={maxDim}
              step={0.1}
              value={yConstant}
              onChange={(event) => setYConstant(Number(event.target.value))}
            />
          </label>
        </div>

        <SceneStatsBar />
      </div>
    </Html>
  );
}

function SceneRoot({ objText, report }) {
  const group = useMemo(() => parseObj(objText), [objText]);
  const boxes = useMemo(() => computePerObjectAABBs(objText, report), [objText, report]);
  const fitBox = useMemo(
    () => reportToBox3(report) ?? new THREE.Box3().setFromObject(group),
    [report, group],
  );
  const center = useMemo(() => fitBox.getCenter(new THREE.Vector3()), [fitBox]);
  const maxDim = useMemo(() => {
    const size = fitBox.getSize(new THREE.Vector3());
    const m = Math.max(size.x, size.y, size.z);
    return Number.isFinite(m) && m > 0 ? m : 1;
  }, [fitBox]);

  return (
    <>
      <Model group={group} boxes={boxes} fitBox={fitBox} report={report} />
      <ViewportControls group={group} center={center} maxDim={maxDim} />
      <CameraFit box={fitBox} />
    </>
  );
}

export default function GeometryScene({ objText, report }) {
  return (
    <SceneStatsProvider>
      <Canvas
        camera={{ position: [10, 8, 10], fov: 45, near: 0.1, far: 10000 }}
        gl={{ antialias: true }}
      >
        <color attach="background" args={['#0b0f19']} />
        <ambientLight intensity={0.7} />
        <directionalLight position={[10, 20, 5]} intensity={1.2} />
        <SceneRoot objText={objText} report={report} />
        <OrbitControls makeDefault enableDamping dampingFactor={0.1} />
      </Canvas>
    </SceneStatsProvider>
  );
}
