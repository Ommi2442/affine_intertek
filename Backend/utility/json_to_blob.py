import os
from azure.storage.blob import BlobServiceClient
from pathlib import Path
from openpyxl import load_workbook
from pathlib import Path
from datetime import datetime
import uuid
import mimetypes
from azure.storage.blob import ContentSettings


import traceback
import logging
from pathlib import Path
import mimetypes
import uuid
from datetime import datetime
from azure.storage.blob import BlobServiceClient

import json
import uuid
from datetime import datetime
from pathlib import Path
from azure.storage.blob import BlobClient
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
import os
from pathlib import Path
from pathlib import Path
from datetime import datetime
import uuid
import mimetypes
import os
from azure.storage.blob import BlobServiceClient
from pathlib import Path

from db.database import COSMOS_DB_project_LETTER_Container,COSMOS_DB_project_TRF_Container,COSMOS_DB_project_CDR_Container

from fastapi import HTTPException
from dotenv import load_dotenv
load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONN_STRING")
blob_container = os.getenv("BLOB_CONTAINER")
blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
COSMOS_DB_URI=os.getenv("COSMOS_DB_URI")
COSMOS_DB_KEY=os.getenv("COSMOS_DB_KEY")
COSMOS_DB_DATABASE=os.getenv("COSMOS_DB_DATABASE")

# Cosmos DB
cosmos_client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
database  = cosmos_client.get_database_client(COSMOS_DB_DATABASE)
trf_container = COSMOS_DB_project_TRF_Container
cdr_container = COSMOS_DB_project_CDR_Container


def save_local_json_to_blob_and_cosmos(
    json_file_path: str,
    docx_file_path: str,
    project_id: str,
    update_only: bool = False
) -> list:
    """
    Uploads JSON and DOCX to Blob Storage.

    Modes:
    - update_only = False (default):
        Upload + create Cosmos DB records
    - update_only = True:
        Overwrite existing blobs ONLY (no Cosmos updates)

    Returns:
    - List of result dictionaries
    """

    results = []

    for file_path in [json_file_path, docx_file_path]:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() not in (".json", ".docx"):
            raise ValueError("Only .json and .docx files allowed")

        # ---------- filename ----------
        filename = f"{path.stem}_{project_id}{path.suffix}"

        # ---------- blob path ----------
        blob_path = f"Documents/{project_id}/Generated_trf_Report/{filename}"

        blob_client = blob_service.get_blob_client(
            container=blob_container,
            blob=blob_path
        )

        # ---------- validate JSON ----------
        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                json.load(f)  # ensure valid JSON

        # ---------- content type ----------
        content_type, _ = mimetypes.guess_type(path.name)
        content_type = content_type or "application/octet-stream"

        # ---------- update-only safety ----------
        if update_only and not blob_client.exists():
            raise FileNotFoundError(
                f"Cannot update missing blob: {blob_path}"
            )

        # ---------- upload (overwrite always) ----------
        with open(path, "rb") as f:
            blob_client.upload_blob(
                f,
                overwrite=True,
                content_type=content_type
            )

        result = {
            "project_id": project_id,
            "filename": filename,
            "file_type": path.suffix.lower(),
            "blob_path": blob_path,
            "blob_url": blob_client.url,
            "status": "updated" if update_only else "created"
        }

        # ---------- cosmos write (CREATE MODE ONLY) ----------
        if not update_only:
            cosmos_item = {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "filename": filename,
                "file_type": path.suffix.lower(),
                "blob_path": blob_path,
                "blob_url": blob_client.url,
                "uploaded_on": datetime.utcnow().isoformat() + "Z"
            }

            trf_container.create_item(cosmos_item)
            result["cosmos_id"] = cosmos_item["id"]

        results.append(result)

    return results


def fetch_json_from_blob(blob_url: str) -> dict:
    """
    Downloads a JSON file from Azure Blob Storage using its URL
    and returns its content as a Python dictionary.
    """
    try:
        # Create a blob client directly from the URL
        blob_client = BlobClient.from_blob_url(blob_url)

        # Download the blob content
        stream = blob_client.download_blob()
        json_bytes = stream.readall()

        # Convert bytes → JSON object
        json_data = json.loads(json_bytes.decode("utf-8"))

        return json_data
    except Exception as e:
        error_details = traceback.format_exc()
        logger.exception("Unhandled error in generate_trf API")
        print("\n===== FULL TRACEBACK START =====")
        print(error_details)
        print("===== FULL TRACEBACK END =====\n")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )



def load_trf_json_from_blob(project_id):
    
    # Get the record from Cosmos DB
    query = "SELECT * FROM c WHERE c.project_id = @pid"
    params = [{"name": "@pid", "value": project_id}]

    items = list(trf_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))

    if not items:
        raise HTTPException(status_code=404, detail="Project not found")

    item = items[0]
    blob_url = item.get("blob_url")

    if not blob_url:
        raise HTTPException(status_code=400, detail="Blob URL not found in record")

    # Fetch JSON from Blob Storage
    json_data = fetch_json_from_blob(blob_url)


    # Return to frontend
    return {
        "status": "success",
        "project_id": project_id,
        "filename": item["filename"],
        "data": json_data
    }



def download_docx_from_local(project_id: str) -> Path:
    BASE_DIR = Path(__file__).resolve().parent.parent
    docx_path = BASE_DIR / "data" / project_id / "final_output.docx"

    if not docx_path.exists():
        raise HTTPException(status_code=404, detail="DOCX file not found")

    if docx_path.stat().st_size == 0:
        raise HTTPException(status_code=500, detail="DOCX file is empty")

    return docx_path


def save_cdr_local_json_to_blob_and_cosmos_cdr(json_file_path, project_id) -> list:
    """
    Uploads JSON files to Blob Storage and creates corresponding Cosmos DB items.
    Returns a list of Cosmos DB item dictionaries.
    """

    cosmos_items = []

    for file_path in [json_file_path]:
        print("\n\nProcessing file:", file_path)

        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() != ".json":
            raise ValueError("Only .json files are allowed")

        # ---------- generate filename ----------
        filename = path.stem  + path.suffix

        print("Modified filename after adding project ID:", filename)

        
        blob_path = f"Documents/{project_id}/Generated_cdr_Report/{filename}"

        
        blob_client = blob_service.get_blob_client(
            container=blob_container,
            blob=blob_path
        )

        content_type, _ = mimetypes.guess_type(path.name)
        content_type = content_type or "application/octet-stream"

        
        try:
            with open(path, "rb") as f:
                blob_client.upload_blob(
                    f,
                    overwrite=True,
                    content_type=content_type
                )
        except Exception as e:
            print(f"Failed to upload {filename} to blob: {e}")
            raise

        # ---------- create Cosmos DB item ----------
        cosmos_item = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "filename": filename,
            "file_type": path.suffix.lower(),
            "blob_path": blob_path,
            "blob_url": blob_client.url,
            "uploaded_on": datetime.utcnow().isoformat() + "Z"
        }

        try:
            cdr_container.create_item(cosmos_item)
            print(f"Cosmos item created for {filename}")
        except Exception as e:
            print(f"Failed to save {filename} metadata to Cosmos DB: {e}")
            raise

        cosmos_items.append(cosmos_item)

    print(f"\nTotal {len(cosmos_items)} files uploaded and saved to Cosmos.")
    return cosmos_items



def finalize_cdr_report_to_blob_and_cosmos_cdr(project_id, updated_data: dict):
    try:
        cdr_container = database.get_container_client(COSMOS_PROJECT_CDR_CONTAINER)
        query = "SELECT * FROM c WHERE c.project_id = @pid"
        params = [{"name": "@pid", "value": project_id}]
        items = list(cdr_container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        ))
        if not items:
            raise HTTPException(status_code=404, detail="Project not found")
        item = items[0]

        filename = item.get("filename")
        blob_url=item.get("blob_url")
        if not filename:
            raise HTTPException(status_code=400, detail="File not found in record")
        
        blob_path = f"Documents/{project_id}/Generated_cdr_Report/{filename}"
        print("Blob pathh---- ",blob_path)
        blob_client = blob_service.get_blob_client(container=blob_container, blob=blob_path)
        
        json_bytes = json.dumps(updated_data, indent=2).encode("utf-8")

        blob_client.upload_blob(json_bytes, overwrite=True)
        item["last_updated"] = str(datetime.utcnow())
        cdr_container.upsert_item(item)

        return blob_path,blob_url

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def save_local_xlsx_to_blob_and_cosmos_cdr(xlsx_file_path: str, project_id: str) -> list:
    cosmos_items = []

    path = Path(xlsx_file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() != ".xlsx":
        raise ValueError("Only .xlsx files are allowed")

    filename = path.name
    blob_path = f"Documents/{project_id}/Generated_cdr_Report/{filename}"

    blob_client = blob_service.get_blob_client(
        container=blob_container,
        blob=blob_path
    )

    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    with path.open("rb") as f:
        blob_client.upload_blob(
            f,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
        )
    
    cosmos_item = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "filename": filename,
        "file_type": ".xlsx",
        "blob_path": blob_path,
        "blob_url": blob_client.url,
        "uploaded_on": datetime.utcnow().isoformat() + "Z"
    }

    cdr_container.create_item(cosmos_item)
    cosmos_items.append(cosmos_item)
    return cosmos_items



def save_local_json_to_blob_and_cosmos_cdr(
    json_file_name: str,
    project_id: str,
    update_only: bool = False
) -> dict:
    
    path = Path(json_file_name)
    print("json_file_name --- ",json_file_name)
    # ---------- existence check ----------
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # ---------- allowed file type ----------
    if path.suffix.lower() != ".json":
        raise ValueError("Only .json files are allowed")

    # ---------- filename ----------
    filename = path.name
    print("Filename:", filename)

    # ---------- correct blob folder for CDR ----------
    blob_path = f"Documents/{project_id}/Generated_cdr_Report/{filename}"
    blob_client = blob_service.get_blob_client(
        container=blob_container,
        blob=blob_path
    )
    with open(path, "r", encoding="utf-8") as f:
        json.load(f)
    content_type = "application/json"

    if update_only and not blob_client.exists():
        raise FileNotFoundError(f"Cannot update missing blob: {blob_path}")

    with open(path, "rb") as f:
        blob_client.upload_blob(
            f,
            overwrite=True,
            content_type=content_type
        )

    result = {
        "project_id": project_id,
        "filename": filename,
        "file_type": "json",
        "blob_path": blob_path,
        "blob_url": blob_client.url,
        "status": "updated" if update_only else "created"
    }

    if not update_only:
        cosmos_item = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "filename": filename,
            "file_type": "json",
            "blob_path": blob_path,
            "blob_url": blob_client.url,
            "uploaded_on": datetime.utcnow().isoformat() + "Z"
        }
        cdr_container.create_item(cosmos_item)
        result["cosmos_id"] = cosmos_item["id"]

    return result


def save_local_jsons_and_docx_to_blob_and_cosmos_for_letter(
    json_file_path_1: str,
    json_file_path_2: str,
    docx_file_path: str,
    project_id: str
) -> list:
    try:
        results = []

        file_paths = [
            json_file_path_1,
            json_file_path_2,
            docx_file_path
        ]

        for file_path in file_paths:
            print("\n\nProcessing file:", file_path)
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            if path.suffix.lower() not in (".json", ".docx"):
                raise ValueError("Only .json and .docx files allowed")

            # ---------- filename logic ----------
            stem = path.stem
            print("Original filename stem:", stem)

            if stem.endswith(f"_{project_id}"):
                filename = f"{stem}{path.suffix}"
            else:
                filename = f"{stem}_{project_id}{path.suffix}"

            print("Modified filename after adding project ID:", filename)

            # ---------- blob path ----------
            blob_path = f"Documents/{project_id}/Letters Templates/{filename}"

            blob_client = blob_service.get_blob_client(
                container=blob_container,
                blob=blob_path
            )

            # ---------- validate JSON ----------
            if path.suffix.lower() == ".json":
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)

            # ---------- content type ----------
            content_type, _ = mimetypes.guess_type(path.name)
            content_type = content_type or "application/octet-stream"

            # ---------- check blob existence ----------
            blob_exists = blob_client.exists()

            # ---------- upload (create or update) ----------
            with open(path, "rb") as f:
                blob_client.upload_blob(
                    f,
                    overwrite=True,
                    content_type=content_type
                )

            status = "updated" if blob_exists else "created"

            result = {
                "project_id": project_id,
                "filename": filename,
                "file_type": path.suffix.lower(),
                "blob_path": blob_path,
                "blob_url": blob_client.url,
                "status": status
            }

            # ---------- create cosmos record ONLY if new blob ----------
            if not blob_exists:
                cosmos_item = {
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "filename": filename,
                    "file_type": path.suffix.lower(),
                    "blob_path": blob_path,
                    "blob_url": blob_client.url,
                    "uploaded_on": datetime.utcnow().isoformat() + "Z"
                }

                COSMOS_DB_project_LETTER_Container.create_item(cosmos_item)
                print("\n-----\n", cosmos_item)
                print(f"Cosmos item created for {filename}")

                result["cosmos_id"] = cosmos_item["id"]

            results.append(result)

        print("Results:", results)
        return results

    except Exception:
        print(traceback.format_exc())
        raise




