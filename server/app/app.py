"""Minimal FastAPI application for the server-side container.

The endpoint simply echoes payloads for now so that the Docker image
remains lightweight while still showing where ingestion logic should go.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(title="Home IoT Server", version="0.1.0")


class PowerReading(BaseModel):
    meter: str = Field(description="Logical meter name, e.g. 'home'")
    power_w: float = Field(description="Instantaneous power in watts")
    measured_at: Optional[datetime] = Field(
        default=None, description="UTC timestamp supplied by the device"
    )


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Return simple health data so compose checks have something to hit."""

    return {
        "status": "ok",
        "influx_url": os.getenv("INFLUX_URL", "not-set"),
    }


@app.post("/readings", tags=["power"])
def ingest_reading(reading: PowerReading) -> dict[str, PowerReading]:
    """Echo the payload; wire this up to InfluxDB when ready."""

    return {"received": reading}
