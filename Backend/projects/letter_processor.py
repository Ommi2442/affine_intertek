import json
import traceback
from pathlib import Path
from datetime import datetime
from azure.cosmos import CosmosClient
from utility.json_to_blob import (
    save_local_jsons_and_docx_to_blob_and_cosmos_for_letter
)
from utility.letter_report.deploymentV1.letter_generator import letter_gen
from utility.letter_report.deploymentV1.ingest_trf_letter import run_full_ingestion
from utility.letter_report.deploymentV1.letter_ingestor import main
from dotenv import load_dotenv
from projects.keyvault_load import *
import math

load_dotenv()

load_keyvault_secrets()

# -------------------------------
# Cosmos DB setup 
# -------------------------------
COSMOS_DB_URI = os.getenv("cosmos-db-url")
COSMOS_DB_KEY = os.getenv("cosmos-db-key")
COSMOS_DB_DATABASE = os.getenv("cosmos-db-database")
COSMOS_PROJECT_CONTAINER = os.getenv("cosmos-db-project-container")

cosmos_client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
db = cosmos_client.get_database_client(COSMOS_DB_DATABASE)
projects_container = db.get_container_client(COSMOS_PROJECT_CONTAINER)

BLOB_CONTAINER_NAME = os.getenv("blob-container")



def update_letter_progress(
    project_doc: dict,
    letter_stage: str,
    letter_percentage: int = 10,
    letter_step: str | None = None,
    error: str | None = None,
    last_updated: datetime | None = None,
    letter_completed: bool = False
):
    project_doc["Letter_Project_Progress"] = {
        "letter_stage": letter_stage,
        "letter_percentage": letter_percentage,
        "letter_step": letter_step,
        "last_updated": (last_updated or datetime.utcnow()).isoformat(),
        "error": error,
        "letter_completed": letter_completed
    }

    projects_container.upsert_item(project_doc)
    print(f" Progress updated → {letter_percentage}% | {letter_step}")



def sanitize_json(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_json(i) for i in obj]
    else:
        return obj


# ==========================================================
# MAIN LETTER PROCESSOR
# ==========================================================
def process_letter_direct(projectId: str, trf_urls, cdr_urls):
    try:
        blob_urls = []

        if trf_urls:
            blob_urls.extend(trf_urls if isinstance(trf_urls, list) else [trf_urls])

        if cdr_urls:
            blob_urls.extend(cdr_urls if isinstance(cdr_urls, list) else [cdr_urls])

        print('########################### trf_urls ############################', trf_urls)

        print('cdr_urls', cdr_urls)


        print("Letter worker started for:", projectId)

        query = "SELECT * FROM c WHERE c.Project_Id = @pid"
        params = [{"name": "@pid", "value": projectId}]

        items = list(
            projects_container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True
            )
        )

        if not items:
            raise Exception("Project not found")

        letter_progress = items[0].get("Letter_Project_Progress") or {}
        letter_percentage = letter_progress.get("letter_percentage", 0)

        if letter_percentage < 100:
            project_doc = items[0]

            update_letter_progress(
                project_doc,
                letter_stage="steps in Progress",
                letter_percentage=10,
                letter_step="Starting running Letter",
                letter_completed=False
            )

            Source_Doc_urls = [
                item["url"]
                for item in project_doc.get("Source_Doc", [])
                if "url" in item
            ]

            if not Source_Doc_urls:
                raise Exception("No Source_Doc URLs found")

            user_name = project_doc.get("User_Name") or ""
            first_name = user_name.split()[0]

            text_container = f"vectorstorecontainer_new_itk_text_{first_name}_{projectId}"
            image_container = f"vectorstorecontainer_new_itk_image_{first_name}_{projectId}"

            run_full_ingestion(
                projectId,
                Source_Doc_urls,
                text_container,
                image_container
            )

            blob_urls_trf = blob_urls + Source_Doc_urls

            f = main(projectId, blob_urls, text_container, image_container)

            if f:
                BASE_DIR = Path(__file__).resolve().parents[1]
                DATA_DIR = BASE_DIR / "data"
                project_dir = DATA_DIR / projectId
                project_dir.mkdir(parents=True, exist_ok=True)

                letter_json1 = project_dir / f"letter_body_iec_output_{projectId}.json"
                letter_json2 = project_dir / f"letter_header_iec_output_{projectId}.json"
                letter_docx_file = project_dir / f"letter_iec_output_{projectId}.docx"

                letter_json_path = BASE_DIR / "utility/letter_report/deploymentV1/letter.json"
                letter_header_json_path = BASE_DIR / "utility/letter_report/deploymentV1/letter_header.json"
                letter_template_docx = BASE_DIR / "utility/letter_report/deploymentV1/Letter_Template.docx"

                letter_src_files = BASE_DIR / "data" / projectId / "letter_src_files"
                trf_src_files = BASE_DIR / "data" / projectId / "trf_src_files"

                letter_gen(
                    blob_urls=blob_urls,
                    container_name=BLOB_CONTAINER_NAME,
                    src_files_dir=letter_src_files,
                    src_files_trf=trf_src_files,
                    letter_json_path=letter_json_path,
                    letter_header_json_path=letter_header_json_path,
                    letter_template_docx=letter_template_docx,
                    output_letter_docx=letter_docx_file,
                    letter_json_path_output=letter_json1,
                    letter_header_json_path_output=letter_json2,
                    project_Id=projectId,
                    blob_urls_trf=blob_urls_trf,
                    text_container=text_container,
                    image_container=image_container
                )

                save_local_jsons_and_docx_to_blob_and_cosmos_for_letter(
                    str(letter_json1),
                    str(letter_json2),
                    str(letter_docx_file),
                    project_id=projectId
                )

                update_letter_progress(
                    project_doc,
                    letter_stage="Completed",
                    letter_percentage=100,
                    letter_step="All steps completed",
                    letter_completed=True
                )
        
        print("Letter worker completed")

    except Exception:
        print(traceback.format_exc())
        raise
