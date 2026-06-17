import { useRef, useState } from "react";
import type { CropBox } from "../types";

/**
 * Mostra il master con il box di crop sovrapposto e ne consente il trascinamento (RF-7).
 * Il box mantiene dimensioni fisse (la finestra di crop dell'aspect ratio target):
 * l'utente lo sposta per scegliere quale parte includere. Coordinate in pixel del master.
 */
export default function CropBoxOverlay({
  src,
  masterW,
  masterH,
  box,
  onChange,
  maxWidth = 520,
}: {
  src: string;
  masterW: number;
  masterH: number;
  box: CropBox;
  onChange: (b: CropBox) => void;
  maxWidth?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const dragging = useRef<{ startX: number; startY: number; bx: number; by: number } | null>(null);
  const [hover, setHover] = useState(false);

  const dispW = Math.min(maxWidth, masterW);
  const scale = dispW / masterW;
  const dispH = masterH * scale;

  function onPointerDown(e: React.PointerEvent) {
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    dragging.current = { startX: e.clientX, startY: e.clientY, bx: box.x, by: box.y };
  }
  function onPointerMove(e: React.PointerEvent) {
    if (!dragging.current) return;
    const dx = (e.clientX - dragging.current.startX) / scale;
    const dy = (e.clientY - dragging.current.startY) / scale;
    let nx = Math.round(dragging.current.bx + dx);
    let ny = Math.round(dragging.current.by + dy);
    nx = Math.max(0, Math.min(nx, masterW - box.w));
    ny = Math.max(0, Math.min(ny, masterH - box.h));
    onChange({ ...box, x: nx, y: ny });
  }
  function onPointerUp(e: React.PointerEvent) {
    (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    dragging.current = null;
  }

  return (
    <div
      ref={ref}
      style={{ position: "relative", width: dispW, height: dispH, userSelect: "none", touchAction: "none" }}
    >
      <img src={src} alt="master" style={{ width: dispW, height: dispH, display: "block", borderRadius: 8 }} />
      {/* velo scuro fuori dal box */}
      <svg
        width={dispW}
        height={dispH}
        style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
      >
        <defs>
          <mask id="hole">
            <rect width={dispW} height={dispH} fill="white" />
            <rect x={box.x * scale} y={box.y * scale} width={box.w * scale} height={box.h * scale} fill="black" />
          </mask>
        </defs>
        <rect width={dispW} height={dispH} fill="rgba(10,15,25,0.5)" mask="url(#hole)" />
        <rect
          x={box.x * scale}
          y={box.y * scale}
          width={box.w * scale}
          height={box.h * scale}
          fill="none"
          stroke={hover ? "#5b8cff" : "#2f6df0"}
          strokeWidth={2}
        />
      </svg>
      {/* area trascinabile sopra il box */}
      <div
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        style={{
          position: "absolute",
          left: box.x * scale,
          top: box.y * scale,
          width: box.w * scale,
          height: box.h * scale,
          cursor: "grab",
        }}
        title="Trascina per spostare il ritaglio"
      />
    </div>
  );
}
