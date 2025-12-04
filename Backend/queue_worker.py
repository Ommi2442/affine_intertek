import asyncio
import json
import os
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
from azure.cosmos import CosmosClient
from fastapi import FastAPI
from utility.embeddings import ingest_files_from_blob_urls_create_embeddings


# Azure Config
# --------------------------
# CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=stintertekesusdev;AccountKey=YtSK+RvUKmkMRJDS8895whLoVFHf35yIMlBgOtqbXBvhdvPznk9fRbijQ5PeroYtn9AECeNL2uEw+AStV9/VUA==;EndpointSuffix=core.windows.net"
print('CONNECTION_STRING', CONNECTION_STRING)
# QUEUE_CONN_STR = os.getenv("AZURE_QUEUE_CONNECTION_STRING")
QUEUE_CONN_STR = "DefaultEndpointsProtocol=https;AccountName=stintertekesusdev;AccountKey=YtSK+RvUKmkMRJDS8895whLoVFHf35yIMlBgOtqbXBvhdvPznk9fRbijQ5PeroYtn9AECeNL2uEw+AStV9/VUA==;EndpointSuffix=core.windows.net"
# BLOB_CONTAINER = os.getenv("AZURE_CONTAINER_NAME")
BLOB_CONTAINER = "testing-blob"
# QUEUE_NAME = os.getenv("AZURE_QUEUE_NAME")
QUEUE_NAME = "stintertekesusdev-queue"

COSMOS_DB_URI="https://csdb-intertek-esus-dev.documents.azure.com:443/"
COSMOS_DB_KEY="azcUeVxFxoYoFkChvWI8Wr8lMijOuWXDYQsvMf6O2LmT0Uv3Zs7lDPiXSxWYOjq00MFDbK88ApotACDbODLFXA=="
COSMOS_DB_DATABASE="intertek_poc_dev"
COSMOS_PROJECT_CONTAINER="projects"

# ---- Azure Clients ----
blob_service = BlobServiceClient.from_connection_string(QUEUE_CONN_STR)
queue_client = QueueClient.from_connection_string(QUEUE_CONN_STR, "stintertekesusdev-queue")

cosmos_client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
db = cosmos_client.get_database_client(COSMOS_DB_DATABASE)
projects_container = db.get_container_client(COSMOS_PROJECT_CONTAINER)

app = FastAPI(title="Queue Worker Service")


async def process_message(message):
    event = json.loads(message.content)
    project_id = event["projectId"]

    print(f"\n🚀 Embedding Trigger Received for Project: {project_id}\n")

    # ---- fetch project ----
    query = f"SELECT * FROM c WHERE c.Project_Id = '{project_id}'"
    docs = list(projects_container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    if not docs:
        print(f"❌ Project not found: {project_id}")
        return False

    project_doc = docs[0]

    # ---- get all blob URLs ----
    blob_urls = [x["url"] for x in project_doc.get("Source_Doc", [])]

    if not blob_urls:
        print(f"⚠ No Source_Doc files found for project {project_id}")
        return False

    print("📄 Files to embed:", len(blob_urls))

    # ---- embed only once ----
    ingest_files_from_blob_urls_create_embeddings(project_id, blob_urls)

    print(f"✔ Embedding completed for project {project_id}")
    return True


async def queue_listener():
    print("Queue Worker Started - Listening...")

    while True:
        messages = queue_client.receive_messages(
            messages_per_page=1,
            visibility_timeout=30
        )

        for message in messages:
            try:
                ok = await process_message(message)
                if ok:
                    queue_client.delete_message(message)
            except Exception as e:
                print("❌ Worker error:", e)

        await asyncio.sleep(2)


@app.on_event("startup")
async def start_worker():
    asyncio.create_task(queue_listener())
