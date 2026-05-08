from __future__ import annotations

import json

from fastapi.testclient import TestClient

from rotdetect.api import app
from tests.test_pipeline_synthetic import make_single_column_period_csv, make_synthetic_peak_csv


def test_api_analyze_returns_result() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/analyze",
        files={"file": ("synthetic.csv", make_synthetic_peak_csv(), "text/csv")},
        data={
            "config": json.dumps(
                {
                    "period_min": 0.5,
                    "period_max": 1.4,
                    "delta_p_min": 0.02,
                    "delta_p_max": 0.045,
                    "delta_p_grid": 0.0002,
                    "min_modes": 6,
                }
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["best_sequence"]["n_modes"] >= 8
    assert "echelle" in payload["plots"]


def test_api_analyze_accepts_period_column() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/analyze",
        files={"file": ("periods.csv", make_single_column_period_csv(), "text/csv")},
        data={
            "config": json.dumps(
                {
                    "period_min": 0.5,
                    "period_max": 1.4,
                    "delta_p_min": 0.02,
                    "delta_p_max": 0.045,
                    "delta_p_grid": 0.0002,
                    "min_modes": 6,
                }
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["input_summary"]["input_quantity"] == "period"
    assert payload["best_sequence"]["n_modes"] >= 8
