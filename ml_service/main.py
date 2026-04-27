"""
ML Service stub — mock YOLO inference for development.
In production replaced by a real YOLOv11 ONNX Runtime service.
"""
import random
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

app = FastAPI(title="ReZeb ML Service (stub)", version="0.1.0")

MOCK_DEFECT_TYPES = [
    "трещина_поверхностная",
    "трещина_сквозная",
    "отслоение_покрытия",
    "раковина_бетона",
    "нарушение_геометрии",
    "недостаточное_армирование",
    "коррозия_арматуры",
    "сколы_бетона",
    "пустоты",
    "деформация",
]

MOCK_CONSTRUCTION_TYPES = [
    "монолитная_колонна",
    "железобетонная_плита",
    "кирпичная_кладка",
    "сварной_шов",
    "фундаментная_лента",
    "перекрытие",
]


class InferenceResult(BaseModel):
    construction_type: str
    construction_type_confidence: float
    detections: list[dict]


@app.post("/inference", response_model=InferenceResult)
async def run_inference(file: UploadFile = File(...)) -> InferenceResult:
    """Mock YOLO inference — returns random detections for dev/testing."""
    await file.read()  # Consume file

    construction_type = random.choice(MOCK_CONSTRUCTION_TYPES)
    confidence = round(random.uniform(0.65, 0.98), 3)

    n_defects = random.randint(0, 3)
    detections = []
    for _ in range(n_defects):
        defect_type = random.choice(MOCK_DEFECT_TYPES)
        det_confidence = round(random.uniform(0.45, 0.95), 3)
        detections.append({
            "class": defect_type,
            "confidence": det_confidence,
            "bbox": [
                round(random.uniform(0.1, 0.4), 3),
                round(random.uniform(0.1, 0.4), 3),
                round(random.uniform(0.5, 0.9), 3),
                round(random.uniform(0.5, 0.9), 3),
            ],
        })

    return InferenceResult(
        construction_type=construction_type,
        construction_type_confidence=confidence,
        detections=detections,
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "model": "stub_v0"}
