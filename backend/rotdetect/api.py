from __future__ import annotations

import json
from pathlib import Path

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
async def analyze(file: UploadFile = File(...),
                  config: str = Form("{}")) -> dict:
    allowed_extensions = (".csv", ".dat", ".txt")
    if not file.filename or not file.filename.lower().endswith(
            allowed_extensions):
        raise HTTPException(status_code=400,
                            detail="Please upload a .csv, .dat, or .txt file.")

    try:
        payload = SearchConfigPayload.model_validate_json(config or "{}")
    except Exception as exc:
        raise HTTPException(status_code=400,
                            detail=f"Invalid config JSON: {exc}") from exc

    try:
        csv_bytes = await file.read()
        search_config = SearchConfig(**payload.model_dump())
        result = run_pipeline_from_csv_bytes(csv_bytes, search_config)
        return result_to_dict(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400,
                            detail=f"Invalid config JSON: {exc}") from exc


@app.get("/api/config")
def get_config() -> dict:
    """Get default search config from config.json."""
    config_path = Path(__file__).resolve().parent.parent.parent / "config.json"

    try:
        with open(config_path) as f:
            config_data = json.load(f)
        search_config = config_data.get("search_config", {})
        return {"status": "ok", "config": search_config}
    except FileNotFoundError:
        raise HTTPException(status_code=404,
                            detail="config.json not found") from None
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON in config.json: {exc}") from exc


@app.post("/api/config")
def save_config(config: str = Form(...)) -> dict:
    """Save search config to config.json."""
    config_path = Path(__file__).resolve().parent.parent.parent / "config.json"

    try:
        payload = SearchConfigPayload.model_validate_json(config)
        config_dict = payload.model_dump(exclude_none=True)
    except Exception as exc:
        raise HTTPException(status_code=400,
                            detail=f"Invalid config JSON: {exc}") from exc

    try:
        # Read existing config.json
        with open(config_path) as f:
            full_config = json.load(f)

        # Update search_config with new values
        full_config["search_config"] = config_dict

        # Write back to file with pretty formatting
        with open(config_path, "w") as f:
            json.dump(full_config, f, indent=2)

        return {"status": "ok", "message": "Config saved successfully"}
    except FileNotFoundError:
        raise HTTPException(status_code=404,
                            detail="config.json not found") from None
    except (json.JSONDecodeError, IOError) as exc:
        raise HTTPException(status_code=500,
                            detail=f"Failed to save config: {exc}") from exc
