from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.db.database import SessionLocal

router = APIRouter(tags=["health"])


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
    "/health",
    response_model=HealthResponse,
    summary="Health check for monitoring and container orchestration (REL-001)",
    responses={503: {"model": HealthResponse, "description": "The database is unavailable"}},
)
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "unavailable"},
        )
    return HealthResponse(status="ok", database="ok")
