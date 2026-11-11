import os
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.db.database import SessionLocal

router = APIRouter(tags=["health"])


class LivenessResponse(BaseModel):
    status: str = Field(..., description="Always 'ok' while the process answers")
    commit: Optional[str] = Field(
        None, description="Git commit of the running build (RENDER_GIT_COMMIT on Render), used to confirm a deploy"
    )


class HealthResponse(BaseModel):
    status: str = Field(..., description="'ok' if the service can serve requests, otherwise 'degraded'")
    database: str = Field(..., description="'ok' if the database answers, otherwise 'unavailable'")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "/health/live",
    response_model=LivenessResponse,
    summary="Liveness check without touching the database (REL-001)",
    description=(
        "For the hosting platform health check and the keep-alive ping: answers while the process is up "
        "and does not wake a serverless database that has scaled to zero. Use /health to check the database too."
    ),
)
def liveness():
    return LivenessResponse(status="ok", commit=os.getenv("RENDER_GIT_COMMIT") or os.getenv("GIT_COMMIT") or None)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check for monitoring and container orchestration (REL-001)",
    responses={503: {"model": HealthResponse, "description": "The database is unavailable"}},
)
def health(request: Request, db: Session = Depends(get_db)):
    if getattr(request.app.state, "database_available", True) is False:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "unavailable"},
        )

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "unavailable"},
        )

    return HealthResponse(status="ok", database="ok")