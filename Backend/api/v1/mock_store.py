"""In-memory store for API v1 mock mode — no Cosmos DB or blob writes."""

from copy import deepcopy
from datetime import datetime
from typing import Optional

MOCK_PROJECT_IDS = ("MOCK-001", "MOCK-002", "MOCK-003")
MOCK_USER_EMAIL = "mock.user@intertek.test"


def _seed_projects() -> dict[str, dict]:
    now = datetime.utcnow().isoformat()
    return {
        "MOCK-001": {
            "Project_Id": "MOCK-001",
            "Standard": "IEC61010-1",
            "Client_Name": "Mock Client A",
            "Product": "Mock Product A",
            "Proj_Created_On": now,
            "Proj_Created_By": MOCK_USER_EMAIL,
            "Proj_Archived": False,
            "Source_Doc": [],
            "Autosave_Drafts": {},
            "Project_Progress": {
                "trf_percentage": 100,
                "trf_step": "done",
                "trf_last_updated": now,
                "trf_completed": "Yes",
            },
            "CDR_Project_Progress": {
                "cdr_percentage": 50,
                "cdr_step": "review",
                "last_updated": now,
                "cdr_completed": "No",
            },
            "Letter_Project_Progress": {
                "letter_percentage": 0,
                "letter_stage": "pending",
                "last_updated": now,
                "letter_completed": "No",
            },
        },
        "MOCK-002": {
            "Project_Id": "MOCK-002",
            "Standard": "IEC62368-1",
            "Client_Name": "Mock Client B",
            "Product": "Mock Product B",
            "Proj_Created_On": now,
            "Proj_Created_By": MOCK_USER_EMAIL,
            "Proj_Archived": False,
            "Source_Doc": [],
            "Autosave_Drafts": {},
            "Project_Progress": {
                "trf_percentage": 30,
                "trf_step": "generating",
                "trf_last_updated": now,
                "trf_error": "Sample error for testing",
                "trf_completed": "No",
            },
            "CDR_Project_Progress": {
                "cdr_percentage": 0,
                "cdr_completed": "No",
            },
            "Letter_Project_Progress": {
                "letter_percentage": 0,
                "letter_completed": "No",
            },
        },
        "MOCK-003": {
            "Project_Id": "MOCK-003",
            "Standard": "IEC61010-1",
            "Client_Name": "Mock Client C",
            "Product": "Mock Product C",
            "Proj_Created_On": now,
            "Proj_Created_By": "other.user@intertek.test",
            "Proj_Archived": False,
            "Source_Doc": [],
            "Autosave_Drafts": {},
            "Project_Progress": {
                "trf_percentage": 100,
                "trf_completed": "Yes",
            },
            "CDR_Project_Progress": {
                "cdr_percentage": 100,
                "cdr_completed": "Yes",
            },
            "Letter_Project_Progress": {
                "letter_percentage": 100,
                "letter_completed": "Yes",
            },
        },
    }


_projects: dict[str, dict] = _seed_projects()
_report_json: dict[str, dict] = {}


def reset() -> None:
    global _projects, _report_json
    _projects = _seed_projects()
    _report_json = {}


def get_project(project_id: str) -> Optional[dict]:
    doc = _projects.get(project_id)
    return deepcopy(doc) if doc else None


def list_projects(user_role: int, user_email: Optional[str]) -> list[dict]:
    docs = [deepcopy(p) for p in _projects.values() if not p.get("Proj_Archived")]
    if user_role == 2 and user_email:
        docs = [p for p in docs if p.get("Proj_Created_By") == user_email]
    return docs


def upsert_project(doc: dict) -> dict:
    pid = doc["Project_Id"]
    _projects[pid] = deepcopy(doc)
    return deepcopy(_projects[pid])


def save_upload(
    project_id: str,
    category: str,
    filename: str,
) -> dict:
    doc = _projects[project_id]
    doc.setdefault("Source_Doc", [])
    entry = {
        "filename": filename,
        "url": f"mock://blob/{project_id}/{category}/{filename}",
        "category": category,
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    doc["Source_Doc"].append(entry)
    return entry


def save_draft(project_id: str, report_type: str, data: dict, section: Optional[str]) -> dict:
    doc = _projects[project_id]
    saved_at = datetime.utcnow().isoformat()
    draft = {"data": deepcopy(data), "section": section, "saved_at": saved_at}
    doc.setdefault("Autosave_Drafts", {})[report_type] = draft
    _report_json[f"{project_id}:{report_type}"] = deepcopy(data)
    return draft


def has_report_json(project_id: str, report_type: str) -> bool:
    return f"{project_id}:{report_type}" in _report_json
