"use client";

import { useEffect, useRef } from "react";
import { useAgent } from "../../context/AgentContext.jsx";

const SKIN_URL = process.env.NEXT_PUBLIC_AGENT_SKIN_URL || "/agent/banker-skin.png";

const VIEWER_ZOOM = 0.9;
const VIEWER_FOV = 50;
const WALK_SPEED = 0.55;
const WALK_SPEED_THINKING = 0.65;
const RUN_SPEED_ALERT = 0.75;

function framePlayer(viewer) {
  if (!viewer || viewer.disposed) return;
  viewer.playerWrapper.position.set(0, -0.12, 0);
  viewer.playerWrapper.rotation.set(0, 0, 0);
  viewer.adjustCameraDistance();
}

function createWalkAnimation(WalkingAnimation, speed) {
  const walk = new WalkingAnimation();
  walk.headBobbing = true;
  walk.speed = speed;
  return walk;
}

function walkSpeedForState(avatarState) {
  if (avatarState === "thinking") return WALK_SPEED_THINKING;
  return WALK_SPEED;
}

export default function AgentAvatar({ className = "" }) {
  const canvasWrapRef = useRef(null);
  const canvasRef = useRef(null);
  const viewerRef = useRef(null);
  const { avatarState } = useAgent();

  useEffect(() => {
    const canvasWrap = canvasWrapRef.current;
    const canvas = canvasRef.current;
    if (!canvasWrap || !canvas) return;

    let viewer = null;
    let resizeObserver = null;
    let cancelled = false;

    (async () => {
      const { SkinViewer, WalkingAnimation } = await import("skinview3d");
      if (cancelled) return;

      const width = canvasWrap.clientWidth || 400;
      const height = canvasWrap.clientHeight || 400;

      viewer = new SkinViewer({
        canvas,
        width,
        height,
        skin: SKIN_URL,
        background: null,
        enableControls: false,
        zoom: VIEWER_ZOOM,
        fov: VIEWER_FOV,
      });
      viewer.autoRotate = false;
      viewer.animation = createWalkAnimation(WalkingAnimation, WALK_SPEED);
      framePlayer(viewer);
      viewerRef.current = viewer;

      resizeObserver = new ResizeObserver(() => {
        if (!viewer || viewer.disposed) return;
        const w = canvasWrap.clientWidth;
        const h = canvasWrap.clientHeight;
        if (w > 0 && h > 0) {
          viewer.setSize(w, h);
          framePlayer(viewer);
        }
      });
      resizeObserver.observe(canvasWrap);
    })();

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      if (viewer && !viewer.disposed) {
        viewer.dispose();
      }
      viewerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.disposed) return;

    let cancelled = false;
    (async () => {
      const { WalkingAnimation, RunningAnimation } = await import("skinview3d");
      if (cancelled || viewer.disposed) return;

      viewer.autoRotate = false;

      if (avatarState === "alert") {
        const run = new RunningAnimation();
        run.speed = RUN_SPEED_ALERT;
        viewer.animation = run;
      } else {
        viewer.animation = createWalkAnimation(
          WalkingAnimation,
          walkSpeedForState(avatarState)
        );
      }
      framePlayer(viewer);
    })();

    return () => {
      cancelled = true;
    };
  }, [avatarState]);

  return (
    <div className={`relative w-full ${className}`.trim()}>
      <div
        ref={canvasWrapRef}
        className="relative h-[min(500px,62vh)] min-h-[420px] w-full"
      >
        <canvas ref={canvasRef} className="block h-full w-full" />
      </div>
    </div>
  );
}
