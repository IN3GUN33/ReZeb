"""HTTP client for ML inference service (YOLOv11)."""
from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.exceptions import MLServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
async def run_yolo_inference(image_bytes: bytes, filename: str = "photo.jpg") -> dict:
    """Call ML service for YOLO inference on a photo."""
    settings = get_settings()
    url = f"{settings.ml_service_url}/inference"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                files={"file": (filename, image_bytes, "image/jpeg")},
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "yolo_inference_done",
                construction_type=result.get("construction_type"),
                n_detections=len(result.get("detections", [])),
            )
            return result
    except httpx.HTTPStatusError as e:
        logger.error("ml_service_http_error", status=e.response.status_code)
        raise MLServiceError(f"ML service returned {e.response.status_code}") from e
    except httpx.RequestError as e:
        logger.warning("ml_service_unavailable", error=str(e))
        # Return empty result — LLM will still attempt analysis from raw image
        return {"construction_type": None, "construction_type_confidence": 0.5, "detections": []}
