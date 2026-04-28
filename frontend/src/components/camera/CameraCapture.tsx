"use client";
import { useCallback, useEffect, useRef, useState } from "react";

interface Props {
  onCapture: (file: File) => void;
  onCancel?: () => void;
}

type Mode = "idle" | "camera" | "preview";

export function CameraCapture({ onCapture, onCancel }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<Mode>("idle");
  const [facingMode, setFacingMode] = useState<"environment" | "user">("environment");
  const [preview, setPreview] = useState<string | null>(null);
  const [capturedFile, setCapturedFile] = useState<File | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const startCamera = useCallback(async (facing: "environment" | "user") => {
    stopStream();
    setCameraError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facing, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setMode("camera");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("NotAllowedError") || msg.includes("Permission")) {
        setCameraError("Доступ к камере запрещён. Используйте загрузку файла.");
      } else {
        setCameraError("Камера недоступна. Используйте загрузку файла.");
      }
    }
  }, [stopStream]);

  const snap = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const ts = new Date().toISOString().replace(/[:.]/g, "-");
      const file = new File([blob], `photo-${ts}.jpg`, { type: "image/jpeg" });
      const url = URL.createObjectURL(blob);
      setPreview(url);
      setCapturedFile(file);
      stopStream();
      setMode("preview");
    }, "image/jpeg", 0.88);
  }, [stopStream]);

  const flipCamera = useCallback(() => {
    const next = facingMode === "environment" ? "user" : "environment";
    setFacingMode(next);
    startCamera(next);
  }, [facingMode, startCamera]);

  const retake = useCallback(() => {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setCapturedFile(null);
    startCamera(facingMode);
  }, [preview, facingMode, startCamera]);

  const confirmCapture = useCallback(() => {
    if (capturedFile) {
      onCapture(capturedFile);
      if (preview) URL.revokeObjectURL(preview);
      setPreview(null);
      setCapturedFile(null);
      setMode("idle");
    }
  }, [capturedFile, preview, onCapture]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    files.forEach((f) => onCapture(f));
    if (e.target) e.target.value = "";
  };

  useEffect(() => () => { stopStream(); }, [stopStream]);

  const hasCameraSupport =
    typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

  if (mode === "preview" && preview) {
    return (
      <div className="space-y-3">
        <div className="relative rounded-xl overflow-hidden bg-black">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview} alt="Предпросмотр" className="w-full object-contain max-h-72" />
        </div>
        <div className="flex gap-2">
          <button
            onClick={retake}
            className="flex-1 rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
          >
            Переснять
          </button>
          <button
            onClick={confirmCapture}
            className="flex-1 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Использовать фото
          </button>
        </div>
      </div>
    );
  }

  if (mode === "camera") {
    return (
      <div className="space-y-3">
        <div className="relative rounded-xl overflow-hidden bg-black">
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full object-contain max-h-72"
          />
          <canvas ref={canvasRef} className="hidden" />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { stopStream(); setMode("idle"); onCancel?.(); }}
            className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
          >
            Отмена
          </button>
          {/* flip camera button — only on mobile with rear/front */}
          <button
            onClick={flipCamera}
            className="rounded-md border px-3 py-2 text-sm hover:bg-accent transition-colors"
            title="Переключить камеру"
          >
            🔄
          </button>
          <button
            onClick={snap}
            className="flex-1 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            📸 Сфотографировать
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {cameraError && (
        <div className="rounded-lg bg-yellow-50 border border-yellow-200 px-3 py-2 text-xs text-yellow-800">
          {cameraError}
        </div>
      )}

      <div className="rounded-lg border-2 border-dashed border-border p-6 text-center space-y-3">
        <div className="text-4xl">📷</div>
        <p className="text-sm text-muted-foreground">Сфотографируйте конструкцию или загрузите фото</p>

        <div className="flex gap-2 justify-center flex-wrap">
          {hasCameraSupport && (
            <button
              onClick={() => startCamera(facingMode)}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              📷 Открыть камеру
            </button>
          )}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
          >
            Загрузить файл
          </button>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={handleFileInput}
        />

        <p className="text-xs text-muted-foreground">
          JPEG, PNG до 20 МБ. Используйте калибровочную карточку ArUco для точных измерений.
        </p>
      </div>

      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
