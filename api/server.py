import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from workflows.discovery_vetting_graph import build_discovery_vetting_graph

logger = logging.getLogger(__name__)
app = FastAPI(title="Home Improvement Agent API", version="0.1.0")


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class DiscoveryJobRequest(BaseModel):
    service_type: str = Field(..., min_length=1)
    zip_code: str = Field(..., min_length=3)
    target_contractor_count: int = Field(default=5, ge=1, le=20)
    selected_contractor_index: int = Field(default=0, ge=0)


class DiscoveryResult(BaseModel):
    consolidated_summary: Optional[dict[str, Any]] = None
    flags: list[str] = Field(default_factory=list)
    selected_contractor_name: Optional[str] = None
    selected_contractor_index: Optional[int] = None
    yelp_candidate_count: int = 0


class DiscoveryJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    request: DiscoveryJobRequest
    result: Optional[DiscoveryResult] = None
    error: Optional[str] = None


class DiscoveryJobCreated(BaseModel):
    job_id: str
    status: JobStatus


_jobs: dict[str, DiscoveryJobResponse] = {}
_jobs_lock = asyncio.Lock()


def _utcnow_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _build_initial_state(payload: DiscoveryJobRequest) -> dict[str, Any]:
    return {
        "service_type": payload.service_type.strip() or "home improvement",
        "target_contractor_count": payload.target_contractor_count,
        "contractor_name": None,
        "selected_contractor_index": payload.selected_contractor_index,
        "zip_code": payload.zip_code.strip(),
        "yelp_candidates": [],
        "contractor_data": None,
        "yelp_url": None,
        "google_url": None,
        "bbb_url": None,
        "raw_yelp_data": None,
        "raw_google_data": None,
        "raw_bbb_data": None,
        "raw_website_data": None,
        "raw_synthesis_data": None,
        "flags": [],
    }


def _run_discovery(payload: DiscoveryJobRequest) -> DiscoveryResult:
    graph = build_discovery_vetting_graph()
    final_state = graph.invoke(_build_initial_state(payload))

    consolidated_summary = None
    raw_synthesis = (final_state.get("raw_synthesis_data") or "").strip()
    if raw_synthesis:
        try:
            consolidated_summary = json.loads(raw_synthesis)
        except Exception:
            logger.warning("Synthesis payload was not valid JSON for API response.")

    return DiscoveryResult(
        consolidated_summary=consolidated_summary,
        flags=list(final_state.get("flags") or []),
        selected_contractor_name=final_state.get("contractor_name"),
        selected_contractor_index=final_state.get("selected_contractor_index"),
        yelp_candidate_count=len(final_state.get("yelp_candidates") or []),
    )


async def _execute_job(job_id: str, payload: DiscoveryJobRequest) -> None:
    async with _jobs_lock:
        job = _jobs[job_id]
        job.status = JobStatus.running
        job.updated_at = _utcnow_iso()

    try:
        result = await asyncio.to_thread(_run_discovery, payload)
        async with _jobs_lock:
            job = _jobs[job_id]
            job.status = JobStatus.completed
            job.result = result
            job.updated_at = _utcnow_iso()
    except Exception as exc:
        logger.exception("Discovery job failed for job_id='%s'.", job_id)
        async with _jobs_lock:
            job = _jobs[job_id]
            job.status = JobStatus.failed
            job.error = str(exc)
            job.updated_at = _utcnow_iso()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/discovery/jobs", response_model=DiscoveryJobCreated)
async def create_discovery_job(payload: DiscoveryJobRequest) -> DiscoveryJobCreated:
    job_id = str(uuid.uuid4())
    now = _utcnow_iso()
    job = DiscoveryJobResponse(
        job_id=job_id,
        status=JobStatus.queued,
        created_at=now,
        updated_at=now,
        request=payload,
    )

    async with _jobs_lock:
        _jobs[job_id] = job

    asyncio.create_task(_execute_job(job_id, payload))
    return DiscoveryJobCreated(job_id=job_id, status=JobStatus.queued)


@app.get("/discovery/jobs/{job_id}", response_model=DiscoveryJobResponse)
async def get_discovery_job(job_id: str) -> DiscoveryJobResponse:
    async with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
