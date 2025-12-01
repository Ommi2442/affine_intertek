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
from projects.models import Project,ProjectCreate
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
CONTAINER_NAME = "testing-blob"
client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
database = client.get_database_client(COSMOS_DB_DATABASE)
container = database.get_container_client(COSMOS_DB_project_TRF_Container)
# QUEUE_NAME = os.getenv("AZURE_QUEUE_NAME")
QUEUE_NAME = "stintertekesusdev-queue"

CONTAINER_NAME = "testing-blob"
BLOB_PREFIX = "Documents"   # top-level folder in blob

blob_service = BlobServiceClient.from_connection_string(QUEUE_CONN_STR)
container_client = blob_service.get_container_client(CONTAINER_NAME)


queue_client = QueueClient.from_connection_string(
    conn_str=QUEUE_CONN_STR,
    queue_name=QUEUE_NAME
)




def generate_project_id():
    try:
        query = "SELECT c.Project_Id FROM c"
        items = list(COSMOS_DB_project_Container.query_items(query=query, enable_cross_partition_query=True))
        numbers = [int(''.join(filter(str.isdigit, item.get("Project_Id", "")))) for item in items if any(c.isdigit() for c in item.get("Project_Id", ""))]
        next_num = max(numbers) + 1 if numbers else 1
        return f"PRJ_{next_num:06d}"
    except Exception:
        return f"PRJ_000001"


def standard_response(status: str, message: str, data: dict = None):
    response = {"status": status, "message": message}
    if data is not None:
        response["data"] = data
    return response


@router.post("/create")
async def create_project(payload: ProjectCreate):
    try:
        new_project = Project(
            id=str(uuid.uuid4()),
            Project_Id=generate_project_id(),
            Standard=payload.Standard,
            Project_Name=payload.Project_Name,
            Product=payload.Product,
            Client_Name=payload.Client_Name,
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


@router.get("/all")
async def get_all_projects():
    try:
        query = """
        SELECT 
            c.Project_Id,
            c.Standard,
            c.Project_Name,
            c.Client_Name,
            c.Product,
            c.Proj_Created_On,
            c.TRF_Generated,
            c.CDR_Generated,
            c.Letter_Generated,
            c.Proj_Created_By
        FROM c
        """

        items = list(
            COSMOS_DB_project_Container.query_items(
                query=query,
                enable_cross_partition_query=True ))

        return {
            "status": "success",
            "count": len(items),
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

@router.post("/Trf-reports")
async def upload_json_file(
    file: UploadFile = File(...),
    project_id: str = Form(...)
):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are allowed")

    try:
        # Read JSON file
        contents = await file.read()
        json_content = json.loads(contents)

        # Prepare Cosmos DB document
        cosmos_item = {
            "id": str(uuid.uuid4()),           # Unique ID
            "project_id": project_id,          # Project ID from frontend
            "filename": file.filename,
            "data": json_content,
            "uploaded_on": datetime.utcnow().isoformat()
        }

        # Save to Cosmos DB
        container.upsert_item(cosmos_item)

        # ✅ Fetch from Cosmos DB after insert
        fetched_item = container.read_item(
            item=cosmos_item["id"],
            partition_key=cosmos_item["id"]   # Replace if partition key is different
        )

        # ✅ Return JSON + project ID to frontend
        return {
            "project_id": fetched_item["project_id"],
            "json": fetched_item["data"]
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON file"
        )



@router.post("/upload")
async def upload_files(
    projectId: str = Form(...),
    key: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Uploads multiple files to:
    testing-blob/Documents/{projectId}/{key}/{original_filename}
    and pushes queue messages for each file.
    """

    results = []

    for file in files:
        # ensure file.filename is safe — remove path segments if any
        original_name = os.path.basename(file.filename)

        # build blob path using original filename (overwrite=True)
        blob_path = f"{BLOB_PREFIX}/{projectId}/{key}/{original_name}"

        blob_client = container_client.get_blob_client(blob_path)

        data = await file.read()
        blob_client.upload_blob(data, overwrite=True)

        blob_url = blob_client.url

        # push message to queue for worker
        queue_message = {
            "projectId": projectId,
            "key": key,
            "filename": original_name,
            "blob_path": blob_path,
            "blob_url": blob_url,
            "timestamp": datetime.utcnow().isoformat()
        }

        queue_client.send_message(json.dumps(queue_message))

        results.append({
            "original_filename": original_name,
            "blob_path": blob_path,
            "blob_url": blob_url,
            "queued": True
        })

    return {"status": "success", "uploaded": results}
