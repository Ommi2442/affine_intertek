from pydantic import BaseModel, Field
from typing import Any, Literal, Optional
from datetime import datetime


UploadCategory = Literal[
    "source_documents",
    "trf",
    "cdr",
    "letter",
    "citation_docs",
    "images",
]

ReportType = Literal["trf", "cdr", "letter"]


class AutosavePayload(BaseModel):
    projectId: str
    reportType: ReportType
    data: dict
    section: Optional[str] = None


class DashboardQuery(BaseModel):
    user_role: int = 2
    user_email: Optional[str] = None
    project_id: Optional[str] = None
