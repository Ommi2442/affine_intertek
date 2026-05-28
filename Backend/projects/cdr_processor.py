from utility.cdr_report.CDR_Pipelines.main import main2
from fastapi import status
import json
import requests
from db.database import COSMOS_DB_project_Container
import os
from datetime import datetime, timezone
from azure.cosmos import CosmosClient
from utility.json_to_blob import *
from utility.trf_utils import upsert_report_statistics
from utility.cdr_report.CDR_Pipelines.main import main2
from utility.json_to_blob import (
    save_cdr_local_json_to_blob_and_cosmos_cdr,
    save_local_xlsx_to_blob_and_cosmos_cdr,
)
from utility.cdr_report.CDR_Pipelines.token_tracker import token_tracker

from azure.cosmos import CosmosClient
from pathlib import Path
from dotenv import load_dotenv
import time

load_dotenv()

from projects.keyvault_load import *

load_keyvault_secrets()

COSMOS_DB_URI = os.getenv("cosmos-db-url")
COSMOS_DB_KEY = os.getenv("cosmos-db-key")
COSMOS_DB_DATABASE = os.getenv("cosmos-db-database")
COSMOS_PROJECT_CONTAINER = os.getenv("cosmos-db-project-container")


cosmos_client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
db = cosmos_client.get_database_client(COSMOS_DB_DATABASE)
projects_container = db.get_container_client(COSMOS_PROJECT_CONTAINER)


BASE_DIR = Path(__file__).resolve().parents[1]  # Backend/
DATA_DIR = BASE_DIR / "data"


# ==========================================================
# HELPER: UPDATE PROJECT PROGRESS
# ==========================================================
def update_project_progress_CDR(
    project_doc: dict,
    cdr_stage: str,
    cdr_percentage: int = 10,
    cdr_step: str | None = None,
    error: str | None = None,
    last_updated: datetime | None = None,
    cdr_completed: bool = False,
):
    project_doc["CDR_Project_Progress"] = {
        "cdr_stage": cdr_stage,
        "cdr_percentage": cdr_percentage,
        "cdr_step": cdr_step,
        "last_updated": (last_updated or datetime.utcnow()).isoformat(),
        "error": error,
        "cdr_completed": cdr_completed,
    }

    projects_container.upsert_item(project_doc)
    print(f" Progress updated → {cdr_percentage}% | {cdr_stage} --- {cdr_completed}")


def process_cdr_direct(project_id: str):

    try:
        # ========================================
        # RESET TRACKER FOR NEW RUN
        # ========================================
        start_time = time.perf_counter()
        token_tracker.reset()

        print(f"CDR started for project {project_id}")

        query = "SELECT * FROM c WHERE c.Project_Id = @pid"

        params = [{"name": "@pid", "value": project_id}]

        items = list(
            COSMOS_DB_project_Container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            )
        )

        cdr_progress = items[0].get("CDR_Project_Progress") or {}

        cdr_percentage = cdr_progress.get("cdr_percentage", 0)

        print(cdr_percentage, "------ ", type(cdr_percentage))

        # if cdr_percentage < 100:
        query = f"SELECT * FROM c WHERE c.Project_Id = '{project_id}'"

        docs = list(
            COSMOS_DB_project_Container.query_items(
                query=query,
                enable_cross_partition_query=True,
            )
        )

        project_doc = docs[0]

        update_project_progress_CDR(
            project_doc,
            cdr_stage="steps in Progress",
            cdr_percentage=10,
            cdr_step="Starting runnig CDR",
            cdr_completed=False,
        )

        query = "SELECT c.blob_url FROM c WHERE c.project_id = @pid"

        params = [{"name": "@pid", "value": project_id}]

        try:
            items = list(
                trf_container.query_items(
                    query=query,
                    parameters=params,
                    enable_cross_partition_query=True,
                )
            )

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to query project data from database",
            )

        if not items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )

        blob_url = items[0].get("blob_url")

        if not blob_url or not isinstance(blob_url, str):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CDR Blob URL not found or invalid",
            )

        response = requests.get(blob_url)

        response.raise_for_status()

        trf_filled = response.json()

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        project_dir = DATA_DIR / project_id

        project_dir.mkdir(parents=True, exist_ok=True)

        output_json_path = project_dir / f"iec_output_cdr_{project_id}.json"

        output_excel_path = project_dir / f"iec_output_sheet_{project_id}.xlsx"

        # ========================================
        # STATS FILE PATH
        # ========================================

        user_name = project_doc.get("User_Name") or []

        user_id = user_name.split()[0]

        # ========================================
        # MAIN PIPELINE
        # ========================================

        result = main2(
            project_id, user_id, trf_filled, output_excel_path=output_excel_path
        )

        # ========================================
        # SAVE OUTPUT JSON
        # ========================================

        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print()

        save_cdr_local_json_to_blob_and_cosmos_cdr(output_json_path, project_id)

        print(
            "-----############################## "
            "JSON CDR uploaded "
            "#####################-----\n"
        )

        # ========================================
        # UPLOAD EXCEL
        # ========================================

        save_local_xlsx_to_blob_and_cosmos_cdr(str(output_excel_path), project_id)

        print("----- Excel CDR uploaded -----")

        # ========================================
        # SAVE TOKEN STATS
        # ========================================

        stats_data = token_tracker.to_dict()
        end_time = time.perf_counter()
        time_taken = end_time - start_time
        stats_data["time_taken"] = time_taken

        cosmos_config = {
            "endpoint": COSMOS_DB_URI,
            "key": COSMOS_DB_KEY,
            "database_name": "intertek_pocplus_dev",
            "container_name": "Project_CDR",
        }

        upsert_report_statistics(
            cosmos_config=cosmos_config,
            payload=stats_data,
            project_id=project_id,
        )

        # ========================================
        # UPDATE STATUS
        # ========================================

        update_project_progress_CDR(
            project_doc,
            cdr_stage="Completed",
            cdr_percentage=100,
            cdr_step="CDR generated and stored",
            cdr_completed=True,
        )

        # elif cdr_percentage == 100:
        #     print("----CDR is already generated-----")

        #     project_dir = DATA_DIR / project_id

        #     project_dir.mkdir(parents=True, exist_ok=True)

        #     output_json_path = project_dir / f"iec_output_cdr_{project_id}.json"

        #     output_excel_path = project_dir / f"iec_output_sheet_{project_id}.xlsx"

        #     with open(output_json_path, "r", encoding="utf-8") as f:
        #         cdr_output = json.load(f)

    except Exception as e:
        query = f"SELECT * FROM c WHERE c.Project_Id = '{project_id}'"

        docs = list(
            COSMOS_DB_project_Container.query_items(
                query=query,
                enable_cross_partition_query=True,
            )
        )

        project_doc = docs[0]

        update_project_progress_CDR(
            project_doc,
            cdr_stage="Failed",
            cdr_percentage=0,
            cdr_step="Processing failed",
            error=str(e),
            cdr_completed=False,
        )

        raise
