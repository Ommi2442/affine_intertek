import os

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from api.v1.config import is_mock_mode
from api.v1.models import AutosavePayload
from api.v1 import mock_store
from api.v1 import services

router = APIRouter()


def _mock_flag() -> dict:
    return {"mock_mode": is_mock_mode()} if is_mock_mode() else {}

VALID_UPLOAD_CATEGORIES = {
    "source_documents",
    "trf",
    "cdr",
    "letter",
    "citation_docs",
    "images",
}


@router.post("/upload")
async def upload_files(
    projectId: str = Form(...),
    category: str = Form(..., description="Upload category (e.g. source_documents, trf, cdr, letter)"),
    files: list[UploadFile] = File(...),
):
    """Upload files based on category."""
    if category not in VALID_UPLOAD_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Allowed: {sorted(VALID_UPLOAD_CATEGORIES)}",
        )

    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    file_payloads = []
    for file in files:
        data = await file.read()
        file_payloads.append((os.path.basename(file.filename), data))

    return await services.upload_files_by_category(projectId, category, file_payloads)


@router.post("/autosave")
async def autosave(payload: AutosavePayload):
    """Save intermediate user progress for a report."""
    return services.autosave_report_progress(
        project_id=payload.projectId,
        report_type=payload.reportType,
        data=payload.data,
        section=payload.section,
    )


@router.get("/report-dashboard")
async def get_report_dashboard(
    user_role: int = Query(2, description="User role (2 = project owner filter)"),
    user_email: str | None = Query(None, description="Required when user_role is 2"),
    project_id: str | None = Query(None, description="Optional single-project filter"),
):
    """Fetch report dashboard project list and progress."""
    projects = services.fetch_dashboard_projects(
        user_role=user_role,
        user_email=user_email,
        project_id=project_id,
    )
    return {
        "status": "success",
        "version": "v1",
        "count": len(projects),
        "user_role": user_role,
        "data": projects,
        **_mock_flag(),
    }


@router.get("/kpi-dashboard")
async def get_kpi_dashboard(
    user_role: int = Query(2),
    user_email: str | None = Query(None),
    project_id: str | None = Query(None),
):
    """Fetch KPI metrics for performance tracking."""
    projects = services.fetch_dashboard_projects(
        user_role=user_role,
        user_email=user_email,
        project_id=project_id,
    )
    return {
        "status": "success",
        "version": "v1",
        "kpis": services.compute_kpi_metrics(projects),
        **_mock_flag(),
    }


@router.get("/report-statistics")
async def get_report_statistics(
    user_role: int = Query(2),
    user_email: str | None = Query(None),
    project_id: str | None = Query(None),
):
    """Detailed analytics of reports."""
    projects = services.fetch_dashboard_projects(
        user_role=user_role,
        user_email=user_email,
        project_id=project_id,
    )
    stats = services.compute_report_statistics(projects)
    return {
        "status": "success",
        "version": "v1",
        **stats,
        **_mock_flag(),
    }


@router.get("/mock/info")
async def mock_info():
    """Sample project IDs and whether mock mode is active."""
    return services.mock_info()


@router.post("/mock/reset")
async def mock_reset():
    """Reset in-memory mock data (only when API_V1_MOCK_MODE=true)."""
    if not is_mock_mode():
        raise HTTPException(
            status_code=403,
            detail="mock/reset is only available when API_V1_MOCK_MODE=true",
        )
    mock_store.reset()
    return {
        "status": "success",
        "message": "Mock data reset to defaults",
        "sample_project_ids": list(mock_store.MOCK_PROJECT_IDS),
    }
