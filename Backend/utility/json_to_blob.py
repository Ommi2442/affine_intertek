import json
import uuid
from datetime import datetime
from pathlib import Path

from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
import os



# Blob Storage
AZURE_STORAGE_CONNECTION_STRING = 'BlobEndpoint=https://stintertekesusdev.blob.core.windows.net/;QueueEndpoint=https://stintertekesusdev.queue.core.windows.net/;FileEndpoint=https://stintertekesusdev.file.core.windows.net/;TableEndpoint=https://stintertekesusdev.table.core.windows.net/;SharedAccessSignature=sv=2024-11-04&ss=bfqt&srt=sco&sp=rwdlacupiytfx&se=2025-12-11T18:54:56Z&st=2025-12-01T10:39:56Z&spr=https&sig=D4MdeDfdffB3VflWgmJLIHhXlk5pwf4Rn3SRxypt%2B2U%3D'
blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
blob_container = 'stintertekesusdev-blob'

COSMOS_DB_URI="https://csdb-intertek-esus-dev.documents.azure.com:443/"
COSMOS_DB_KEY="azcUeVxFxoYoFkChvWI8Wr8lMijOuWXDYQsvMf6O2LmT0Uv3Zs7lDPiXSxWYOjq00MFDbK88ApotACDbODLFXA=="
COSMOS_DB_DATABASE="intertek_poc_dev"
COSMOS_PROJECT_TRF_CONTAINER="Project_TRF"

# Cosmos DB
cosmos_client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
database  = cosmos_client.get_databa4se_client(COSMOS_DB_DATABASE)
container = database.get_container_client(COSMOS_PROJECT_TRF_CONTAINER)



def save_local_json_to_blob_and_cosmos(
    file_path: str,
    project_id: str
) -> dict:
    """
    Reads a local JSON file, uploads it to Blob Storage,
    and stores the blob URL in Cosmos DB
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() != ".json":
        raise ValueError("Only .json files are allowed")

    filename = path.name

    # ---------- 1. Read local JSON ----------
    with open(path, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    # ---------- 2. Upload to Blob ----------
    blob_path = f"{project_id}/{filename}"
    blob_client = blob_service.get_blob_client(
        container=blob_container,
        blob=blob_path
    )

    with open(path, "rb") as file_bytes:
        blob_client.upload_blob(
            file_bytes,
            overwrite=True,
            content_type="application/json"
        )

    blob_url = blob_client.url

    # ---------- 3. Save metadata in Cosmos ----------
    cosmos_item = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "filename": filename,
        "blob_url": blob_url,
        "uploaded_on": datetime.utcnow().isoformat() + "Z"
    }

    container.create_item(cosmos_item)

    return cosmos_item






