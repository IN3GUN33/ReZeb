"use client";
import { useEffect, useRef } from "react";
import type { Defect } from "@/types";

interface Props {
  photoUrl: string;
  defects: Defect[];
  width?: number;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#dc2626",
  significant: "#ea580c",
  acceptable: "#16a34a",
};

export function DefectPhotoCanvas({ photoUrl, defects, width = 640 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      const scale = width / img.naturalWidth;
      const h = img.naturalHeight * scale;
      canvas.width = width;
      canvas.height = h;
      ctx.drawImage(img, 0, 0, width, h);

      defects.forEach((defect) => {
        if (!defect.bbox || defect.bbox.length < 4) return;
        const [x1, y1, x2, y2] = defect.bbox;
        const color = SEVERITY_COLORS[defect.severity] ?? "#6b7280";

        const bx = x1 * width;
        const by = y1 * h;
        const bw = (x2 - x1) * width;
        const bh = (y2 - y1) * h;

        // Box
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(bx, by, bw, bh);

        // Background for label
        const label = `${defect.defect_type.replace(/_/g, " ")} ${Math.round(defect.confidence * 100)}%`;
        ctx.font = "bold 12px sans-serif";
        const textWidth = ctx.measureText(label).width;
        ctx.fillStyle = color;
        ctx.fillRect(bx, by - 18, textWidth + 8, 18);

        // Label text
        ctx.fillStyle = "#ffffff";
        ctx.fillText(label, bx + 4, by - 4);
      });
    };
    img.onerror = () => {
      // Photo load failed (CORS / presigned URL expired) — draw placeholder
      canvas.width = width;
      canvas.height = Math.round(width * 0.56);
      ctx.fillStyle = "#f3f4f6";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#9ca3af";
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Фото недоступно", canvas.width / 2, canvas.height / 2);
    };
    img.src = photoUrl;
  }, [photoUrl, defects, width]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full rounded-lg border"
      style={{ maxWidth: width }}
    />
  );
}
