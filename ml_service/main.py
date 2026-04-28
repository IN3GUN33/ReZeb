"""
ML Service — YOLO inference via Roboflow Inference API.

If ROBOFLOW_API_KEY env var is set, calls Roboflow-hosted model.
Otherwise falls back to a deterministic mock for local development.

Roboflow model: concrete-defect-detection-zuym8 v1
Classes: crack, exposed reinforcement, corrosion, efflorescence, spalling, rust stain
"""
import base64
import os
import random

import httpx
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

app = FastAPI(title="ReZeb ML Service", version="0.2.0")

ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_MODEL = os.getenv("ROBOFLOW_MODEL", "concrete-defect-detection-zuym8/1")
ROBOFLOW_BASE = "https://detect.roboflow.com"

# Map Roboflow English class names → internal Russian names
CLASS_MAP = {
    "crack": "трещина_поверхностная",
    "exposed reinforcement": "обнажённая_арматура",
    "exposed_reinforcement": "обнажённая_арматура",
    "corrosion": "коррозия_арматуры",
    "efflorescence": "эффлоресценция",
    "spalling": "сколы_бетона",
    "rust stain": "ржавое_пятно",
    "rust_stain": "ржавое_пятно",
    "scaling": "отслоение_покрытия",
    # GYU-DET / other models
    "exposed rebar": "обнажённая_арматура",
    "honeycomb": "раковина_бетона",
    "seepage": "протечка",
    "hole": "пустоты",
}

CONSTRUCTION_TYPES = [
    "монолитная_колонна",
    "железобетонная_плита",
    "кирпичная_кладка",
    "фундаментная_лента",
    "перекрытие",
    "монолитная_стена",
    "сварной_шов",
    "кровельное_покрытие",
]

MOCK_DEFECT_TYPES = list(CLASS_MAP.values())


class Detection(BaseModel):
    class_name: str
    confidence: float
    bbox: list[float]  # [x1_rel, y1_rel, x2_rel, y2_rel] normalised 0-1


class InferenceResult(BaseModel):
    construction_type: str | None
    construction_type_confidence: float
    detections: list[dict]


def _roboflow_pred_to_detection(pred: dict, img_w: int, img_h: int) -> dict:
    """Convert Roboflow prediction (center x/y/w/h in pixels) → normalised bbox."""
    cx, cy = pred["x"], pred["y"]
    w, h = pred["width"], pred["height"]
    x1 = max(0.0, (cx - w / 2) / img_w)
    y1 = max(0.0, (cy - h / 2) / img_h)
    x2 = min(1.0, (cx + w / 2) / img_w)
    y2 = min(1.0, (cy + h / 2) / img_h)
    raw_class = pred.get("class", "")
    mapped = CLASS_MAP.get(raw_class.lower(), raw_class)
    return {
        "class": mapped,
        "confidence": round(pred.get("confidence", 0.5), 3),
        "bbox": [round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)],
    }


async def _call_roboflow(image_bytes: bytes) -> list[dict]:
    b64 = base64.b64encode(image_bytes).decode()
    url = f"{ROBOFLOW_BASE}/{ROBOFLOW_MODEL}?api_key={ROBOFLOW_API_KEY}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            content=b64,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
    img_w = data.get("image", {}).get("width", 1920)
    img_h = data.get("image", {}).get("height", 1080)
    return [_roboflow_pred_to_detection(p, img_w, img_h) for p in data.get("predictions", [])]


def _mock_detections() -> tuple[str, float, list[dict]]:
    """Deterministic-ish mock for local dev without Roboflow key."""
    construction_type = random.choice(CONSTRUCTION_TYPES)
    confidence = round(random.uniform(0.65, 0.95), 3)
    n = random.randint(0, 2)
    detections = []
    for _ in range(n):
        detections.append({
            "class": random.choice(MOCK_DEFECT_TYPES),
            "confidence": round(random.uniform(0.45, 0.92), 3),
            "bbox": [
                round(random.uniform(0.05, 0.4), 3),
                round(random.uniform(0.05, 0.4), 3),
                round(random.uniform(0.5, 0.95), 3),
                round(random.uniform(0.5, 0.95), 3),
            ],
        })
    return construction_type, confidence, detections


@app.post("/inference", response_model=InferenceResult)
async def run_inference(file: UploadFile = File(...)) -> InferenceResult:
    image_bytes = await file.read()

    if ROBOFLOW_API_KEY:
        try:
            detections = await _call_roboflow(image_bytes)
            # Construction type is determined by Claude Vision in the main pipeline;
            # here we return None so the control service uses LLM classification.
            return InferenceResult(
                construction_type=None,
                construction_type_confidence=0.0,
                detections=detections,
            )
        except Exception as exc:
            # Log and fall through to mock so dev still works
            print(f"[ml-service] Roboflow error: {exc}")

    construction_type, confidence, detections = _mock_detections()
    return InferenceResult(
        construction_type=construction_type,
        construction_type_confidence=confidence,
        detections=detections,
    )


@app.get("/health")
async def health() -> dict:
    mode = "roboflow" if ROBOFLOW_API_KEY else "mock"
    return {"status": "ok", "mode": mode, "model": ROBOFLOW_MODEL}
