import asyncio
import json
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
from azure.cosmos import CosmosClient, ConsistencyLevel
from utility.embeddings import ingest_files_from_blob_urls_create_embeddings
from utility.json_to_blob import *
from utility.trf_report.trf_generation import run_trf_generation
from azure.cosmos import CosmosClient, ConsistencyLevel
from pathlib import Path
from dotenv import load_dotenv

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


BASE_DIR = Path(__file__).resolve().parent.parent

BASE_PTA_JSON_PATH = BASE_DIR / "data" / "input_files" / "pta_final_6_3_1.json"
INPUT_JSON_FILENAMES = ["pta_final_6_3_1_part1.json","pta_final_6_3_1_part2.json","pta_final_6_3_1_part3.json","pta_final_6_3_1_part4.json", "pta_final_6_3_1_part5.json"]
INPUT_DOCX_PATH = BASE_DIR / "data" / "input_files" / "input.docx"

DOWNLOAD_DIR = BASE_DIR / "data" / "src_files"

DATA_DIR = BASE_DIR / "data" 

IMAGE_URLS_PATH = BASE_DIR / "utility" / "image_urls.json"  # adjust if needed


# ==========================================================
# HELPER: UPDATE PROJECT PROGRESS
# ==========================================================
def update_project_progress(
    project_doc: dict,
    trf_stage: str,
    trf_percentage: int = 10,
    trf_step: str | None = None,
    error: str | None = None,
    last_updated: datetime | None = None,
    trf_completed: bool = False
):
    project_doc["Project_Progress"] = {
        "trf_stage": trf_stage,
        "trf_percentage": trf_percentage,
        "trf_step": trf_step,
        "last_updated": (last_updated or datetime.utcnow()).isoformat(),
        "error": error,
        "trf_completed": trf_completed
    }

    projects_container.upsert_item(project_doc)
    print(f" Progress updated → {trf_percentage}% | {trf_stage}")


def process_trf_direct(project_id: str):
    print(f"TRF started for project {project_id}")

    query = f"SELECT * FROM c WHERE c.Project_Id = '{project_id}'"
    docs = list(
        projects_container.query_items(
            query=query,
            enable_cross_partition_query=True,
        )
    )

    if not docs:
        raise Exception("Project not found")

    project_doc = docs[0]

    source_docs = project_doc.get("Source_Doc") or []
    blob_urls = [
        d["url"]
        for d in source_docs
        if isinstance(d, dict) and "url" in d
    ]

    if not blob_urls:
        raise Exception("No valid source docs")

    user_name = project_doc.get("User_Name") or ""
    # first_name = user_name.split()[0]
    first_name = user_name.strip().split()[0] if isinstance(user_name, str) and user_name.strip() else None

    text_container = f"vectorstorecontainer_new_itk_text_{first_name}_{project_id}"
    image_container = f"vectorstorecontainer_new_itk_image_{first_name}_{project_id}"

    def on_first_json_ready():
        update_project_progress(
            project_doc,
            trf_stage="First TRF JSON Generated",
            trf_percentage=30,
            trf_step="Initial TRF JSON ready",
            trf_completed=False
        )

    try:
        update_project_progress(
            project_doc,
            trf_stage="Indexing",
            trf_percentage=10,
            trf_step="Embedding started",
            trf_completed=False
        )

        ingest_files_from_blob_urls_create_embeddings(
            DOWNLOAD_DIR,
            blob_urls,
            project_id,
            text_container,
            image_container
        )

        project_data_dir = BASE_DIR / "data" / project_id
        OUTPUT_JSON = DATA_DIR / project_id / "final_output.json"
        OUTPUT_DOCX = DATA_DIR / project_id / "final_output.docx"

        INPUT_JSONS = [
            DATA_DIR / "input_files" / f
            for f in INPUT_JSON_FILENAMES
        ]

        run_trf_generation(
            blob_urls,
            text_container,
            image_container,
            input_docx_path=INPUT_DOCX_PATH,
            output_docx_path=OUTPUT_DOCX,
            base_pta_path=BASE_PTA_JSON_PATH,
            input_json_paths=INPUT_JSONS,
            project_data_dir=project_data_dir,
            batch_size=150,
            final_output_path=OUTPUT_JSON,
            cooldown_sec=15,
            max_workers=10,
            on_first_json_generated=on_first_json_ready
        )

        save_local_json_to_blob_and_cosmos(
            str(OUTPUT_JSON),
            str(OUTPUT_DOCX),
            project_id,
            update_only=False
        )

        update_project_progress(
            project_doc,
            trf_stage="Completed",
            trf_percentage=100,
            trf_step="TRF generated",
            trf_completed=True
        )

    except Exception as e:
        update_project_progress(
            project_doc,
            trf_stage="Failed",
            trf_percentage=0,
            trf_step="Processing failed",
            error=str(e),
            trf_completed=False
        )
        raise
