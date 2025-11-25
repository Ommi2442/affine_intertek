
from fastapi import APIRouter, HTTPException, Body
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from projects.models import Project
from datetime import datetime
import uuid, os
from db.database import *
from fastapi import APIRouter, HTTPException
from db.database import COSMOS_DB_project_Container
from projects.models import Project
from azure.cosmos import exceptions
router = APIRouter()


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

@router.post("/create", status_code=201)
async def create_project(project: Project):
    try:
        project.id = str(uuid.uuid4())
        print("Database name used:", COSMOS_DB_project_Container)
        import time
        print("Container name used:", COSMOS_DB_project_Container)
        time.sleep(0)  # Simulate delay for debugging
        project.Project_Id = generate_project_id()
        COSMOS_DB_project_Container.create_item(project.dict())
        return standard_response("success", "Project created successfully", {"Cosmos_id": project.id, "Project_Id": project.Project_Id})
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
            c.Project_Id,c.Standard,c.Client_Name,c.Proj_Created_On,c.TRF_Generated,c.CDR_Generated,c.Letter_Generated FROM c
        """
        items = list(
            COSMOS_DB_project_Container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
        )
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
        print("Found item:", item)

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
