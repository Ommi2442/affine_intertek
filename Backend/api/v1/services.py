import os
import threading
from datetime import datetime
from typing import Optional

from fastapi import HTTPException

from api.v1.config import is_mock_mode
from api.v1 import mock_store

CONTAINER_NAME = os.getenv("blob-container")
BLOB_PREFIX = "Documents"


def _format_project_row(p: dict) -> dict:
    progress = p.get("Project_Progress") or {}
    cdr_progress = p.get("CDR_Project_Progress") or {}
    letter_progress = p.get("Letter_Project_Progress") or {}

    return {
        "Project_Id": p.get("Project_Id"),
        "Standard": p.get("Standard"),
        "Client_Name": p.get("Client_Name"),
        "Product": p.get("Product"),
        "Proj_Created_On": p.get("Proj_Created_On"),
        "Proj_Created_By": p.get("Proj_Created_By"),
        "Proj_Archived": p.get("Proj_Archived"),
        "trf_percentage": progress.get("trf_percentage", 0),
        "trf_step": progress.get("trf_step"),
        "trf_last_updated": progress.get("trf_last_updated"),
        "trf_error": progress.get("trf_error"),
        "trf_completed": progress.get("trf_completed", "No"),
        "cdr_percentage": cdr_progress.get("cdr_percentage", 0),
        "cdr_step": cdr_progress.get("cdr_step"),
        "cdr_last_updated": cdr_progress.get("last_updated"),
        "cdr_error": cdr_progress.get("error"),
        "cdr_completed": cdr_progress.get("cdr_completed", "No"),
        "letter_percentage": letter_progress.get("letter_percentage", 0),
        "letter_step": letter_progress.get("letter_stage"),
        "letter_last_updated": letter_progress.get("last_updated"),
        "letter_error": letter_progress.get("error"),
        "letter_completed": letter_progress.get("letter_completed", "No"),
    }


def _get_project_doc(project_id: str) -> dict:
    if is_mock_mode():
        doc = mock_store.get_project(project_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Project not found (mock)")
        return doc

    from db.database import COSMOS_DB_project_Container

    query = "SELECT * FROM c WHERE c.Project_Id = @pid"
    params = [{"name": "@pid", "value": project_id}]
    docs = list(
        COSMOS_DB_project_Container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        )
    )
    if not docs:
        raise HTTPException(status_code=404, detail="Project not found")
    return docs[0]


def fetch_dashboard_projects(
    user_role: int,
    user_email: Optional[str] = None,
    project_id: Optional[str] = None,
) -> list[dict]:
    if project_id:
        return [_format_project_row(_get_project_doc(project_id))]

    if is_mock_mode():
        if user_role == 2 and not user_email:
            raise HTTPException(
                status_code=400,
                detail="user_email is required for role 2",
            )
        items = mock_store.list_projects(user_role, user_email)
        return [_format_project_row(p) for p in items]

    from db.database import COSMOS_DB_project_Container

    if user_role == 2:
        if not user_email:
            raise HTTPException(
                status_code=400,
                detail="user_email is required for role 2",
            )
        query = f"""
            SELECT
                c.Project_Id, c.Standard, c.Client_Name, c.Product,
                c.Proj_Created_On, c.Proj_Created_By, c.Proj_Archived,
                c.Project_Progress, c.CDR_Project_Progress, c.Letter_Project_Progress
            FROM c
            WHERE c.Proj_Created_By = "{user_email}"
            AND c.Proj_Archived = false
            ORDER BY c.Proj_Created_On DESC
        """
    else:
        query = """
            SELECT
                c.Project_Id, c.Standard, c.Client_Name, c.Product,
                c.Proj_Created_On, c.Proj_Created_By, c.Proj_Archived,
                c.Project_Progress, c.CDR_Project_Progress, c.Letter_Project_Progress
            FROM c
            WHERE c.Proj_Archived = false
            ORDER BY c.Proj_Created_On DESC
        """

    items = list(
        COSMOS_DB_project_Container.query_items(
            query=query,
            enable_cross_partition_query=True,
        )
    )
    return [_format_project_row(p) for p in items]


def compute_kpi_metrics(projects: list[dict]) -> dict:
    total = len(projects)
    if total == 0:
        return {
            "total_projects": 0,
            "trf": {"completed": 0, "in_progress": 0, "pending": 0, "avg_percentage": 0},
            "cdr": {"completed": 0, "in_progress": 0, "pending": 0, "avg_percentage": 0},
            "letter": {"completed": 0, "in_progress": 0, "pending": 0, "avg_percentage": 0},
        }

    def _is_completed(value) -> bool:
        return str(value).lower() in ("yes", "true", "1")

    def _report_kpi(prefix: str) -> dict:
        pct_key = f"{prefix}_percentage"
        done_key = f"{prefix}_completed"
        completed = sum(1 for p in projects if _is_completed(p.get(done_key)))
        in_progress = sum(
            1
            for p in projects
            if not _is_completed(p.get(done_key)) and (p.get(pct_key) or 0) > 0
        )
        avg_pct = round(sum(p.get(pct_key) or 0 for p in projects) / total, 1)
        return {
            "completed": completed,
            "in_progress": in_progress,
            "pending": total - completed - in_progress,
            "avg_percentage": avg_pct,
        }

    return {
        "total_projects": total,
        "trf": _report_kpi("trf"),
        "cdr": _report_kpi("cdr"),
        "letter": _report_kpi("letter"),
        "generated_at": datetime.utcnow().isoformat(),
    }


def compute_report_statistics(projects: list[dict]) -> dict:
    kpi = compute_kpi_metrics(projects)

    by_standard: dict[str, int] = {}
    errors = {"trf": 0, "cdr": 0, "letter": 0}

    for p in projects:
        standard = p.get("Standard") or "Unknown"
        by_standard[standard] = by_standard.get(standard, 0) + 1
        if p.get("trf_error"):
            errors["trf"] += 1
        if p.get("cdr_error"):
            errors["cdr"] += 1
        if p.get("letter_error"):
            errors["letter"] += 1

    return {
        "summary": kpi,
        "projects_by_standard": by_standard,
        "error_counts": errors,
        "projects": projects,
        "generated_at": datetime.utcnow().isoformat(),
    }


async def upload_files_by_category(
    project_id: str,
    category: str,
    file_payloads: list[tuple[str, bytes]],
) -> dict:
    if is_mock_mode():
        _get_project_doc(project_id)
        results = []
        for original_name, _data in file_payloads:
            entry = mock_store.save_upload(project_id, category, original_name)
            results.append(
                {
                    "filename": entry["filename"],
                    "blob_url": entry["url"],
                    "category": category,
                }
            )
        conversion_note = (
            "mock: citation conversion skipped"
            if category == "source_documents"
            else None
        )
        return {
            "status": "success",
            "message": "Files uploaded successfully (mock — not saved to real DB)",
            "mock_mode": True,
            "category": category,
            "files": results,
            "conversion": conversion_note,
            "cosmos_updated": False,
        }

    from db.database import COSMOS_DB_project_Container
    from utility.json_to_blob import blob_service

    container_client = blob_service.get_container_client(CONTAINER_NAME)
    results = []
    uploaded_urls = []

    for original_name, data in file_payloads:
        blob_path = f"{BLOB_PREFIX}/{project_id}/{category}/{original_name}"
        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(data, overwrite=True)
        uploaded_urls.append(
            {"filename": original_name, "blob_url": blob_client.url}
        )
        results.append(
            {
                "filename": original_name,
                "blob_url": blob_client.url,
                "category": category,
            }
        )

    project_doc = _get_project_doc(project_id)
    project_doc.setdefault("Source_Doc", [])

    for item in uploaded_urls:
        project_doc["Source_Doc"].append(
            {
                "filename": item["filename"],
                "url": item["blob_url"],
                "category": category,
                "uploaded_at": datetime.utcnow().isoformat(),
            }
        )

    COSMOS_DB_project_Container.upsert_item(project_doc)

    conversion_note = None
    if category == "source_documents":
        from projects.routes import process_citation_documents

        threading.Thread(
            target=process_citation_documents,
            args=(project_id, blob_service, CONTAINER_NAME),
            daemon=True,
        ).start()
        conversion_note = "citation docs conversion started"

    return {
        "status": "success",
        "message": "Files uploaded successfully",
        "category": category,
        "files": results,
        "conversion": conversion_note,
        "cosmos_updated": True,
    }


def autosave_report_progress(
    project_id: str,
    report_type: str,
    data: dict,
    section: Optional[str] = None,
) -> dict:
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="data must be a valid JSON object")

    if is_mock_mode():
        _get_project_doc(project_id)
        draft = mock_store.save_draft(project_id, report_type, data, section)
        return {
            "status": "success",
            "message": "Progress saved (mock — not saved to real DB)",
            "mock_mode": True,
            "projectId": project_id,
            "reportType": report_type,
            "section": section,
            "saved_at": draft["saved_at"],
            "blob_updated": False,
        }

    from db.database import (
        COSMOS_DB_project_Container,
        COSMOS_DB_project_cdr_Container,
        COSMOS_DB_project_LETTER_Container,
        COSMOS_DB_project_trf_Container,
    )
    from projects.helpers import fetch_final_json_record, replace_json_blob
    from utility.json_to_blob import blob_service

    report_containers = {
        "trf": COSMOS_DB_project_trf_Container,
        "cdr": COSMOS_DB_project_cdr_Container,
        "letter": COSMOS_DB_project_LETTER_Container,
    }

    project_doc = _get_project_doc(project_id)
    saved_at = datetime.utcnow().isoformat()
    drafts = project_doc.setdefault("Autosave_Drafts", {})
    drafts[report_type] = {
        "data": data,
        "section": section,
        "saved_at": saved_at,
    }
    project_doc["Autosave_Drafts"] = drafts
    COSMOS_DB_project_Container.upsert_item(project_doc)

    blob_updated = False
    container = report_containers[report_type]
    try:
        record = fetch_final_json_record(container, project_id)
        replace_json_blob(
            blob_service=blob_service,
            container_name=CONTAINER_NAME,
            blob_path=record["blob_path"],
            json_data=data,
        )
        blob_updated = True
    except HTTPException as exc:
        if exc.status_code != 404:
            raise

    return {
        "status": "success",
        "message": "Progress saved",
        "projectId": project_id,
        "reportType": report_type,
        "section": section,
        "saved_at": saved_at,
        "blob_updated": blob_updated,
    }


def mock_info() -> dict:
    raw = os.getenv("API_V1_MOCK_MODE", "")
    return {
        "mock_mode": is_mock_mode(),
        "API_V1_MOCK_MODE": raw or None,
        "hint": "Add API_V1_MOCK_MODE=true to Backend/.env (or set env var), then restart uvicorn",
        "sample_project_ids": list(mock_store.MOCK_PROJECT_IDS),
        "sample_user_email": mock_store.MOCK_USER_EMAIL,
    }
