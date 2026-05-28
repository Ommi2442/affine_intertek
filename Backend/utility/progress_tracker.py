"""
pipeline_progress_tracker.py
─────────────────────────────
Singleton tracker for TRF / CDR / Letter pipeline progress.

Cosmos Containers
─────────────────
Projects
    - Updated on EVERY stage call
    - Stores ONLY latest progress snapshot for each pipeline

Project_Status_Tracker
    - Written ONLY once when pipeline completes or errors
    - Stores FULL audit trail list for each pipeline

Schema rules
────────────
STRICTLY follows existing Cosmos schema.
NO additional fields are introduced.

Error handling
──────────────
When update_pipeline_progress is called with an error:
  1. Stage history is inspected in reverse to find the last successfully
     running/completed stage.
  2. The failed stage is derived as the NEXT stage after the last
     completed one in the stages list.
  3. If no history exists the pipeline failed at the very first stage.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

from azure.cosmos import CosmosClient
from azure.cosmos.container import ContainerProxy
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Environment
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv(override=True)

COSMOS_URL: str = os.environ["cosmos-url"]
COSMOS_KEY: str = os.environ["cosmos-key"]
COSMOS_DB: str = "intertek_pocplus_dev"

PROJECTS_CONTAINER = "Projects"
TRACKER_CONTAINER = "Project_Status_Tracker"

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

# ──────────────────────────────────────────────────────────────────────────────
# Pipeline types
# ──────────────────────────────────────────────────────────────────────────────


class PipelineType:
    TRF = "TRF"
    CDR = "CDR"
    LETTER = "Letter"

    ALL: frozenset[str] = frozenset({TRF, CDR, LETTER})

    @classmethod
    def progress_key(cls, pipeline_type: str) -> str:
        return f"{pipeline_type}_Project_Progress"

    @classmethod
    def status_key(cls, pipeline_type: str) -> str:
        return f"{pipeline_type.lower()}_completion_status"

    @classmethod
    def step_key(cls, pipeline_type: str) -> str:
        return f"{pipeline_type.lower()}_step"

    @classmethod
    def completed_key(cls, pipeline_type: str) -> str:
        return f"is_{pipeline_type.lower()}_completed"

    @classmethod
    def percentage_key(cls, pipeline_type: str) -> str:
        return f"{pipeline_type.lower()}_percentage"


# ──────────────────────────────────────────────────────────────────────────────
# Singleton Tracker
# ──────────────────────────────────────────────────────────────────────────────


class PipelineProgressTracker:
    """
    Thread-safe singleton tracker.
    """

    _instance: Optional["PipelineProgressTracker"] = None
    _class_lock: Lock = Lock()

    def __new__(cls) -> "PipelineProgressTracker":
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._init()
                    cls._instance = inst
        return cls._instance

    # ──────────────────────────────────────────────────────────────────────
    # Init
    # ──────────────────────────────────────────────────────────────────────

    def _init(self) -> None:
        self._instance_lock = Lock()

        self._cosmos_client = CosmosClient(
            url=COSMOS_URL,
            credential=COSMOS_KEY,
        )

        self._db_client = self._cosmos_client.get_database_client(COSMOS_DB)

        self._container_cache: Dict[str, ContainerProxy] = {}

        self._project_cache: Dict[str, dict] = {}

        self._stage_history: Dict[tuple, List[dict]] = {}

        logger.info("PipelineProgressTracker initialized.")

    # ──────────────────────────────────────────────────────────────────────
    # Containers
    # ──────────────────────────────────────────────────────────────────────

    def get_container(self, name: str) -> ContainerProxy:
        if name not in self._container_cache:
            with self._instance_lock:
                if name not in self._container_cache:
                    self._container_cache[name] = self._db_client.get_container_client(
                        name
                    )
        return self._container_cache[name]

    # ──────────────────────────────────────────────────────────────────────
    # Project cache
    # ──────────────────────────────────────────────────────────────────────

    def get_project_document(self, project_id: str) -> Optional[dict]:
        if project_id in self._project_cache:
            return self._project_cache[project_id]

        container = self.get_container(PROJECTS_CONTAINER)

        items = list(
            container.query_items(
                query="SELECT * FROM c WHERE c.Project_Id = @pid",
                parameters=[{"name": "@pid", "value": project_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            return None

        doc = items[0]

        self._project_cache[project_id] = doc

        return doc

    def invalidate_project_cache(self, project_id: str) -> None:
        self._project_cache.pop(project_id, None)

    def upsert_project_document(self, doc: dict) -> None:
        project_id = doc.get("Project_Id")

        self.get_container(PROJECTS_CONTAINER).upsert_item(doc)

        self.invalidate_project_cache(project_id)

    # ──────────────────────────────────────────────────────────────────────
    # Stage history
    # ──────────────────────────────────────────────────────────────────────

    def append_stage(
        self,
        project_id: str,
        pipeline_type: str,
        entry: dict,
    ) -> None:
        key = (project_id, pipeline_type)

        self._stage_history.setdefault(key, []).append(entry)

    def get_stage_history(
        self,
        project_id: str,
        pipeline_type: str,
    ) -> List[dict]:
        key = (project_id, pipeline_type)

        return self._stage_history.get(key, [])

    def clear_stage_history(
        self,
        project_id: str,
        pipeline_type: str,
    ) -> None:
        key = (project_id, pipeline_type)

        self._stage_history.pop(key, None)

    # ──────────────────────────────────────────────────────────────────────
    # Tracker container flush
    # ──────────────────────────────────────────────────────────────────────

    def flush_stage_history(
        self,
        *,
        project_id: str,
        pipeline_type: str,
    ) -> None:
        """
        STRICT tracker schema:
        {
            "Project_Id": "...",
            "TRF_Project_Progress": [],
            "CDR_Project_Progress": [],
            "Letter_Project_Progress": [],
            "id": "uuid"
        }
        """

        history = self.get_stage_history(project_id, pipeline_type)

        if not history:
            logger.warning(
                "No history found for project=%s pipeline=%s",
                project_id,
                pipeline_type,
            )
            return

        tracker_doc = {
            "id": str(uuid.uuid4()),
            "Project_Id": project_id,
            "TRF_Project_Progress": [],
            "CDR_Project_Progress": [],
            "Letter_Project_Progress": [],
        }

        tracker_doc[PipelineType.progress_key(pipeline_type)] = history

        tracker_container = self.get_container(TRACKER_CONTAINER)

        tracker_container.upsert_item(tracker_doc)

        logger.info(
            "Tracker flushed | project=%s | pipeline=%s | stages=%d",
            project_id,
            pipeline_type,
            len(history),
        )

        self.clear_stage_history(project_id, pipeline_type)

    # ──────────────────────────────────────────────────────────────────────
    # Error stage derivation
    # ──────────────────────────────────────────────────────────────────────

    def resolve_failed_stage(
        self,
        project_id: str,
        pipeline_type: str,
        stages: List[str],
    ) -> tuple[str, Optional[str]]:
        """
        Inspect stage history to derive where the pipeline actually failed.

        Returns
        ───────
        (failed_stage, last_completed_stage)

        Algorithm
        ─────────
        1. Walk history in reverse to find the most recent entry whose
           pipeline_status is 'running' or 'completed' — this is the last
           stage that executed successfully.
        2. The failed stage is the NEXT stage in the stages list after that.
        3. If no prior history exists the pipeline failed at the very first
           stage; last_completed_stage is None.
        """

        history = self.get_stage_history(project_id, pipeline_type)

        last_completed_stage: Optional[str] = None

        for entry in reversed(history):
            status = entry.get("pipeline_status", "")
            if status in ("running", "completed", "started"):
                stage_name = entry.get("current_stage")
                if stage_name and stage_name in stages:
                    last_completed_stage = stage_name
                    break

        if last_completed_stage is None:
            # No successful prior stage — failed at the very beginning
            return stages[0], None

        last_completed_index = stages.index(last_completed_stage)
        next_index = last_completed_index + 1

        if next_index < len(stages):
            failed_stage = stages[next_index]
        else:
            # Error reported after the final stage; point back to the last one
            failed_stage = last_completed_stage

        return failed_stage, last_completed_stage


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────


def update_pipeline_progress(
    *,
    project_id: str,
    stages: List[str],
    current_stage: str,
    pipeline_type: str,
    error: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    last_updated: Optional[datetime] = None,
) -> dict:
    """
    Update latest progress in Projects container.

    Flush complete audit trail into Project_Status_Tracker
    ONLY on completion or error.

    Error handling
    ──────────────
    When `error` is provided:
      - Stage history is inspected to find the last successfully executed stage.
      - The failed stage is derived as the next stage after that in the
        stages list and replaces current_stage for all calculations.
      - `extra["failed_stage"]` is populated with the derived failed stage name.
    """

    # ──────────────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────────────

    if not project_id:
        raise ValueError("project_id cannot be empty.")

    if not stages:
        raise ValueError("stages cannot be empty.")

    if pipeline_type not in PipelineType.ALL:
        raise ValueError(
            f"Invalid pipeline_type='{pipeline_type}'. "
            f"Expected one of {sorted(PipelineType.ALL)}"
        )

    if current_stage not in stages:
        raise ValueError(f"current_stage='{current_stage}' not found in stages list.")

    tracker = PipelineProgressTracker()

    try:
        # ──────────────────────────────────────────────────────────────────
        # Fetch project
        # ──────────────────────────────────────────────────────────────────

        project_doc = tracker.get_project_document(project_id)

        if project_doc is None:
            raise ValueError(f"Project '{project_id}' not found in Projects container.")

        # ──────────────────────────────────────────────────────────────────
        # Error: derive failed stage from history
        # ──────────────────────────────────────────────────────────────────

        if error:
            failed_stage, last_completed_stage = tracker.resolve_failed_stage(
                project_id=project_id,
                pipeline_type=pipeline_type,
                stages=stages,
            )

            logger.info(
                "Error detected | project=%s | pipeline=%s | "
                "last_completed=%s | failed_stage=%s",
                project_id,
                pipeline_type,
                last_completed_stage,
                failed_stage,
            )

            # Re-point current_stage to the derived failed stage so all
            # downstream calculations (index, percentage, audit) are consistent
            current_stage = failed_stage

        # ──────────────────────────────────────────────────────────────────
        # Progress calculation
        # ──────────────────────────────────────────────────────────────────

        total_steps = len(stages)

        current_index = stages.index(current_stage)

        percentage = round(
            ((current_index + 1) / total_steps) * 100,
            2,
        )

        # For non-error paths derive last_completed_stage from index position
        if not error:
            last_completed_stage = (
                stages[current_index - 1] if current_index > 0 else None
            )

        # ──────────────────────────────────────────────────────────────────
        # Pipeline status
        # ──────────────────────────────────────────────────────────────────

        if error:
            pipeline_status = "error"

        elif current_index == 0:
            pipeline_status = "started"

        elif current_index == total_steps - 1:
            pipeline_status = "completed"

        else:
            pipeline_status = "running"

        # ──────────────────────────────────────────────────────────────────
        # Completion status
        # ──────────────────────────────────────────────────────────────────

        if error:
            completion_status = "Failed"

        elif pipeline_status == "completed":
            completion_status = "Completed"

        else:
            completion_status = pipeline_status.title()

        # ──────────────────────────────────────────────────────────────────
        # Timestamp
        # ──────────────────────────────────────────────────────────────────

        now = last_updated or datetime.now(timezone.utc)

        now_iso = now.strftime(ISO_FORMAT)

        now_ts = now.timestamp()

        # ──────────────────────────────────────────────────────────────────
        # Extra payload
        # ──────────────────────────────────────────────────────────────────

        extra_payload: Dict[str, Any] = dict(extra or {})

        if message:
            extra_payload["message"] = message

        # ──────────────────────────────────────────────────────────────────
        # PROJECTS container schema
        # STRICTLY FOLLOWED
        # ──────────────────────────────────────────────────────────────────

        latest_progress_entry = {
            PipelineType.status_key(pipeline_type): completion_status,
            PipelineType.step_key(pipeline_type): current_stage,
            PipelineType.completed_key(pipeline_type): pipeline_status == "completed",
            "type": "pipeline_progress",
            "pipeline_status": pipeline_status,
            "current_stage": current_stage,
            "last_completed_stage": last_completed_stage,
            "current_step": current_index + 1,
            "total_steps": total_steps,
            PipelineType.percentage_key(pipeline_type): percentage,
            "error": error,
            "last_updated": now_iso,
            "extra": extra_payload,
        }

        progress_key = PipelineType.progress_key(pipeline_type)

        project_doc[progress_key] = latest_progress_entry

        tracker.upsert_project_document(project_doc)

        logger.info(
            "Projects updated | project=%s | pipeline=%s | stage=%s | status=%s",
            project_id,
            pipeline_type,
            current_stage,
            pipeline_status,
        )

        # ──────────────────────────────────────────────────────────────────
        # TRACKER container schema
        # STRICTLY FOLLOWED
        # percentage field ONLY (not trf_percentage etc)
        # ──────────────────────────────────────────────────────────────────

        audit_entry = {
            "type": "pipeline_progress",
            "pipeline_status": pipeline_status,
            "current_stage": current_stage,
            "last_completed_stage": last_completed_stage,
            "current_step": current_index + 1,
            "total_steps": total_steps,
            "percentage": percentage,
            "error": error,
            "last_updated": now_iso,
            "extra": extra_payload,
            "ts": now_ts,
        }

        tracker.append_stage(
            project_id=project_id,
            pipeline_type=pipeline_type,
            entry=audit_entry,
        )

        # ──────────────────────────────────────────────────────────────────
        # Flush ONLY on completion / error
        # ──────────────────────────────────────────────────────────────────

        if pipeline_status in ("completed", "error"):
            tracker.flush_stage_history(
                project_id=project_id,
                pipeline_type=pipeline_type,
            )

        return latest_progress_entry

    except Exception:
        logger.exception(
            "Failed update_pipeline_progress | project=%s | pipeline=%s | stage=%s",
            project_id,
            pipeline_type,
            current_stage,
        )
        raise
