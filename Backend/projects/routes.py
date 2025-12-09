from fastapi import APIRouter, HTTPException, Depends, Body, Form
from typing import List
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from projects.models import Project
from datetime import datetime
import uuid, os
from fastapi import Depends
from api.auth.jwt_auth.utils import get_current_user
from db.database import *
from fastapi import APIRouter, HTTPException
from db.database import COSMOS_DB_project_Container, COSMOS_DB_URI,COSMOS_DB_KEY,COSMOS_DB_DATABASE,COSMOS_DB_project_TRF_Container
from projects.models import Project,ProjectCreate,ProjectFilter
from azure.cosmos import exceptions
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
from fastapi import APIRouter, UploadFile, File, HTTPException
import json

router = APIRouter()

# CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=stintertekesusdev;AccountKey=YtSK+RvUKmkMRJDS8895whLoVFHf35yIMlBgOtqbXBvhdvPznk9fRbijQ5PeroYtn9AECeNL2uEw+AStV9/VUA==;EndpointSuffix=core.windows.net"
QUEUE_CONN_STR = "DefaultEndpointsProtocol=https;AccountName=stintertekesusdev;AccountKey=YtSK+RvUKmkMRJDS8895whLoVFHf35yIMlBgOtqbXBvhdvPznk9fRbijQ5PeroYtn9AECeNL2uEw+AStV9/VUA==;EndpointSuffix=core.windows.net"
# CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")
CONTAINER_NAME = "stintertekesusdev-blob"
client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
database = client.get_database_client(COSMOS_DB_DATABASE)
trf_container = database.get_container_client(COSMOS_DB_project_TRF_Container)
# QUEUE_NAME = os.getenv("AZURE_QUEUE_NAME")
QUEUE_NAME = "stintertekesusdev-queue"

CONTAINER_NAME = "stintertekesusdev-blob"
BLOB_PREFIX = "Documents"   # top-level folder in blob

blob_service = BlobServiceClient.from_connection_string(QUEUE_CONN_STR)
container_client = blob_service.get_container_client(CONTAINER_NAME)


queue_client = QueueClient.from_connection_string(
    conn_str=QUEUE_CONN_STR,
    queue_name=QUEUE_NAME
)



@router.post("/create")
async def create_project(payload: ProjectCreate):
    try:
        new_project = Project(
            id=str(uuid.uuid4()),
            Standard=payload.Standard,
            Project_Id=payload.Project_Id,
            Product=payload.Product,
            Client_Name=payload.Client_Name,
            Proj_Created_By=payload.Proj_Created_By,
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

        folders_to_create = [f"{base_path}/source_documents",f"{base_path}/TRF Templates",f"{base_path}/CDR Templates",f"{base_path}/Letters Templates",f"{base_path}/Standard Document"]
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

        # ----------------------------
        # Build Query Based on Role
        # ----------------------------
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
                c.TRF_Generated,
                c.CDR_Generated,
                c.Letter_Generated,
                c.Proj_Created_By
            FROM c
            WHERE c.Proj_Created_By = "{user_email}"
            """
        else:
            query = """
            SELECT 
                c.Project_Id,
                c.Standard,
                c.Client_Name,
                c.Product,
                c.Proj_Created_On,
                c.TRF_Generated,
                c.CDR_Generated,
                c.Letter_Generated,
                c.Proj_Created_By
            FROM c
            """

        # Execute query
        items = list(
            COSMOS_DB_project_Container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
        )

        return {
            "status": "success",
            "count": len(items),
            "user_role": user_role,
            "data": items
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
        items = list(COSMOS_DB_project_Container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        ))

        if not items:
            raise HTTPException(status_code=404, detail="Project not found")
        item = items[0]
        
        for key, value in update_data.items():
            item[key] = value
        updated_item = COSMOS_DB_project_Container.replace_item(
            item["id"], item, item["id"])
        return {
            "status": "success",
            "message": "Project updated successfully",
            "data": updated_item
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    try:
        props = COSMOS_DB_project_Container.read()
        pk_path = props["partitionKey"]["paths"][0]
        pk_name = pk_path.lstrip("/")             
        print("Partition key-name ->", pk_name)
        query = "SELECT * FROM c WHERE c.Project_Id = @pid"
        params = [{"name": "@pid", "value": project_id}]
        items = list(COSMOS_DB_project_Container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        ))
        if not items:
            raise HTTPException(status_code=404, detail="Project not found")
        item = items[0]
        COSMOS_DB_project_Container.delete_item(
            item=item["id"],
            partition_key=item[pk_name]
        )
        return {"status": "success", "message": "Project deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fetch-trf-reports")
async def fetch_trf_reports(project_id: str):
    try:
        #  Query Cosmos DB for all documents with this project_id
        query = "SELECT * FROM c WHERE c.project_id = @pid"
        parameters = [{"name": "@pid", "value": project_id}]

        items = list(trf_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))

        if not items:
            raise HTTPException(
                status_code=404,
                detail="No TRF reports found for this project_id"
            )

        # 🟢 Return only json + project_id
        return {
            "project_id": project_id,
            "reports": [
                {
                    "id": item["id"],
                    "filename": item.get("filename"),
                    "json": item.get("data"),
                    "uploaded_on": item.get("uploaded_on")
                }
                for item in items
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching TRF reports: {str(e)}"
        )




@router.post("/upload")
async def upload_files(
    projectId: str = Form(...),
    key: str = Form(...),
    files: List[UploadFile] = File(...)
):
    results = []
    uploaded_urls = []

    # ---------- 1) Upload all files to Blob ----------
    for file in files:
        original_name = os.path.basename(file.filename)
        blob_path = f"{BLOB_PREFIX}/{projectId}/{key}/{original_name}"
        blob_client = container_client.get_blob_client(blob_path)

        data = await file.read()
        blob_client.upload_blob(data, overwrite=True)
        blob_url = blob_client.url

        uploaded_urls.append({
            "filename": original_name,
            "blob_url": blob_url
        })

        results.append({
            "filename": original_name,
            "blob_url": blob_url,
            "queued": False   # Now queue is not file-level
        })

    # ---------- 2) Fetch Project Doc from Cosmos ----------
    query = f"SELECT * FROM c WHERE c.Project_Id = '{projectId}'"
    docs = list(COSMOS_DB_project_Container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    if not docs:
        raise HTTPException(status_code=404, detail="Project not found")

    project_doc = docs[0]

    # ---------- 3) Update Source_Doc ----------
    if "Source_Doc" not in project_doc:
        project_doc["Source_Doc"] = []

    for item in uploaded_urls:
        project_doc["Source_Doc"].append({
            "filename": item["filename"],
            "url": item["blob_url"],
            "uploaded_at": datetime.utcnow().isoformat()
        })

    COSMOS_DB_project_Container.upsert_item(project_doc)


    return {
        "status": "success",
        "message": "Files uploaded. Embedding triggered for project.",
        "uploaded": results,
        "cosmos_updated": True,
        "queue_triggered_for_project": projectId,
        "source_docs_count": len(project_doc["Source_Doc"])
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
            "status": "Pending",
            "percentage": 0
        }

    return {
        "status": progress.get("stage"),
        "percentage": progress.get("percentage"),
        "step": progress.get("step"),
        "error": progress.get("error")
    }



@router.post("/generate-trf")
def generate_trf(projectId: str):
    try:
        queue_client.send_message(json.dumps({
            "projectId": projectId,
            "action": "embed_generatetrf",
            "timestamp": datetime.utcnow().isoformat()
        }))

        return {
            "status": "success",
            "message": "TRF generation triggered",
            "projectId": projectId
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))