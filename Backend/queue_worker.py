import asyncio
import json
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
from azure.cosmos import CosmosClient, ConsistencyLevel
from fastapi import FastAPI
from utility.embeddings import ingest_files_from_blob_urls_create_embeddings
from utility.json_to_blob import *
from utility.trf_report.trf_generation import run_trf_generation
from utility.trf_utils import build_vectorstore, build_embeddings


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


# ---- Azure Clients ----
blob_service = BlobServiceClient.from_connection_string(QUEUE_CONN_STR)
queue_client = QueueClient.from_connection_string(QUEUE_CONN_STR, QUEUE_NAME)

cosmos_client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
db = cosmos_client.get_database_client(COSMOS_DB_DATABASE)
projects_container = db.get_container_client(COSMOS_PROJECT_CONTAINER)


############################ TRF OPENAI CREDENTIALS ###################################


# Load environment variables
AOAI_ENDPOINT      = os.getenv("AOAI_ENDPOINT")
AOAI_KEY           = os.getenv("AOAI_KEY")
API_VERSION        = os.getenv("API_VERSION")
EMBED_DEPLOY       = os.getenv("EMBED_DEPLOY")
RAG_DB_NAME        = os.getenv("DB_NAME")
RAG_CONT_NAME      = os.getenv("CONT_NAME")
RAG_AZURE_CONN_STRING  = os.getenv("AZURE_CONN_STRING")
RAG_COSMOS_URL         = os.getenv("COSMOS_URL")
RAG_COSMOS_KEY         = os.getenv("COSMOS_KEY")



BASE_DIR = Path(__file__).resolve().parent

INPUT_JSON_PATH = BASE_DIR / "data" / "pta_final_5.json"
INPUT_DOCX_PATH = BASE_DIR / "data" / "input.docx"

OUTPUT_JSON = BASE_DIR / "data" / "iec_output.json"
OUTPUT_DOCX = BASE_DIR / "data" / "iec_output.docx"
OUTPUT_EXCEL = BASE_DIR / "data" / "iec_output.xlsx"

IMAGE_URLS_PATH = BASE_DIR / "data" / "image_urls.json"  # adjust if needed




app = FastAPI(title="Queue Worker Service")


# ==========================================================
# HELPER: UPDATE PROJECT PROGRESS
# ==========================================================
def update_project_progress(
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

    projects_container.upsert_item(project_doc)
    print(f"✅ Progress updated → {trf_percentage}% | {trf_stage}")


# ==========================================================
# PROCESS QUEUE MESSAGE (SAFE + IDEMPOTENT)
# ==========================================================
async def process_message(message) -> bool:
    print("\n🚀 Queue message received")

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
        # Start at 0%
        update_project_progress(
            project_doc,
            trf_stage="Indexing in Progress",
            trf_percentage=0,
            trf_step="Starting embedding",
            trf_completed=False
        )

        ingest_files_from_blob_urls_create_embeddings(blob_urls, project_id)

        print(f"🎉 Embeddings completed for project {project_id}")

        # Embedding Complete → 20%
        update_project_progress(
            project_doc,
            trf_stage="Embedding Completed",
            trf_percentage=20,
            trf_step="Embeddings completed",
            trf_completed=False
        )

        with open(IMAGE_URLS_PATH, "r") as f:
            image_urls = json.load(f)
        print(f"✔ Loaded {len(image_urls)} image URLs from ingestion.")

        print("🔧 Initializing Cosmos + Vectorstore...")

        trf_cosmos_client = CosmosClient(
            RAG_COSMOS_URL,
            credential=RAG_COSMOS_KEY,
            consistency_level=ConsistencyLevel.Eventual
        )

        embeddings = build_embeddings(AOAI_ENDPOINT, AOAI_KEY, API_VERSION, EMBED_DEPLOY)

        vs = build_vectorstore(
            embeddings=embeddings,
            client=trf_cosmos_client,
            DB_NAME=RAG_DB_NAME,
            CONT_NAME=RAG_CONT_NAME
        )

        print("✔ Vectorstore loaded from Cosmos DB.")

        # --- TRF PROGRESS CALLBACK (20% → 95%) ---
        def trf_progress_callback(processed, total):
            raw_percent = (processed / total) * 100
            ui_percent = int(20 + (raw_percent * 0.75))  # 0–100 → 20–95
            if ui_percent > 95:
                ui_percent = 95

            update_project_progress(
                project_doc,
                trf_stage="Generating TRF",
                trf_percentage=ui_percent,
                trf_step=f"Processed {processed}/{total}",
                trf_completed=False
            )

        result = run_trf_generation(
            vs=vs,
            image_urls=image_urls,
            input_json_path=INPUT_JSON_PATH,
            docx_input_path=INPUT_DOCX_PATH,
            output_json_path=OUTPUT_JSON,
            output_docx_path=OUTPUT_DOCX,
            output_excel_path=OUTPUT_EXCEL,
            batch_size=150,
            cooldown_sec=15,
            max_workers=10,
            use_llm_inGrey=False,
            stats=True,
            progress_callback=trf_progress_callback
        )

        print(f"🎉 TRF generation completed for project {project_id}")

        # 95% before saving
        update_project_progress(
            project_doc,
            trf_stage="Saving TRF Report",
            trf_percentage=95,
            trf_step="Saving TRF output files",
            trf_completed=False
        )

        save_local_json_to_blob_and_cosmos(
            file_path=str(OUTPUT_JSON),
            project_id=project_id,
        )

        # 100% completed
        update_project_progress(
            project_doc,
            trf_stage="Completed",
            trf_percentage=100,
            trf_step="TRF generated and stored",
            trf_completed=True
        )

        print(f"🎉 Saving TRF Report to the Blob")
        return True

    except Exception as e:
        print(f"❌ Worker failed for project {project_id}: {e}")

        update_project_progress(
            project_doc,
            trf_stage="Failed",
            trf_percentage=0,
            trf_step="Processing failed",
            error=str(e),
            trf_completed=False
        )

        return False




# ==========================================================
# QUEUE LISTENER (CORRECT DELETE LOGIC)
# ==========================================================
async def queue_listener():
    print("\n📡 Worker started — actively listening to Azure Queue...\n")

    while True:
        try:
            # Pull exactly 1 message for strict sequential processing
            messages = queue_client.receive_messages(
                messages_per_page=1,
                visibility_timeout=300,  # keep long since TRF pipeline is heavy
            )

            message_found = False

            for message in messages:
                message_found = True

                try:
                    ok = await process_message(message)

                    if ok:
                        queue_client.delete_message(
                            message.id,
                            message.pop_receipt
                        )
                        print(f"✅ Queue message deleted: {message.id}")

                except Exception as e:
                    print(f"❌ Error during message handling: {e}")

            # -----------------------------------------------------
            # ACTIVE LISTENING LOGIC
            # -----------------------------------------------------
            if not message_found:
                # No message → short backoff sleep to avoid CPU burn
                await asyncio.sleep(1)
            else:
                # Messages present → check again immediately
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"❌ Queue listener failure: {e}")
            # Do not kill worker; recover after short backoff
            await asyncio.sleep(2)



# ==========================================================
# START WORKER ON APPLICATION STARTUP
# ==========================================================
@app.on_event("startup")
async def start_worker():
    asyncio.create_task(queue_listener())
