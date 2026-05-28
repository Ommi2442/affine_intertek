import os
import time
from datetime import datetime
from pathlib import Path

from azure.cosmos import CosmosClient
from dotenv import load_dotenv

from projects.keyvault_load import load_keyvault_secrets
from utility.embeddings import ingest_files_from_blob_urls_create_embeddings
from utility.json_to_blob import *
from utility.trf_report.trf_generation import run_trf_generation
from utility.trf_utils import upsert_report_statistics

load_dotenv()


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

# Single JSON mode: use the main PTA JSON directly for AI answering
INPUT_JSON_FILENAMES = ["pta_final_6_3_1.json"]
INPUT_DOCX_PATH = BASE_DIR / "data" / "input_files" / "input.docx"

DOWNLOAD_DIR = BASE_DIR / "data" / "src_files"

DATA_DIR = BASE_DIR / "data"
DATA_DIR = BASE_DIR / "data"

IMAGE_URLS_PATH = BASE_DIR / "utility" / "image_urls.json"  # adjust if needed


def process_trf_direct(project_id: str):
    print(f"TRF started for project {project_id}")
    pipeline_start = time.perf_counter()

    from utility.progress_tracker import update_pipeline_progress, PipelineType
    from utility.pipeline_stages import TRF_STAGES, get_trf_message

    update_pipeline_progress(
        project_id=project_id,
        stages=TRF_STAGES,
        current_stage="GATHER_PROJECT_INFO",
        pipeline_type=PipelineType.TRF,
        message=get_trf_message("GATHER_PROJECT_INFO"),
    )

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
    blob_urls = [d["url"] for d in source_docs if isinstance(d, dict) and "url" in d]

    if not blob_urls:
        raise Exception("No valid source docs")

    user_name = project_doc.get("User_Name") or ""
    # first_name = user_name.split()[0]
    first_name = (
        user_name.strip().split()[0]
        if isinstance(user_name, str) and user_name.strip()
        else None
    )
    text_container = f"vectorstorecontainer_new_itk_text_{first_name}_{project_id}"
    image_container = f"vectorstorecontainer_new_itk_image_{first_name}_{project_id}"

    def on_first_json_ready():
        pass

    try:
        ingest_files_from_blob_urls_create_embeddings(
            DOWNLOAD_DIR, blob_urls, project_id, text_container, image_container
        )

        project_data_dir = BASE_DIR / "data" / project_id
        OUTPUT_JSON = DATA_DIR / project_id / "final_output.json"
        OUTPUT_DOCX = DATA_DIR / project_id / "final_output.docx"

        # Single JSON mode: process the main PTA JSON directly
        INPUT_JSONS = [BASE_PTA_JSON_PATH]

        stats = run_trf_generation(
            blob_urls,
            text_container,
            image_container,
            input_docx_path=INPUT_DOCX_PATH,
            output_docx_path=OUTPUT_DOCX,
            base_pta_path=BASE_PTA_JSON_PATH,
            input_json_paths=INPUT_JSONS,
            project_data_dir=project_data_dir,
            project_id=project_id,
            batch_size=150,
            final_output_path=OUTPUT_JSON,
            cooldown_sec=15,
            max_workers=10,
            on_first_json_generated=on_first_json_ready,
        )

        save_local_json_to_blob_and_cosmos(
            str(OUTPUT_JSON), str(OUTPUT_DOCX), project_id, update_only=False
        )

        end_time = time.perf_counter()
        time_taken = end_time - pipeline_start
        stats["time_taken"] = time_taken

        # Update statistics report to Cosmos DB
        upsert_report_statistics(
            payload=stats,
            cosmos_config={
                "endpoint": COSMOS_DB_URI,
                "key": COSMOS_DB_KEY,
                "database_name": "intertek_pocplus_dev",
                "container_name": "Project_TRF",
            },
            project_id=project_id,
        )

    except Exception as e:
        from utility.progress_tracker import update_pipeline_progress, PipelineType
        from utility.pipeline_stages import TRF_STAGES, get_trf_message

        # Emit error to progress tracker
        update_pipeline_progress(
            project_id=project_id,
            stages=TRF_STAGES,
            current_stage="GATHER_PROJECT_INFO",
            pipeline_type=PipelineType.TRF,
            message=get_trf_message("GATHER_PROJECT_INFO"),
            error=str(e),
        )
        raise
