from __future__ import annotations

import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .core.config import SearchConfig
from .core.pipeline import result_to_dict, run_pipeline_from_csv_bytes
from .schemas import SearchConfigPayload

app = FastAPI(title="RotDetect API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), config: str = Form("{}")) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    try:
        payload = SearchConfigPayload.model_validate_json(config or "{}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid config JSON: {exc}") from exc

    try:
        csv_bytes = await file.read()
        search_config = SearchConfig(**payload.model_dump())
        result = run_pipeline_from_csv_bytes(csv_bytes, search_config)
        return result_to_dict(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid config JSON: {exc}") from exc
