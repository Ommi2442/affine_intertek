from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pathlib import Path
from azure.core.exceptions import ResourceNotFoundError

from fastapi import APIRouter, HTTPException, Depends, Body, Form, UploadFile, File, Query, logger, BackgroundTasks, status
import math
import traceback
from azure.storage.blob import ContainerClient
from typing import List
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from projects.models import Project
from datetime import datetime
import uuid, os
from fastapi import Depends
from api.auth.jwt_auth.utils import get_current_user
from db.database import *
from db.database import COSMOS_DB_project_Container, COSMOS_DB_URI,COSMOS_DB_KEY,COSMOS_DB_DATABASE,COSMOS_DB_project_TRF_Container,COSMOS_DB_project_CDR_Container,COSMOS_DB_project_LETTER_Container
from projects.models import Project,ProjectCreate,ProjectFilter,FinalizeReportPayload,LetterGeneration,RegenratePayload,LetterResult,CdrResult
from azure.cosmos import exceptions
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
import json
import time
from utility.json_to_blob import *
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import shutil
import requests
import tempfile          
import os
import base64
from docx2pdf import convert
from projects.helpers import *
from projects.keyvault_load import *
from utility.cdr_report.CDR_Pipelines.main import main2
from utility.cdr_report.CDR_Pipelines.compiler import fill_excel_from_json
from utility.cdr_report.CDR_Pipelines.configs import init_runtime, clear_runtime
from utility.letter_report.deploymentV1.letter_ingestor import main
from utility.letter_report.deploymentV1.letter_regenerator import rebuild_letter_docx_from_json
from utility.letter_report.deploymentV1.letter_generator import letter_gen
from utility.letter_report.deploymentV1.ingest_trf_letter import run_full_ingestion
from utility.cdr_report.CDR_Pipelines.configs import OUTPUT_EXCEL_AI_FINAL_PATH
from utility.json_to_blob import save_local_json_to_blob_and_cosmos,save_cdr_local_json_to_blob_and_cosmos_cdr,save_local_xlsx_to_blob_and_cosmos_cdr
save_local_jsons_and_docx_to_blob_and_cosmos_for_letter
import logging
from pathlib import Path
import asyncio
import threading
import traceback
import os
from dotenv import load_dotenv

load_dotenv()

load_keyvault_secrets()

print('blob-container', os.getenv("blob-container"))

BLOB_CONTAINER_NAME = os.getenv("blob-container")

router = APIRouter()

# Setup logging

logger = logging.getLogger(__name__)

CONNECTION_STRING = os.getenv("azure-conn-string")
print('CONNECTION_STRING', CONNECTION_STRING)
# CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=stintertekesusdev;AccountKey=YtSK+RvUKmkMRJDS8895whLoVFHf35yIMlBgOtqbXBvhdvPznk9fRbijQ5PeroYtn9AECeNL2uEw+AStV9/VUA==;EndpointSuffix=core.windows.net"
CONTAINER_NAME = os.getenv("blob-container")
print('CONTAINER_NAME', CONTAINER_NAME)
# CONTAINER_NAME = "stintertekesusdev-blob"

COSMOS_DB_URI = os.getenv("cosmos-db-url")
print('COSMOS_DB_URI', COSMOS_DB_URI)

COSMOS_DB_KEY = os.getenv("cosmos-db-key")
print('COSMOS_DB_KEY', COSMOS_DB_KEY)

COSMOS_DB_DATABASE = os.getenv("cosmos-db-database")
print('COSMOS_DB_DATABASE', COSMOS_DB_DATABASE)

COSMOS_DB_project_TRF_Container = os.getenv("cosmos-db-project-trf-container")
print('COSMOS_DB_project_TRF_Container', COSMOS_DB_project_TRF_Container)

client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
database = client.get_database_client(COSMOS_DB_DATABASE)
trf_container = database.get_container_client(COSMOS_DB_project_TRF_Container)


BLOB_PREFIX = "Documents"   # top-level folder in blob

container_client = blob_service.get_container_client(CONTAINER_NAME)


BASE_DIR = Path(__file__).resolve().parent

LOCAL_TRF_FOLDER = BASE_DIR / "data"

TOTAL_PARTS = 5
FILE_PREFIX = "pta_final_6_3_1_part"


CDR_WORKER_URL = "http://127.0.0.1:9000/run-cdr"
TRF_WORKER_URL = "http://127.0.0.1:9000/run-trf"

LETTER_WORKER_URL = "http://127.0.0.1:9000/run-letter"

@router.post("/create")
async def create_project(payload: ProjectCreate):
    try:
        new_project = Project(
            id=str(uuid.uuid4()),
            Standard=payload.Standard,
            Project_Id=payload.Project_Id,
            Product=payload.Product,
            Client_Name=payload.Client_Name,
            Proj_Archived=False,
            Proj_Created_By=payload.Proj_Created_By,
            User_Name=payload.User_Name,
            Proj_Created_On=str(datetime.utcnow()),
            
        )

        COSMOS_DB_project_Container.create_item(new_project.dict())
        
        def create_folder(folder_path: str):
            if not folder_path.endswith("/"):
                folder_path += "/"
            blob_client = container_client.get_blob_client(folder_path)
            blob_client.upload_blob(b"", overwrite=True)
            return folder_path

        base_path = f"Documents/{new_project.Project_Id}"
        folders_to_create = [f"{base_path}/source_documents",f"{base_path}/TRF Templates",f"{base_path}/CDR Templates",f"{base_path}/Letters Templates",f"{base_path}/Standard Document",f"{base_path}/Generated_trf_Report",f"{base_path}/Generated_cdr_Report",f"{base_path}/Citation_docs",f"{base_path}/letter_images"]
        created_folders = [create_folder(folder) for folder in folders_to_create]
        return {
            "status": "success",
            "message": "Project created successfully",
            "folders_created": created_folders,
            "data": {
                "id": new_project.id,
                "Project_Id": new_project.Project_Id,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}")
async def get_project(project_id: str):
    try:
        query = "SELECT * FROM c WHERE c.Project_Id = @pid"
        params = [{"name": "@pid", "value": project_id}]        
        items = list(
            COSMOS_DB_project_Container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True
            )
        )
        cdr_percent=items[0].get('CDR_Project_Progress',None)
        print("cdr_percent --- ",cdr_percent.get("cdr_percentage"))
        if not items:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"status": "success", "data": items[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/all")
async def get_all_projects(payload: ProjectFilter):
    try:
        user_role = payload.user_role
        user_email = payload.user_email

        # ---------------------------------------
        # ROLE-BASED QUERY
        # ---------------------------------------
        if user_role == 2:
            if not user_email:
                raise HTTPException(
                    status_code=400,
                    detail="user_email is required for role 2"
                )

            query = f"""
                SELECT 
                    c.Project_Id,
                    c.Standard,
                    c.Client_Name,
                    c.Product,
                    c.Proj_Created_On,
                    c.Proj_Created_By,
                    c.Proj_Archived,
                    c.Project_Progress,
                    c.CDR_Project_Progress,
                    c.Letter_Project_Progress
                FROM c
                WHERE c.Proj_Created_By = "{user_email}"
                AND c.Proj_Archived = false
                ORDER BY c.Proj_Created_On DESC
            """

        else:
            query = """
                SELECT 
                    c.Project_Id,
                    c.Standard,
                    c.Client_Name,
                    c.Product,
                    c.Proj_Created_On,
                    c.Proj_Created_By,
                    c.Proj_Archived,
                    c.Project_Progress,
                    c.CDR_Project_Progress,
                    c.Letter_Project_Progress
                FROM c
                WHERE c.Proj_Archived = false
                ORDER BY c.Proj_Created_On DESC
            """

        # ---------------------------------------
        # EXECUTE QUERY
        # ---------------------------------------
        items = list(
            COSMOS_DB_project_Container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
        )

        # ---------------------------------------
        # FORMAT RESPONSE
        # ---------------------------------------
        projects = []
        for p in items:
            progress = p.get("Project_Progress") or {}
            cdr_progress = p.get("CDR_Project_Progress") or {}
            letter_progress = p.get("Letter_Project_Progress") or {}
 
            projects.append({
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

                "cdr_percentage": cdr_progress.get("cdr_percentage",0),
                "cdr_step": cdr_progress.get("cdr_step"),
                "cdr_last_updated": cdr_progress.get("last_updated"),
                "cdr_error": cdr_progress.get("error"),
                "cdr_completed": cdr_progress.get("cdr_completed", "No"),

                "letter_percentage": letter_progress.get("letter_percentage", 0),
                "letter_step": letter_progress.get("letter_stage"),
                "letter_last_updated": letter_progress.get("last_updated"),
                "letter_error": letter_progress.get("error"),
                "letter_completed": letter_progress.get("letter_completed", "No")
            })

        return {
            "status": "success",
            "count": len(projects),
            "user_role": user_role,
            "data": projects
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.put("/{project_id}")
async def update_project(project_id: str, update_data: dict):
    try:
        props = COSMOS_DB_project_Container.read()
        pk_path = props["partitionKey"]["paths"][0]
        pk_name = pk_path.lstrip("/")

        query = "SELECT * FROM c WHERE c.Project_Id = @pid"
        params = [{"name": "@pid", "value": project_id}]

        items = list(
            COSMOS_DB_project_Container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True
            )
        )

        if not items:
            raise HTTPException(status_code=404, detail="Project not found")

        item = items[0]

        # protect system fields
        protected_fields = {"id", pk_name}
        for key, value in update_data.items():
            if key not in protected_fields:
                item[key] = value

        updated_item = COSMOS_DB_project_Container.replace_item(
            item["id"],
            item,
            item[pk_name]
        )

        return {
            "status": "success",
            "message": "Project updated successfully",
            "data": updated_item
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}")
async def update_project(project_id: str, update_data: dict):
    try:
        # Fetch container properties
        props = COSMOS_DB_project_Container.read()
        pk_path = props["partitionKey"]["paths"][0]
        pk_name = pk_path.lstrip("/")

        # Query project
        query = "SELECT * FROM c WHERE c.Project_Id = @pid"
        params = [{"name": "@pid", "value": project_id}]

        items = list(
            COSMOS_DB_project_Container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True
            )
        )

        if not items:
            raise HTTPException(status_code=404, detail="Project not found")

        item = items[0]

        # Prevent updating protected fields
        protected_fields = {"id", pk_name}
        for key, value in update_data.items():
            if key not in protected_fields:
                item[key] = value

        # Replace item with correct partition key
        updated_item = COSMOS_DB_project_Container.replace_item(
            item=item["id"],
            body=item,
            partition_key=item[pk_name]
        )

        return {
            "status": "success",
            "message": "Project updated successfully",
            "data": updated_item
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")



def delete_blob_folder(folder_path: str):
    if not folder_path.endswith("/"):
        folder_path += "/"
    blobs = container_client.list_blobs(name_starts_with=folder_path)
    deleted = False
    for blob in blobs:
        container_client.delete_blob(blob.name)
        deleted = True
    return deleted




def delete_local_project_folder(project_id: str) -> bool:
    """
    Deletes local project folder:
    <BASE_DIR>/data/<project_id>
    """
    BASE_DIR = Path(__file__).resolve().parent.parent
    TRF_DATA_DIR = BASE_DIR / "data" / project_id

    if not TRF_DATA_DIR.exists():
        return False

    if not TRF_DATA_DIR.is_dir():
        raise RuntimeError(f"Expected directory but found file: {TRF_DATA_DIR}")

    shutil.rmtree(TRF_DATA_DIR)
    return True



@router.delete("/{project_id}")
async def delete_project(project_id: str):
    try:
        deleted_project = delete_by_project_id(
            COSMOS_DB_project_Container, project_id
        )
        if deleted_project == 0:
            raise HTTPException(
                status_code=404,
                detail="Project not found in Project container"
            )
        deleted_trf = delete_by_project_id(
            COSMOS_DB_project_trf_Container, project_id
        )

        deleted_cdr = delete_by_project_id(
            COSMOS_DB_project_cdr_Container, project_id
        )

        delete_blob_folder(f"Documents/{project_id}")
        delete_local_project_folder(project_id)

        return {
            "status": "success",
            "message": "Project and related documents deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fetch-trf-reports")
async def fetch_trf_reports(
    project_id: str,
    file_type: str   # e.g. ".json", ".xlsx", ".pdf"
):
    try:
        # ---------------------------------------------------
        # COSMOS QUERY (FIXED)
        # ---------------------------------------------------
        query = """
            SELECT * FROM c
            WHERE c.project_id = @pid
            AND c.file_type = @file_type
        """

        parameters = [
            {"name": "@pid", "value": project_id},
            {"name": "@file_type", "value": file_type},
        ]

        items = list(
            trf_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )

        if not items:
            raise HTTPException(
                status_code=404,
                detail=f"No TRF reports found for project_id={project_id} and file_type={file_type}"
            )

        reports_output = []

        for item in items:
            filename = item.get("filename")
            blob_url = item.get("blob_url")

            local_path = LOCAL_TRF_FOLDER / project_id / filename
            json_data = None

            # ---------------------------------------------------
            # JSON FILE HANDLING
            # ---------------------------------------------------
            if file_type == ".json":
                # 1) Try local file
                if os.path.exists(local_path):
                    with open(local_path, "r", encoding="utf-8") as f:
                        json_data = json.load(f)
                else:
                    # 2) Fallback → Blob
                    if blob_url:
                        blob_client = BlobClient.from_blob_url(blob_url)
                        downloaded_bytes = blob_client.download_blob().readall()
                        json_data = json.loads(downloaded_bytes.decode("utf-8"))

            reports_output.append({
                "id": item["id"],
                "project_id": item.get("project_id"),
                "filename": filename,
                "file_type": item.get("file_type"),
                "uploaded_on": item.get("uploaded_on"),
                "json": json_data,      # only populated for .json
                "blob_url": blob_url,
                "blob_path": item.get("blob_path"),
            })

        return {
            "project_id": project_id,
            "file_type": file_type,
            "reports": reports_output
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching TRF reports: {str(e)}"
        )




def process_citation_documents(
    project_id: str,
    blob_service: BlobServiceClient,
    container_name: str,
):
    """
    SOURCE:
      Documents/{project_id}/source_documents/

    TARGET:
      Documents/{project_id}/Citation_docs/

    - Copies PDFs as-is
    - Converts DOC/DOCX to PDF
    """

    SOURCE_PREFIX = f"Documents/{project_id}/source_documents/"
    TARGET_PREFIX = f"Documents/{project_id}/Citation_docs/"

    

    container_client = blob_service.get_container_client(container_name)

    try:
        blobs = list(container_client.list_blobs(name_starts_with=SOURCE_PREFIX))
    except Exception as e:
        print("❌ Failed to list source documents:", str(e))
        return

    if not blobs:
        print("ℹ No source documents found")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        for blob in blobs:
            blob_name = blob.name
            filename = os.path.basename(blob_name)

            # ---------- SKIP FOLDER MARKERS ----------
            if not filename:
                continue

            filename_lower = filename.lower()

            try:
                blob_client = container_client.get_blob_client(blob_name)

                # =========================================================
                # CASE 1: PDF → COPY AS-IS
                # =========================================================
                if filename_lower.endswith(".pdf"):
                    target_blob_path = TARGET_PREFIX + filename
                    target_blob_client = container_client.get_blob_client(target_blob_path)

                    print("📄 Copying PDF:", filename)

                    # Server-side copy (NO download)
                    target_blob_client.start_copy_from_url(blob_client.url)
                    continue

                # =========================================================
                # CASE 2: DOC / DOCX → CONVERT TO PDF
                # =========================================================
                if filename_lower.endswith(".doc") or filename_lower.endswith(".docx"):
                    local_docx = os.path.join(tmpdir, filename)
                    pdf_name = os.path.splitext(filename)[0] + ".pdf"
                    local_pdf = os.path.join(tmpdir, pdf_name)

                    print("⬇ Downloading:", filename)
                    with open(local_docx, "wb") as f:
                        f.write(blob_client.download_blob().readall())

                    print("⚙ Converting:", filename)
                    convert_docx_to_pdf(local_docx, local_pdf)

                    target_blob_path = TARGET_PREFIX + pdf_name
                    target_blob_client = container_client.get_blob_client(target_blob_path)

                    with open(local_pdf, "rb") as f:
                        target_blob_client.upload_blob(f, overwrite=True)

                    print("✅ Uploaded converted PDF:", pdf_name)
                    continue

                # =========================================================
                # OTHER FILE TYPES → IGNORE
                # =========================================================
                print("⏭ Skipping unsupported file:", filename)

            except Exception as e:
                print("❌ Failed processing", filename, "→", str(e))

    print("✔ Citation processing completed:", project_id)





@router.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    projectId: str = Form(...),
    key: str = Form(...),
    files: list[UploadFile] = File(...),
):
    results = []
    uploaded_urls = []

    # ---------- 1) Upload files ----------
    for file in files:
        original_name = os.path.basename(file.filename)
        blob_path = f"{BLOB_PREFIX}/{projectId}/{key}/{original_name}"
        blob_client = container_client.get_blob_client(blob_path)

        data = await file.read()
        blob_client.upload_blob(data, overwrite=True)

        uploaded_urls.append({
            "filename": original_name,
            "blob_url": blob_client.url
        })

        results.append({
            "filename": original_name,
            "blob_url": blob_client.url,
            "queued": False
        })

    # ---------- 2) Cosmos Update ----------
    query = f"SELECT * FROM c WHERE c.Project_Id = '{projectId}'"
    docs = list(COSMOS_DB_project_Container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    if not docs:
        raise HTTPException(status_code=404, detail="Project not found")

    project_doc = docs[0]
    project_doc.setdefault("Source_Doc", [])

    for item in uploaded_urls:
        project_doc["Source_Doc"].append({
            "filename": item["filename"],
            "url": item["blob_url"],
            "uploaded_at": datetime.utcnow().isoformat()
        })

    COSMOS_DB_project_Container.upsert_item(project_doc)

    # ---------- 3) FIRE CONVERSION THREAD (NO WAIT) ----------
    threading.Thread(
        target=process_citation_documents,
        args=(projectId, blob_service, CONTAINER_NAME),
        daemon=True
    ).start()

    return {
            "status": "success",
            "message": "Files uploaded successfully",
            "files": results,
            "conversion": "citation docs conversion started",
            "cosmos_updated": True,
        }



@router.get("/check/{project_id}")
def check_project_id(project_id: str):
    query = "SELECT VALUE COUNT(1) FROM c WHERE c.Project_Id = @pid"
    params = [{"name": "@pid", "value": project_id}]

    result = list(COSMOS_DB_project_Container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    exists = result[0] > 0
    return {"exists": exists}



@router.get("/filesuploaded/{project_id}")
def get_project_details(project_id: str):
    query = """
        SELECT c.Project_Id, c.Source_Doc
        FROM c
        WHERE c.Project_Id = @pid
    """
    
    params = [{ "name": "@pid", "value": project_id }]

    result = list(COSMOS_DB_project_Container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    if not result:
        return {
            "projectId": project_id,
            "uploaded_files": []
        }

    item = result[0]

    print("result", result)

    return {
        "projectId": item.get("Project_Id"),
        "uploaded_files": item.get("Source_Doc", [])
    }



@router.delete("/filesdelete/{project_id}/{file_name}")
def delete_uploaded_file(project_id: str, file_name: str):

    # 1️⃣ Fetch project record from Cosmos DB
    query = """
        SELECT *
        FROM c
        WHERE c.Project_Id = @pid
    """
    params = [{"name": "@pid", "value": project_id}]

    items = list(
        COSMOS_DB_project_Container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        )
    )

    if not items:
        raise HTTPException(status_code=404, detail="Project not found")

    project_doc = items[0]

    # 2️⃣ Ensure Source_Doc exists
    source_docs = project_doc.get("Source_Doc", [])

    # 3️⃣ Remove file entry from Cosmos
    updated_docs = [
        f for f in source_docs
        if f.get("filename") != file_name
    ]

    if len(updated_docs) == len(source_docs):
        raise HTTPException(status_code=404, detail="File not found in Source_Doc")

    project_doc["Source_Doc"] = updated_docs

    # 4️⃣ Update Cosmos DB
    try:
        COSMOS_DB_project_Container.upsert_item(project_doc)
    except cosmos_exceptions.CosmosHttpResponseError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cosmos update failed: {str(e)}"
        )

    # 5️⃣ Delete file from Azure Blob Storage
    blob_path = f"Documents/{project_id}/source_documents/{file_name}"

    try:
        blob_client = blob_service.get_blob_client(
            container=CONTAINER_NAME,
            blob=blob_path
        )

        if blob_client.exists():
            blob_client.delete_blob()
        else:
            print("⚠️ Blob not found in storage:", blob_path)

    except Exception as e:
        # Do NOT fail API if blob deletion fails
        print("⚠️ Blob delete warning:", str(e))

    # 6️⃣ Success response
    return {
        "message": "File deleted successfully",
        "projectId": project_id,
        "deleted_file": file_name,
        "uploaded_files": updated_docs
    }




@router.get("/report/status")
def get_project_report_status(id: str):
    query = f"SELECT * FROM c WHERE c.Project_Id = '{id}'"
    docs = list(COSMOS_DB_project_Container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    if not docs:
        raise HTTPException(status_code=404, detail="Project not found")

    progress = docs[0].get("Project_Progress")

    if not progress:
        return {
            "trf_status": "Pending",
            "trf_percentage": 10,
            "trf_completed": 'No'
        }

    return {
        "trf_status": progress.get("trf_stage"),
        "trf_percentage": progress.get("trf_percentage"),
        "trf_step": progress.get("trf_step"),
        "trf_error": progress.get("trf_error"),
        "trf_completed": progress.get("trf_completed")
    }

@router.get("/report/status/cdr")
def get_project_report_status(id: str):
    query = f"SELECT * FROM c WHERE c.Project_Id = '{id}'"
    docs = list(COSMOS_DB_project_Container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    if not docs:
        raise HTTPException(status_code=404, detail="Project not found")

    cdr_progress = docs[0].get("CDR_Project_Progress")

    if not cdr_progress:
        return {
            "trf_status": "Pending",
            "trf_percentage": 10,
            "trf_completed": 'No'
        }
    

    return {
        "cdr_status":cdr_progress.get("cdr_stage"),
        "cdr_percentage": cdr_progress.get("cdr_percentage",0),
        "cdr_step": cdr_progress.get("cdr_step"),
        "cdr_error": cdr_progress.get("error"),
        "cdr_completed": cdr_progress.get("cdr_completed", "No"),

    }



# @router.post("/generate-trf")
# def generate_trf(projectId: str):
#     try:
#         queue_client.send_message(json.dumps({
#             "projectId": projectId,
#             "action": "embed_generatetrf",
#             "timestamp": datetime.utcnow().isoformat()
#         }))

#         MAX_WAIT_SECONDS = 6000
#         POLL_INTERVAL = 2
#         elapsed = 0

#         while elapsed < MAX_WAIT_SECONDS:
#             query = "SELECT * FROM c WHERE c.Project_Id = @pid"
#             params = [{"name": "@pid", "value": projectId}]

#             docs = list(projects_container.query_items(
#                 query=query,
#                 parameters=params,
#                 enable_cross_partition_query=True,
#             ))

#             if docs:
#                 progress = docs[0].get("Project_Progress") or {}
#                 percentage = progress.get("trf_percentage")

#                 if percentage == 100:
#                     break

#             time.sleep(POLL_INTERVAL)
#             elapsed += POLL_INTERVAL

#         if elapsed >= MAX_WAIT_SECONDS:
#             raise HTTPException(status_code=408, detail="TRF generation timed out")

#         response = load_trf_json_from_blob(projectId)
#         return response

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))




# @router.post("/generate-trf", status_code=202)
# def generate_trf(projectId: str):
#     """
#     Triggers TRF generation asynchronously.
#     Frontend must poll /trf-json-part for parts.
#     """
#     try:
#         queue_client.send_message(json.dumps({
#             "projectId": projectId,
#             "action": "embed_generatetrf",
#             "timestamp": datetime.utcnow().isoformat()
#         }))

#         return {
#             "projectId": projectId,
#             "status": "started",
#             "message": "TRF generation triggered. Fetch parts progressively."
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))




# @router.post("/generate-trf", status_code=202)
# def generate_trf(projectId: str):
#     """
#     Triggers TRF generation asynchronously.
#     Frontend must poll /trf-json-part for parts.
#     """
#     try:
#         project_id = event.get("projectId")
#         if not project_id:
#             print(" Missing projectId in queue message")
#             return True

#         print(f"📦 Processing project: {project_id}")

#         query = f"SELECT * FROM c WHERE c.Project_Id = '{project_id}'"
#         docs = list(
#             projects_container.query_items(
#                 query=query,
#                 enable_cross_partition_query=True,
#             )
#         )

#         if not docs:
#             print(f" Project not found: {project_id}")
#             return True

#         project_doc = docs[0]

#         source_docs = project_doc.get("Source_Doc") or []

#         blob_urls: list[str] = []
#         for doc in source_docs:
#             if isinstance(doc, dict) and "url" in doc:
#                 blob_urls.append(doc["url"])
#             else:
#                 print(f" Skipping invalid Source_Doc entry: {doc}")

#         if not blob_urls:
#             print(f" No valid source documents for project {project_id}")
#             return True
        
#         print(f"blob_urls source_docs------{blob_urls}")
#         print(f" Files to embed: {len(blob_urls)}")

#         user_name = project_doc.get("User_Name") or []
#         first_name = user_name.split()[0]
#         textDB_container_name = f"vectorstorecontainer_new_itk_text_{first_name}_{project_id}"
#         imageDB_container_name = f"vectorstorecontainer_new_itk_image_{first_name}_{project_id}"

#         # ---------------------------------------------------------
#         # DEFINE CALLBACK (MUST BE BEFORE TRF CALL)
#         # ---------------------------------------------------------
#         def on_first_json_ready():
#             print("🚀 EVENT: First TRF JSON has been generated")

#             update_project_progress(
#                 project_doc,
#                 trf_stage="First TRF JSON Generated",
#                 trf_percentage=30, 
#                 trf_step="Initial TRF JSON ready",
#                 trf_completed=False
#             )
        
#         try:
#             # Start at 10%
#             update_project_progress(
#                 project_doc,
#                 trf_stage="Indexing in Progress",
#                 trf_percentage=10,
#                 trf_step="Starting embedding",
#                 trf_completed=False
#             )
                    
#             ingest_files_from_blob_urls_create_embeddings(DOWNLOAD_DIR, blob_urls, project_id, textDB_container_name, imageDB_container_name)

#             print(f" Embeddings completed for project {project_id}")


#             project_data_dir = BASE_DIR / "data" / project_id

#             OUTPUT_JSON_PATH = DATA_DIR / project_id / "final_output.json"
#             OUTPUT_DOCX_PATH = DATA_DIR / project_id / "final_output.docx"

#             INPUT_FILES = DATA_DIR / "input_files"

#             INPUT_JSON_PATHS = [
#                 INPUT_FILES / filename
#                 for filename in INPUT_JSON_FILENAMES
#             ]


#             run_trf_generation(
#                 blob_urls,
#                 textDB_container_name,
#                 imageDB_container_name,
#                 input_docx_path=INPUT_DOCX_PATH,
#                 output_docx_path=OUTPUT_DOCX_PATH,
#                 base_pta_path=BASE_PTA_JSON_PATH,
#                 input_json_paths=INPUT_JSON_PATHS,
#                 project_data_dir=project_data_dir,
#                 batch_size=150,
#                 final_output_path=OUTPUT_JSON_PATH,
#                 cooldown_sec=15,
#                 max_workers=10,
#                 on_first_json_generated=on_first_json_ready,
#             )


#             print(f" TRF generation completed for project {project_id}")
            
#             save_local_json_to_blob_and_cosmos(str(OUTPUT_JSON_PATH),str(OUTPUT_DOCX_PATH),project_id=project_id,update_only=False)

#             # 100% completed
#             update_project_progress(
#                 project_doc,
#                 trf_stage="Completed",
#                 trf_percentage=100,
#                 trf_step="TRF generated and stored",
#                 trf_completed=True
#             )

#             print(f" Saving TRF Report to the Blob")
#             return {
#                 "projectId": projectId,
#                 "status": "started",
#                 "message": "TRF generation triggered. Fetch parts progressively."
#             }

#         except Exception as e:
#             print(f" Worker failed for project {project_id}: {e}")
#             raise HTTPException(status_code=500, detail=str(e))

#             update_project_progress(
#                 project_doc,
#                 trf_stage="Failed",
#                 trf_percentage=0,
#                 trf_step="Processing failed",
#                 error=str(e),
#                 trf_completed=False
#             )

#             return {
#                 "projectId": projectId,
#                 "status": "started",
#                 "message": "TRF generation triggered. Fetch parts progressively."
#             }


@router.post("/generate-trf", status_code=202)
def generate_trf(projectId: str):
    try:
        response = requests.post(
            TRF_WORKER_URL,
            json={"projectId": projectId},
            timeout=3
        )
        response.raise_for_status()

        return {
            "projectId": projectId,
            "status": "dispatched",
            "worker_port": 9000
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Worker unavailable: {e}"
        )


@router.get("/report/status")
def get_project_report_status(id: str):
    query = f"SELECT * FROM c WHERE c.Project_Id = '{id}'"
    docs = list(COSMOS_DB_project_Container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    if not docs:
        raise HTTPException(status_code=404, detail="Project not found")

    progress = docs[0].get("Project_Progress")

    if not progress:
        return {
            "trf_status": "Pending",
            "trf_percentage": 10,
            "trf_completed": 'No'
        }

    return {
        "trf_status": progress.get("trf_stage"),
        "trf_percentage": progress.get("trf_percentage"),
        "trf_step": progress.get("trf_step"),
        "trf_error": progress.get("trf_error"),
        "trf_completed": progress.get("trf_completed")
    }



def update_project_progress_CDR(
    project_doc: dict,
    cdr_stage: str,
    cdr_percentage: int,
    cdr_step: str | None = None,
    error: str | None = None,
    last_updated: datetime | None = None,
    cdr_completed: bool = False
):
    project_doc["CDR_Project_Progress"] = {
        "cdr_stage": cdr_stage,
        "cdr_percentage": cdr_percentage,
        "cdr_step": cdr_step,
        "last_updated": (last_updated or datetime.utcnow()).isoformat(),
        "error": error,
        "cdr_completed": cdr_completed
    }

    projects_container.upsert_item(project_doc)
    print(f" Progress updated → {cdr_percentage}% | {cdr_stage} --- {cdr_completed}")


# @router.post("/generate-cdr")
# def generate_cdr(projectId: str):
#     try:
#         if not projectId:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="projectId is required"
#             )
        
#         if not projectId:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="projectId is required"
#             )
#         project_id=projectId
#         query = "SELECT * FROM c WHERE c.Project_Id = @pid"
#         params = [{"name": "@pid", "value": project_id}]        
#         items = list(
#             COSMOS_DB_project_Container.query_items(
#                 query=query,
#                 parameters=params,
#                 enable_cross_partition_query=True
#             )
#         )
#         cdr_progress = items[0].get("CDR_Project_Progress") or {}
#         print(cdr_progress,"------ ",type(cdr_progress))

#         cdr_percentage = cdr_progress.get("cdr_percentage", 0)
#         print(cdr_percentage,"------ ",type(cdr_percentage))
#         if cdr_percentage < 100:
#             query = f"SELECT * FROM c WHERE c.Project_Id = '{project_id}'"
#             docs = list(
#                 COSMOS_DB_project_Container.query_items(
#                     query=query,
#                     enable_cross_partition_query=True,
#                 )
#             )

#             print('docs', docs)


#             project_doc = docs[0]
#             update_project_progress_CDR(
#                 project_doc,
#                 cdr_stage="steps in Progress",
#                 cdr_percentage=10,
#                 cdr_step="Starting runnig CDR",
#                 cdr_completed=False
#             )
#             ############### QUEUE LOGIC (COMMENTED) ################
#             # queue_client_cdr.send_message(json.dumps({
#             #     "projectId": projectId,
#             #     "action": "CDR_Generation",
#             #     "timestamp": datetime.utcnow().isoformat()
#             # }))
#             #
#             # MAX_WAIT_SECONDS = 6000
#             # POLL_INTERVAL = 2
#             # elapsed = 0
#             #
#             # while elapsed < MAX_WAIT_SECONDS:
#             #     query = "SELECT * FROM c WHERE c.Project_Id = @pid"
#             #     params = [{"name": "@pid", "value": projectId}]
#             #
#             #     docs = list(projects_container.query_items(
#             #         query=query,
#             #         parameters=params,
#             #         enable_cross_partition_query=True,
#             #     ))
#             #
#             #     if docs:
#             #         progress = docs[0].get("CDR_Project_Progress") or {}
#             #         percentage = progress.get("cdr_percentage")
#             #
#             #         if percentage == 100:
#             #             break
#             #
#             #     time.sleep(POLL_INTERVAL)
#             #     elapsed += POLL_INTERVAL
#             #
#             # if elapsed >= MAX_WAIT_SECONDS:
#             #     raise HTTPException(status_code=408, detail="CDR generation timed out")
#             ############### QUEUE LOGIC END #######################


#             # ------------------ COSMOS QUERY ------------------
#             query = "SELECT c.blob_url FROM c WHERE c.project_id = @pid"
#             params = [{"name": "@pid", "value": projectId}]

#             try:
#                 items = list(trf_container.query_items(
#                     query=query,
#                     parameters=params,
#                     enable_cross_partition_query=True,
#                 ))
#             except Exception:
#                 raise HTTPException(
#                     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                     detail="Failed to query project data from database"
#                 )

#             if not items:
#                 raise HTTPException(
#                     status_code=status.HTTP_404_NOT_FOUND,
#                     detail=f"Project '{projectId}' not found"
#                 )

#             blob_url = items[0].get("blob_url")
#             if not blob_url or not isinstance(blob_url, str):
#                 raise HTTPException(
#                     status_code=status.HTTP_404_NOT_FOUND,
#                     detail="CDR Blob URL not found or invalid"
#                 )

#             response = requests.get(blob_url)
#             response.raise_for_status()
#             trf_filled = response.json()

#             BASE_DIR = Path(__file__).resolve().parents[1]  # Backend/
#             DATA_DIR = BASE_DIR / "data"
#             DATA_DIR.mkdir(parents=True, exist_ok=True)

#             project_dir = DATA_DIR / projectId
#             project_dir.mkdir(parents=True, exist_ok=True)

#             output_json_path = project_dir / f"iec_output_cdr_{projectId}.json"
#             output_excel_path = project_dir / f"iec_output_sheet_{projectId}.xlsx"

#             user_name = project_doc.get("User_Name") or []
#             user_id = user_name.split()[0]

#             # ------------------ PIPELINE ------------------
#             result = main2(project_id,
#                 user_id,
#                 trf_filled,
#                 output_excel_path=output_excel_path
#             )

#             # ------------------ SAVE JSON ------------------
#             with open(output_json_path, "w", encoding="utf-8") as f:
#                 json.dump(result, f, indent=2, ensure_ascii=False)

#             save_cdr_local_json_to_blob_and_cosmos_cdr(
#                 output_json_path,
#                 projectId
#             )
#             print("----- JSON CDR uploaded -----")
            
#             # ------------------ UPLOAD EXCEL ------------------
#             save_local_xlsx_to_blob_and_cosmos_cdr(
#                 str(output_excel_path),
#                 projectId
#             )
#             print("----- Excel CDR uploaded -----")

#             update_project_progress_CDR(
#                 project_doc,
#                 cdr_stage="Completed",
#                 cdr_percentage=100,
#                 cdr_step="CDR generated and stored",
#                 cdr_completed=True
#             )
#             print("#################")
#             return {
#                 "message": "CDR Report generated successfully",
#                 "projectId": projectId,
#                 "data": result
#             }
#         if cdr_percentage==100:
#             print("----CDR is already generated-----")
#             BASE_DIR = Path(__file__).resolve().parents[1]  # Backend/
#             DATA_DIR = BASE_DIR / "data"
#             DATA_DIR.mkdir(parents=True, exist_ok=True)

#             project_dir = DATA_DIR / projectId
#             project_dir.mkdir(parents=True, exist_ok=True)

#             output_json_path = project_dir / f"iec_output_cdr_{projectId}.json"
#             output_excel_path = project_dir / f"iec_output_sheet_{projectId}.xlsx"


#             output_json_path = project_dir / f"iec_output_cdr_{projectId}.json"
#             with open(output_json_path, "r", encoding="utf-8") as f:
#                 cdr_output = json.load(f)
            
#             return {
#                 "message": "CDR Report Already Generated ",
#                 "projectId": projectId,
#                 "data": cdr_output
#             }

#     except HTTPException:
#         raise

#     except Exception as e:
#         h=traceback.format_exc()
#         print(h)
#         logger.exception("Unhandled error in generate_cdr API")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=str(e)
#         )


@router.get("/download-file")
def download_file(project_id: str,report_type:str):
    report_type=report_type.lower()
    if report_type=='trf':
        docx_path = download_docx_from_local(project_id)
        file_like = open(docx_path, "rb")
        return StreamingResponse(
            file_like,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="final_output_{project_id}.docx"',
                "Content-Length": str(docx_path.stat().st_size)
            })
    elif report_type == "cdr":
        blob_path = (
            f"Documents/{project_id}/Generated_cdr_Report/"
            f"iec_output_sheet_{project_id}.xlsx")

        blob_client = blob_service.get_blob_client(
            container=blob_container,
            blob=blob_path
        )

        if not blob_client.exists():
            raise HTTPException(
                status_code=404,
                detail=f"XLSX file not found at {blob_path}"
            )
        stream = blob_client.download_blob()

        return StreamingResponse(
            stream.chunks(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="iec_output_sheet_{project_id}.xlsx"'
            }
        )
    elif report_type == "letter":
            blob_path = f"Documents/{project_id}/Letters Templates/letter_iec_output_{project_id}.docx"

            blob_client = blob_service.get_blob_client(
                container=blob_container,
                blob=blob_path
            )

            if not blob_client.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Word file not found at {blob_path}"
                )

            stream = blob_client.download_blob()

            return StreamingResponse(
                stream.chunks(),  # or stream.readall() if chunks() causes issues
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f'attachment; filename="letter_iec_output_{project_id}.docx"'
                }
            )


@router.get("/pdf-proxy")
def pdf_proxy(
    url: str = Query(..., description="Azure Blob PDF URL")
):
    try:
        resp = requests.get(
            url,
            headers={
                # Azure Blob compatibility
                "x-ms-version": "2020-10-02"
            },
            timeout=30
        )

        resp.raise_for_status()

        # -------- STRICT PDF VALIDATION --------
        content_type = resp.headers.get("content-type", "")
        if "pdf" not in content_type.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Not a PDF. Content-Type: {content_type}"
            )

        return Response(
            content=resp.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "inline",
                "Cache-Control": "no-store"
            }
        )

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))



@router.get("/project-pdfs-load")
def get_project_pdfs(project_id: str = Query(...)):
    try:
        # ------------------ FETCH PROJECT (VALIDATION ONLY) ------------------
        query = "SELECT * FROM c WHERE c.Project_Id = @pid"
        items = list(
            COSMOS_DB_project_Container.query_items(
                query=query,
                parameters=[{"name": "@pid", "value": project_id}],
                enable_cross_partition_query=True
            )
        )

        if not items:
            raise HTTPException(status_code=404, detail="Project not found")

        pdf_outputs = []

        # ------------------ LIST BLOBS FROM CITATION_DOCS ------------------
        prefix = f"Documents/{project_id}/Citation_docs/"

        container_client = blob_service.get_container_client(CONTAINER_NAME)

        blobs = container_client.list_blobs(name_starts_with=prefix)

        for blob in blobs:
            file_name = blob.name.split("/")[-1]

            if not file_name.lower().endswith(".pdf"):
                continue

            blob_client = blob_service.get_blob_client(
                container=CONTAINER_NAME,
                blob=blob.name
            )

            downloader = blob_client.download_blob()
            pdf_bytes = downloader.readall()

            pdf_outputs.append({
                "filename": file_name,
                "data": base64.b64encode(pdf_bytes).decode()
            })

        # ------------------ RESPONSE (INDEXEDDB COMPATIBLE) ------------------
        return JSONResponse({
            "project_id": project_id,
            "pdfs": pdf_outputs
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/trf-json-part")
def get_trf_json_part(
    project_id: str = Query(...),
    part_index: int = Query(..., ge=1),
):
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data" / project_id

    # --------------------------------------------------
    # FINAL MERGED JSON (requested AFTER last part)
    # --------------------------------------------------
    if part_index == TOTAL_PARTS + 1:
        final_path = DATA_DIR / "final_output.json"

        if not final_path.exists():
            return {
                "project_id": project_id,
                "part_index": part_index,
                "status": "processing",
                "json_data": None,
                "is_last": True,
                "is_final": True,
            }

        with open(final_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {
            "project_id": project_id,
            "part_index": part_index,
            "status": "completed",
            "json_data": data,
            "is_last": True,
            "is_final": True,
        }

    # --------------------------------------------------
    # SPLIT PART JSONS (1..5)
    # --------------------------------------------------
    if part_index > TOTAL_PARTS:
        return {
            "project_id": project_id,
            "part_index": part_index,
            "status": "invalid",
            "json_data": None,
            "is_last": True,
        }

    file_path = DATA_DIR / f"{FILE_PREFIX}{part_index}_output.json"

    if not file_path.exists():
        return {
            "project_id": project_id,
            "part_index": part_index,
            "status": "processing",
            "json_data": None,
            "is_last": False,
        }

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "project_id": project_id,
        "part_index": part_index,
        "status": "completed",
        "json_data": data,
        "is_last": part_index == TOTAL_PARTS,
    }



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




# @router.post("/letter-generation")
# async def letter_implementation(payload: LetterGeneration):
#     try:
#         projectId = payload.projectId
#         trf_urls = payload.trf_urls
#         cdr_urls = payload.cdr_urls
#         # other_urls = payload.other_urls

        
#         blob_urls = [
#             trf_urls,
#             cdr_urls,
#             # other_urls
#         ]

#         print("Project ID for Letter Generation:", projectId,type(projectId))
#         print("All URLs for Letter Generation:", blob_urls)

#         if not projectId:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="projectId is required"
#             )

#         # ----------------------------------
#         # Cosmos DB query
#         # ----------------------------------
#         project_id = projectId
#         query = "SELECT * FROM c WHERE c.Project_Id = @pid"
#         params = [{"name": "@pid", "value": project_id}]

#         items = list(
#             COSMOS_DB_project_Container.query_items(
#                 query=query,
#                 parameters=params,
#                 enable_cross_partition_query=True
#             )
#         )

#         if not items:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Project not found"
#             )

#         letter_progress = items[0].get("Letter_Project_Progress") or {}
#         letter_percentage = letter_progress.get("letter_percentage", 0)

#         if letter_percentage < 100:
#             query = f"SELECT * FROM c WHERE c.Project_Id = '{project_id}'"
#             docs = list(
#                 projects_container.query_items(
#                     query=query,
#                     enable_cross_partition_query=True,
#                 )
#             )

#             if not docs:
#                 raise HTTPException(
#                     status_code=404,
#                     detail="Project document not found"
#                 )

#             project_doc = docs[0]

#             update_letter_progress(
#                 project_doc,
#                 letter_stage="steps in Progress",
#                 letter_percentage=10,
#                 letter_step="Starting running Letter",
#                 letter_completed=False
#             )

#             Source_Doc_urls = [
#                 item["url"]
#                 for item in project_doc.get("Source_Doc", [])
#                 if "url" in item
#             ]
#             if not Source_Doc_urls:
#                 raise HTTPException(
#                     status_code=400,
#                     detail="No Source_Doc URLs found for this project"
#                 )
#             print("Source Document URLs for Letter Generation:\n\n\n", Source_Doc_urls)
#             import time;time.sleep(10)
#             print("Starting full ingestion for Letter Generation...")
#             user_name = project_doc.get("User_Name") or ""
#             first_name = user_name.split()[0]

#             text_container = f"vectorstorecontainer_new_itk_text_{first_name}_{project_id}"
#             image_container = f"vectorstorecontainer_new_itk_image_{first_name}_{project_id}"
#             import time;time.sleep(10)
#             print("Starting full ingestion for Letter Generation...")
#             run_full_ingestion(project_id,Source_Doc_urls,text_container,image_container)
#             blob_urls_trf=blob_urls+ Source_Doc_urls
#             print("Blob URLs for Letter Generation after ingestion:", blob_urls_trf)
#             f=main(projectId,blob_urls,text_container,image_container)
            
#             if f:
#                 BASE_DIR = Path(__file__).resolve().parents[1]
#                 DATA_DIR = BASE_DIR / "data"
#                 project_dir = DATA_DIR / projectId
#                 project_dir.mkdir(parents=True, exist_ok=True)
#                 letter_json1 = project_dir / f"letter_body_iec_output_{projectId}.json"
#                 letter_json2 = project_dir / f"letter_header_iec_output_{projectId}.json"
#                 letter_docx_file = project_dir / f"letter_iec_output_{projectId}.docx"
                
#                 letter_json_path = BASE_DIR / "utility" / "letter_report" / "deploymentV1" / "letter.json"
#                 letter_header_json_path = BASE_DIR / "utility" / "letter_report" / "deploymentV1" / "letter_header.json"
#                 letter_template_docx = BASE_DIR / "utility" / "letter_report" / "deploymentV1" / "Letter_Template.docx"

#                 letter_src_files = BASE_DIR / "data" / projectId / "letter_src_files"

#                 trf_src_files = BASE_DIR / "data" / projectId / "trf_src_files"
                
#                 g=letter_gen(
#                 blob_urls=blob_urls,
#                 container_name=BLOB_CONTAINER_NAME,
#                 src_files_dir=letter_src_files,
#                 src_files_trf=trf_src_files,  
                
#                 letter_json_path=letter_json_path,
#                 letter_header_json_path=letter_header_json_path,
#                 letter_template_docx=letter_template_docx,

#                 output_letter_docx=letter_docx_file,
#                 letter_json_path_output=letter_json1,
#                 letter_header_json_path_output=letter_json2,
#                 project_Id=projectId,
#                 blob_urls_trf=blob_urls_trf,
#                 text_container=text_container,
#                 image_container=image_container)

#                 print("----- Saving Letter JSON and DOCX to Blob and CosmosDB -----")
                
#                 save_local_jsons_and_docx_to_blob_and_cosmos_for_letter(
#                                     str(letter_json1),
#                                     str(letter_json2),
#                                     str(letter_docx_file),
#                                     project_id=project_id
#                                     )
                
#                 update_letter_progress(
#                 project_doc,
#                 letter_stage="Completed",
#                 letter_percentage=100,
#                 letter_step="All steps completed",
#                 letter_completed=False
#             )
                
#                 with open(letter_json1, "r", encoding="utf-8") as f:
#                     letter_header_json_data = json.load(f)
#                 with open(letter_json2, "r", encoding="utf-8") as f:
#                     letter_body_json_data = json.load(f)
                

#                 letter_header_json_data = sanitize_json(letter_header_json_data)
#                 letter_body_json_data = sanitize_json(letter_body_json_data)
            
#                 return  {
#                     "status":"success",
#                     "project_Id":project_id,
#                     "Message":"Letter Generated Successfully",
#                     "Data":{
#                         "Letter_json_body":letter_body_json_data,
#                         "Letter_header_json":letter_header_json_data
#                     }
#                 }

#         if letter_percentage == 100:
#             BASE_DIR = Path(__file__).resolve().parents[1]
#             DATA_DIR = BASE_DIR / "data"
#             project_dir = DATA_DIR / projectId
#             project_dir.mkdir(parents=True, exist_ok=True)
#             letter_json1 = project_dir / f"letter_body_iec_output_{projectId}.json"
#             letter_json2 = project_dir / f"letter_header_iec_output_{projectId}.json"
#             letter_docx_file = project_dir / f"letter_iec_output_{projectId}.docx"
            
#             with open(letter_json2, "r", encoding="utf-8") as f:
#                 letter_json_data = json.load(f)
            
#             with open(letter_json1, "r", encoding="utf-8") as f:
#                 letter_header_json_data = json.load(f)
            
#             letter_json_data = sanitize_json(letter_json_data)
#             letter_header_json_data = sanitize_json(letter_header_json_data)
#             return {
#                 "status":"success",
#                 "project_Id":project_id,
#                 "Message":"Letter Already Generated",
#                 "Data":{
#                         "Letter_json_body":letter_json_data,
#                         "Letter_header_json":letter_header_json_data
#                     }
#             }   
            
#     except Exception as e:
#         print(traceback.format_exc())
#         return {
#             "status":"Failed",
#             "Message":"Letter Generation Code Failed"
#         }



@router.post("/letter-result")
def get_letter_result(payload: LetterResult):
    projectId = payload.projectId
    BASE_DIR = Path(__file__).resolve().parents[1]
    DATA_DIR = BASE_DIR / "data"
    project_dir = DATA_DIR / projectId

    query = "SELECT c.Letter_Project_Progress FROM c WHERE c.Project_Id = @pid"
    params = [{"name": "@pid", "value": projectId}]

    items = list(
        projects_container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        )
    )

    letter_status_data = items[0].get("Letter_Project_Progress", {})

    letter_percentage = letter_status_data['letter_percentage']

    if letter_percentage == 100:
        BASE_DIR = Path(__file__).resolve().parents[1]
        DATA_DIR = BASE_DIR / "data"
        project_dir = DATA_DIR / projectId
        # project_dir.mkdir(parents=True, exist_ok=True)
        print('project_dir',project_dir)
        letter_json1 = project_dir / f"letter_body_iec_output_{projectId}.json"
        letter_json2 = project_dir / f"letter_header_iec_output_{projectId}.json"
        letter_docx_file = project_dir / f"letter_iec_output_{projectId}.docx"
        
        with open(letter_json2, "r", encoding="utf-8") as f:
            letter_json_data = json.load(f)
        
        with open(letter_json1, "r", encoding="utf-8") as f:
            letter_header_json_data = json.load(f)
        
        letter_json_data = sanitize_json(letter_json_data)
        letter_header_json_data = sanitize_json(letter_header_json_data)
        
        return {
            "status":"success",
            "project_Id":projectId,
            "Message":"Letter Report Loaded",
            "Data":{
                    "Letter_json_body":letter_json_data,
                    "Letter_header_json":letter_header_json_data
                }
        }  



@router.post("/letter-generation", status_code=202)
def letter_implementation(payload: LetterGeneration):
    try:
        print('**** letter-generation *****', payload.trf_urls)
        response = requests.post(
            LETTER_WORKER_URL,  
            json={
                "projectId": payload.projectId,
                "trf_urls": payload.trf_urls,
                "cdr_urls": payload.cdr_urls,
            },
            timeout=3
        )
        response.raise_for_status()

        return {
            "projectId": payload.projectId,
            "status": "dispatched",
            "worker_port": 9000
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Worker unavailable: {e}"
        )




@router.post("/letter-status")
def get_letter_status(payload: LetterResult):
    projectId = payload.projectId
    query = "SELECT c.Letter_Project_Progress FROM c WHERE c.Project_Id = @pid"
    params = [{"name": "@pid", "value": projectId}]

    items = list(
        projects_container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        )
    )

    if not items:
        raise HTTPException(status_code=404, detail="Project not found")

    return items[0].get("Letter_Project_Progress", {})






def delete_by_project_id(container, project_id):
    props = container.read()
    pk_path = props["partitionKey"]["paths"][0]
    pk_name = pk_path.lstrip("/")

    query = """
    SELECT * FROM c
    WHERE c.project_id = @pid OR c.Project_Id = @pid
    """
    params = [{"name": "@pid", "value": project_id}]

    items = list(container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    if not items:
        return 0

    for item in items:
        container.delete_item(
            item=item["id"],
            partition_key=item[pk_name]
        )
    return len(items)


@router.post("/upload_trf")
async def upload_files(
    background_tasks: BackgroundTasks,
    projectId: str = Form(...),
    files: list[UploadFile] = File(...),
):
    uploaded_urls = []
    folder_path = f"{BLOB_PREFIX}/{projectId}/user_uploaded_TRF_file"
 
    # Upload files to Blob Storage
    for file in files:
        filename = os.path.basename(file.filename)
        blob_path = f"{folder_path}/{filename}"
        blob_client = container_client.get_blob_client(blob_path)
 
        data = await file.read()
        blob_client.upload_blob(data, overwrite=True)
 
        uploaded_urls.append({
            "filename": filename,
            "blob_url": blob_client.url
        })
 
    if not uploaded_urls:
        raise HTTPException(status_code=400, detail="No files uploaded")
 
    # Fetch project document
    query = f"SELECT * FROM c WHERE c.Project_Id = '{projectId}'"
    docs = list(
        COSMOS_DB_project_Container.query_items(
            query=query,
            enable_cross_partition_query=True
        )
    )
 
    if not docs:
        raise HTTPException(status_code=404, detail="Project not found")
 
    project_doc = docs[0]
 
    # Ensure User_uploaded_trf exists
    if "User_uploaded_trf" not in project_doc or project_doc["User_uploaded_trf"] is None:
        project_doc["User_uploaded_trf"] = []
 
    now = datetime.utcnow().isoformat()
 
    # Soft-delete existing active records
    for record in project_doc["User_uploaded_trf"]:
        if record.get("Deleted_At") is None:
            record["Deleted_At"] = now
 
    # Insert new uploads as active records
    for item in uploaded_urls:
        project_doc["User_uploaded_trf"].append({
            "filename": item["filename"],
            "url": item["blob_url"],
            "uploaded_at": now,
            "Deleted_At": None
        })
 
    COSMOS_DB_project_Container.upsert_item(project_doc)
 
    background_tasks.add_task(
        process_citation_documents,
        projectId,
        blob_service,
        CONTAINER_NAME
    )
 
    first_file = uploaded_urls[0]
 
    return {
        "status": "success",
        "message": "Files uploaded successfully for TRF",
        "filename": first_file["filename"],
        "blob_url": first_file["blob_url"]
    }


@router.post("/upload_cdr")
async def upload_files(
    background_tasks: BackgroundTasks,
    projectId: str = Form(...),
    files: list[UploadFile] = File(...),
):
    uploaded_urls = []
    folder_path = f"{BLOB_PREFIX}/{projectId}/user_uploaded_CDR_file"
 
    # Upload files to Blob Storage
    for file in files:
        filename = os.path.basename(file.filename)
        blob_path = f"{folder_path}/{filename}"
        blob_client = container_client.get_blob_client(blob_path)
 
        data = await file.read()
        blob_client.upload_blob(data, overwrite=True)
 
        uploaded_urls.append({
            "filename": filename,
            "blob_url": blob_client.url
        })
 
    if not uploaded_urls:
        raise HTTPException(status_code=400, detail="No files uploaded")
 
    # Fetch project document
    query = f"SELECT * FROM c WHERE c.Project_Id = '{projectId}'"
    docs = list(
        COSMOS_DB_project_Container.query_items(
            query=query,
            enable_cross_partition_query=True
        )
    )
 
    if not docs:
        raise HTTPException(status_code=404, detail="Project not found")
 
    project_doc = docs[0]
 
    # Ensure User_uploaded_cdr exists
    if "User_uploaded_cdr" not in project_doc or project_doc["User_uploaded_cdr"] is None:
        project_doc["User_uploaded_cdr"] = []
 
    now = datetime.utcnow().isoformat()
 
    # Soft-delete existing active records
    for record in project_doc["User_uploaded_cdr"]:
        if record.get("Deleted_At") is None:
            record["Deleted_At"] = now
 
    # Insert new uploads as active records
    for item in uploaded_urls:
        project_doc["User_uploaded_cdr"].append({
            "filename": item["filename"],
            "url": item["blob_url"],
            "uploaded_at": now,
            "Deleted_At": None
        })
 
    # Save back to Cosmos DB
    COSMOS_DB_project_Container.upsert_item(project_doc)
 
    # Background processing
    background_tasks.add_task(
        process_citation_documents,
        projectId,
        blob_service,
        CONTAINER_NAME
    )
 
    first_file = uploaded_urls[0]
 
    return {
        "status": "success",
        "message": "Files uploaded successfully for CDR ",
        "filename": first_file["filename"],
        "blob_url": first_file["blob_url"]
    }




@router.post("/finalize_report/trf")
async def finalize_trf_report(payload: FinalizeReportPayload):
    project_id = payload.projectId
    updated_data = payload.data

    if not project_id:
        raise HTTPException(400, "projectId is required")

    if not isinstance(updated_data, dict):
        raise HTTPException(400, "data must be a valid JSON object")

    container_trf = COSMOS_DB_project_trf_Container
    record = fetch_final_json_record(container_trf, project_id)
    blob_path = record["blob_path"]

    replace_json_blob(
        blob_service=blob_service,
        container_name=CONTAINER_NAME,
        blob_path=blob_path,
        json_data=updated_data
    )

    replace_local_final_json(project_id, updated_data)

    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    INPUT_DOCX_PATH = DATA_DIR / "input_files" / "input.docx"
    OUTPUT_JSON_PATH = DATA_DIR / project_id / "final_output.json"
    OUTPUT_DOCX_PATH = DATA_DIR / project_id / "final_output.docx"

    save_local_json_to_blob_and_cosmos(
        str(OUTPUT_JSON_PATH),
        str(OUTPUT_DOCX_PATH),
        project_id=project_id,
        update_only=True
    )

    update_docx_from_existing_json(
        input_docx_path=INPUT_DOCX_PATH,
        input_json_path=OUTPUT_JSON_PATH,
        output_docx_path=OUTPUT_DOCX_PATH,
        projectId=project_id
    )

    return {
        "status": "success",
        "reportType": "TRF",
        "projectId": project_id,
        "blob_url": record.get("blob_url")
    }



@router.post("/finalize_report/cdr")
async def finalize_cdr_report(payload: FinalizeReportPayload):
    project_id = payload.projectId
    updated_data = payload.data

    if not project_id:
        raise HTTPException(400, "projectId is required")

    if not isinstance(updated_data, dict):
        raise HTTPException(400, "data must be a valid JSON object")

    container = COSMOS_DB_project_CDR_Container
    container_cdr = COSMOS_DB_project_cdr_Container

    BASE_DIR = Path(__file__).resolve().parents[1]
    DATA_DIR = BASE_DIR / "data" / project_id
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    record = fetch_final_json_record(container_cdr, project_id)
    blob_url = record["blob_url"]

    OUTPUT_JSON_PATH = DATA_DIR / f"iec_output_cdr_{project_id}.json"
    OUTPUT_JSON_PATH_LOCAL = DATA_DIR / f"iec_output_cdr_{project_id}_updated.json"

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, indent=2, ensure_ascii=False)

    save_local_json_to_blob_and_cosmos_cdr(
        str(OUTPUT_JSON_PATH),
        project_id=project_id,
        update_only=True
    )

    updated_json_data = fetch_json_from_blob(blob_url)
    with open(OUTPUT_JSON_PATH_LOCAL, "w", encoding="utf-8") as f:
        json.dump(updated_json_data, f, indent=2, ensure_ascii=False)

    output_excel_path = DATA_DIR / f"iec_output_sheet_{project_id}.xlsx"

    query = f"SELECT * FROM c WHERE c.Project_Id = '{project_id}'"
    docs = list(
        projects_container.query_items(
            query=query,
            enable_cross_partition_query=True,
        )
    )
    project_doc = docs[0]
    user_name = project_doc.get("User_Name") or ""
    user_id = user_name.strip().split()[0] if user_name else None

    init_runtime(project_id=project_id, user_id=user_id)
    fill_excel_from_json(updated_json_data, str(output_excel_path))

    cosmos_item = save_local_xlsx_to_blob_and_cosmos_cdr(
        str(output_excel_path),
        project_id
    )

    clear_runtime(project_id=project_id, user_id=user_id)

    if not cosmos_item:
        raise HTTPException(500, "CDR Excel upload failed")

    final_record = fetch_final_json_record(container, project_id)

    return {
        "status": "success",
        "reportType": "CDR",
        "projectId": project_id,
        "blob_url": final_record.get("blob_url")
    }



@router.post("/finalize_report/letter")
async def finalize_letter_report(payload: FinalizeReportPayload):
    project_id = payload.projectId
    updated_data = payload.data

    if not project_id:
        raise HTTPException(400, "projectId is required")

    if not isinstance(updated_data, dict):
        raise HTTPException(400, "data must be a valid JSON object")

    container = COSMOS_DB_project_LETTER_Container
    print(" container -----  ",container)
    print(" container -----  ",COSMOS_DB_project_LETTER_Container)
    record = fetch_final_json_record(container, project_id)
    blob_url = record["blob_url"]

    BASE_DIR = Path(__file__).resolve().parents[1]
    DATA_DIR = BASE_DIR / "data"
    project_dir = DATA_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    non_conforming_images_dir = DATA_DIR / project_id / "non_conforming_images"

    letter_template_path = (
        BASE_DIR / "utility" / "letter_report" / "deploymentV1" / "Letter_Template.docx"
    )

    local_body_json = project_dir / f"letter_body_iec_output_{project_id}.json"
    local_header_json = project_dir / f"letter_header_iec_output_{project_id}.json"
    output_docx = project_dir / f"letter_iec_output_{project_id}.docx"

    body = updated_data["Letter_header_json"]
    header = updated_data["Letter_json_body"]

    with open(local_body_json, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2, ensure_ascii=False)

    with open(local_header_json, "w", encoding="utf-8") as f:
        json.dump(header, f, indent=2, ensure_ascii=False)

    rebuild_letter_docx_from_json(
        letter_json_path=local_body_json,
        letter_header_json_path=local_header_json,
        letter_template_docx=letter_template_path,
        output_letter_docx=output_docx,
        temp_image_dir=non_conforming_images_dir
    )

    save_local_jsons_and_docx_to_blob_and_cosmos_for_letter(
        str(local_body_json),
        str(local_header_json),
        str(output_docx),
        project_id=project_id
    )

    return {
        "status": "success",
        "reportType": "LETTER",
        "projectId": project_id,
        "blob_url": blob_url
    }


def update_trf_project_progress(
    project_doc: dict,
    trf_stage: str,
    trf_percentage: int = 0,
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

    COSMOS_DB_project_Container.upsert_item(project_doc)
    print(f" Progress updated → {trf_percentage}% | {trf_stage}")



@router.post("/trf-regenrate-reset")
async def regenrate_clear(payload: RegenratePayload):
    try:
        project_id = payload.projectId
        trf_report_entry_delete = delete_by_project_id(
            COSMOS_DB_project_trf_Container, project_id
        )

        delete_blobs_inside_folder(f"Documents/{project_id}/Generated_trf_Report/",container_client)

        delete_local_project_outputs(project_id,"TRF")

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

        update_trf_project_progress(
            project_doc,
            trf_stage="TRF Regnerate Initiated",
            trf_percentage=0,
            trf_step="TRF Regnerate Clicked",
            trf_completed=False
        )

        return {
            "status": "success",
            "message": "TRF Regenrate Files Cleanup done successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/cdr-regenrate-reset")
async def regenrate_clear(payload: RegenratePayload):
    try:
        project_id = payload.projectId
        cdr_report_entry_delete = delete_by_project_id(
            COSMOS_DB_project_CDR_Container, project_id
        )

        delete_blobs_inside_folder(f"Documents/{project_id}/Generated_cdr_Report/",container_client)

        delete_local_project_outputs(project_id,"CDR")

        query = f"SELECT * FROM c WHERE c.Project_Id = '{project_id}'"
        docs = list(
            projects_container.query_items(
                query=query,
                enable_cross_partition_query=True,
            )
        )

        project_doc = docs[0]

        update_project_progress_CDR(
            project_doc,
            cdr_stage="CDR Regnerate Initiated",
            cdr_percentage=0,
            cdr_step="CDR Regnerate Clicked",
            cdr_completed=False
        )

        return {
            "status": "success",
            "message": "CDR Regenrate Files Cleanup done successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/letter-regenrate-reset")
async def regenrate_clear(payload: RegenratePayload):
    try:
        project_id = payload.projectId
        letter_report_entry_delete = delete_by_project_id(
            COSMOS_DB_project_LETTER_Container, project_id
        )

        delete_blobs_inside_folder(f"Documents/{project_id}/Letters Templates/",container_client)

        delete_local_project_outputs(project_id,"LETTER")

        query = f"SELECT * FROM c WHERE c.Project_Id = '{project_id}'"
        docs = list(
            projects_container.query_items(
                query=query,
                enable_cross_partition_query=True,
            )
        )

        project_doc = docs[0]

        update_letter_progress(
            project_doc,
            letter_stage="Letter Regnerate Initiated",
            letter_percentage=0,
            letter_step="Letter Regnerate Clicked",
            letter_completed=False
        )

        return {
            "status": "success",
            "message": "Letter Regenrate Files Cleanup done successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/upload_images")
async def upload_images(
    background_tasks: BackgroundTasks,
    projectId: str = Form(...),
    files: list[UploadFile] = File(...),
    report_type: str = Form(...),
):
    report_type = report_type.lower()

    if report_type not in {"trf", "cdr","letter"}:
        raise HTTPException(400, "Invalid report_type")

    uploaded_urls = []

    
    user_upload_key = f"User_uploaded_{report_type}_images"

    folder_path = f"{BLOB_PREFIX}/{projectId}/user_uploded_images/{report_type}"

    for file in files:
        filename = os.path.basename(file.filename)
        blob_path = f"{folder_path}/{filename}"
        blob_client = container_client.get_blob_client(blob_path)

        data = await file.read()
        blob_client.upload_blob(data, overwrite=True)

        uploaded_urls.append({
            "filename": filename,
            "blob_url": blob_client.url
        })

    if not uploaded_urls:
        raise HTTPException(status_code=400, detail="No files uploaded")

    query = f"SELECT * FROM c WHERE c.Project_Id = '{projectId}'"
    docs = list(
        COSMOS_DB_project_Container.query_items(
            query=query,
            enable_cross_partition_query=True
        )
    )

    if not docs:
        raise HTTPException(status_code=404, detail="Project not found")

    project_doc = docs[0]

    
    if user_upload_key not in project_doc:
        project_doc[user_upload_key] = []

    now = datetime.utcnow().isoformat()

    
    for record in project_doc[user_upload_key]:
        if record.get("Deleted_At") is None:
            record["Deleted_At"] = now


    for item in uploaded_urls:
        project_doc[user_upload_key].append({
            "filename": item["filename"],
            "url": item["blob_url"],
            "uploaded_at": now,
            "Deleted_At": None
        })

    COSMOS_DB_project_Container.upsert_item(project_doc)
    first_file = uploaded_urls[0]

    return {
        "status": "success",
        "message": f"Image uploaded successfully for {report_type.upper()}",
        "filename": first_file["filename"],
        "blob_url": first_file["blob_url"]
    }




@router.post("/generate-cdr", status_code=202)
def generate_cdr(projectId: str):
    try:
        response = requests.post(
            CDR_WORKER_URL,
            json={"projectId": projectId},
            timeout=3
        )
        response.raise_for_status()

        return {
            "projectId": projectId,
            "status": "dispatched",
            "worker_port": 9000
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Worker unavailable: {e}"
        )



@router.get("/report/status/cdr")
def get_project_report_status(id: str):
    query = f"SELECT * FROM c WHERE c.Project_Id = '{id}'"
    docs = list(COSMOS_DB_project_Container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    if not docs:
        raise HTTPException(status_code=404, detail="Project not found")

    cdr_progress = docs[0].get("CDR_Project_Progress")

    if not cdr_progress:
        return {
            "cdr_status": "Pending",
            "cdr_percentage": 10,
            "cdr_completed": 'No'
        }
    

    return {
        "cdr_status":cdr_progress.get("cdr_stage"),
        "cdr_percentage": cdr_progress.get("cdr_percentage",0),
        "cdr_step": cdr_progress.get("cdr_step"),
        "cdr_error": cdr_progress.get("error"),
        "cdr_completed": cdr_progress.get("cdr_completed", "No"),

    }


@router.post("/cdr-result")
def get_letter_result(payload: CdrResult):
    projectId = payload.projectId
    query = "SELECT * FROM c WHERE c.Project_Id = @pid"
    params = [{"name": "@pid", "value": projectId}]        
    items = list(
        COSMOS_DB_project_Container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        )
    )
    cdr_progress = items[0].get("CDR_Project_Progress") or {}
    cdr_percentage = cdr_progress.get("cdr_percentage", 0)
    if cdr_percentage==100:
        BASE_DIR = Path(__file__).resolve().parents[1]  # Backend/
        DATA_DIR = BASE_DIR / "data"
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        project_dir = DATA_DIR / projectId
        project_dir.mkdir(parents=True, exist_ok=True)

        output_json_path = project_dir / f"iec_output_cdr_{projectId}.json"

        output_json_path = project_dir / f"iec_output_cdr_{projectId}.json"
        with open(output_json_path, "r", encoding="utf-8") as f:
            cdr_output = json.load(f)
        
        return {
            "message": "CDR Report Already Generated ",
            "projectId": projectId,
            "data": cdr_output
        }
    else:
        return {
            "message": "CDR Report Not Generated",
            "projectId": projectId
            
        }
