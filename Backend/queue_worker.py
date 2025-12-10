import asyncio
import json
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
from azure.cosmos import CosmosClient
from fastapi import FastAPI
from utility.embeddings import ingest_files_from_blob_urls_create_embeddings
from utility.json_to_blob import *

# Azure Config
# --------------------------
# CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=stintertekesusdev;AccountKey=YtSK+RvUKmkMRJDS8895whLoVFHf35yIMlBgOtqbXBvhdvPznk9fRbijQ5PeroYtn9AECeNL2uEw+AStV9/VUA==;EndpointSuffix=core.windows.net"
print('CONNECTION_STRING', CONNECTION_STRING)
# QUEUE_CONN_STR = os.getenv("AZURE_QUEUE_CONNECTION_STRING")
QUEUE_CONN_STR = "DefaultEndpointsProtocol=https;AccountName=stintertekesusdev;AccountKey=YtSK+RvUKmkMRJDS8895whLoVFHf35yIMlBgOtqbXBvhdvPznk9fRbijQ5PeroYtn9AECeNL2uEw+AStV9/VUA==;EndpointSuffix=core.windows.net"
# BLOB_CONTAINER = os.getenv("AZURE_CONTAINER_NAME")
BLOB_CONTAINER = "stintertekesusdev-blob"
# QUEUE_NAME = os.getenv("AZURE_QUEUE_NAME")
QUEUE_NAME = "stintertekesusdev-queue"

COSMOS_DB_URI="https://csdb-intertek-esus-dev.documents.azure.com:443/"
COSMOS_DB_KEY="azcUeVxFxoYoFkChvWI8Wr8lMijOuWXDYQsvMf6O2LmT0Uv3Zs7lDPiXSxWYOjq00MFDbK88ApotACDbODLFXA=="
COSMOS_DB_DATABASE="intertek_poc_dev"
COSMOS_PROJECT_CONTAINER="projects"

BASE_DIR = Path(__file__).resolve().parent
TRF_JSON_OUTPUT_PATH = BASE_DIR / "data" / "pta_final_5_UI_upd.json" 

# ---- Azure Clients ----
blob_service = BlobServiceClient.from_connection_string(QUEUE_CONN_STR)
queue_client = QueueClient.from_connection_string(QUEUE_CONN_STR, QUEUE_NAME)

cosmos_client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
db = cosmos_client.get_database_client(COSMOS_DB_DATABASE)
projects_container = db.get_container_client(COSMOS_PROJECT_CONTAINER)

app = FastAPI(title="Queue Worker Service")


# ==========================================================
# HELPER: UPDATE PROJECT PROGRESS
# ==========================================================
def update_project_progress(
    project_doc: dict,
    stage: str,
    percentage: int,
    step: str | None = None,
    error: str | None = None,
):
    project_doc["Project_Progress"] = {
        "stage": stage,
        "percentage": percentage,
        "step": step,
        "last_updated": datetime.utcnow().isoformat(),
        "error": error,
    }

    projects_container.upsert_item(project_doc)
    print(f"✅ Progress updated → {percentage}% | {stage}")


# ==========================================================
# PROCESS QUEUE MESSAGE (SAFE + IDEMPOTENT)
# ==========================================================
async def process_message(message) -> bool:
    print("\n🚀 Queue message received")

    # ------------------------------------------------------
    # SAFE MESSAGE PARSE
    # ------------------------------------------------------
    try:
        if not message.content:
            print("❌ Empty queue message")
            return True

        event = json.loads(message.content)
        if not isinstance(event, dict):
            print("❌ Queue message is not a JSON object")
            return True

    except Exception as e:
        print(f"❌ Invalid queue message format: {e}")
        return True

    project_id = event.get("projectId")
    if not project_id:
        print("❌ Missing projectId in queue message")
        return True

    print(f"📦 Processing project: {project_id}")

    # ------------------------------------------------------
    # FETCH PROJECT
    # ------------------------------------------------------
    query = f"SELECT * FROM c WHERE c.Project_Id = '{project_id}'"
    docs = list(
        projects_container.query_items(
            query=query,
            enable_cross_partition_query=True,
        )
    )

    if not docs:
        print(f"❌ Project not found: {project_id}")
        return True

    project_doc = docs[0]

    # ------------------------------------------------------
    # IDEMPOTENCY GUARD
    # ------------------------------------------------------
    # progress = project_doc.get("Project_Progress") or {}
    # if progress.get("percentage") == 100:
    #     print(f"✅ Project already completed: {project_id}")
    #     return True

    # ------------------------------------------------------
    # EXTRACT SOURCE DOCUMENT URLs (SAFE)
    # ------------------------------------------------------
    source_docs = project_doc.get("Source_Doc") or []

    blob_urls: list[str] = []
    for doc in source_docs:
        if isinstance(doc, dict) and "url" in doc:
            blob_urls.append(doc["url"])
        else:
            print(f"⚠️ Skipping invalid Source_Doc entry: {doc}")

    if not blob_urls:
        print(f"⚠️ No valid source documents for project {project_id}")
        return True

    print(f"📄 Files to embed: {len(blob_urls)}")

    try:
        # --------------------------------------------------
        # 25% — EMBEDDING START
        # --------------------------------------------------
        update_project_progress(
            project_doc,
            stage="Indexing in Progress",
            percentage=25,
            step="Creating embeddings",
        )

        ingest_files_from_blob_urls_create_embeddings(
            project_id,
            blob_urls,
        )

        # --------------------------------------------------
        # 50% — EMBEDDING COMPLETE
        # --------------------------------------------------
        update_project_progress(
            project_doc,
            stage="Embedding Completed",
            percentage=50,
            step="Embeddings ready",
        )

        # --------------------------------------------------
        # 75% — TRF GENERATION
        # --------------------------------------------------
        update_project_progress(
            project_doc,
            stage="Generating TRF",
            percentage=75,
            step="Generating TRF JSON",
        )

        # --------------------------------------------------
        # SAVE TRF JSON → BLOB + COSMOS
        # --------------------------------------------------
        save_local_json_to_blob_and_cosmos(
            file_path=str(TRF_JSON_OUTPUT_PATH),
            project_id=project_id,
        )

        # --------------------------------------------------
        # 100% — COMPLETED
        # --------------------------------------------------
        update_project_progress(
            project_doc,
            stage="Completed",
            percentage=100,
            step="TRF generated and stored",
        )

        print(f"🎉 TRF generation completed for project {project_id}")
        return True

    except Exception as e:
        print(f"❌ Worker failed for project {project_id}: {e}")

        update_project_progress(
            project_doc,
            stage="Failed",
            percentage=0,
            step="Processing failed",
            error=str(e),
        )

        return False  # ❌ retry allowed


# ==========================================================
# QUEUE LISTENER (CORRECT DELETE LOGIC)
# ==========================================================
async def queue_listener():
    print("\n📡 Worker started — listening to Azure Queue...\n")

    while True:
        try:
            messages = queue_client.receive_messages(
                messages_per_page=1,
                visibility_timeout=300,  # must exceed processing time
            )

            for message in messages:
                try:
                    ok = await process_message(message)

                    if ok:
                        queue_client.delete_message(
                            message.id,
                            message.pop_receipt
                        )
                        print(f"✅ Queue message deleted: {message.id}")

                except Exception as e:
                    print("❌ Error during message handling:", e)

        except Exception as e:
            print("❌ Queue listener failure:", e)

        await asyncio.sleep(2)


# ==========================================================
# START WORKER ON APPLICATION STARTUP
# ==========================================================
@app.on_event("startup")
async def start_worker():
    asyncio.create_task(queue_listener())
