from pydantic import BaseModel, Field
from typing import List, Optional, Any


class ErrorDetail(BaseModel):
    field: str = Field(..., description="Name of the field with the error")
    message: str = Field(..., description="Error description for this field")
    provided_value: Optional[Any] = Field(None, description="Value provided by the client")

class ErrorPayload(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Details about specific fields")
    request_id: str = Field(..., description="Unique request identifier for tracing")
    documentation: str = Field(..., description="Link to the documentation")

class ErrorResponse(BaseModel):
    error: ErrorPayload

STANDARD_ERRORS = {
    400: {"model": ErrorResponse, "description": "Bad Request"},
    404: {"model": ErrorResponse, "description": "Resource Not Found"},
    422: {"model": ErrorResponse, "description": "Validation Error (Unprocessable Entity)"},
}
