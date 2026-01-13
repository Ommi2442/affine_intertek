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
from utility.cdr_report.CDR_Pipelines.main import main2
from utility.cdr_report.CDR_Pipelines.compiler import fill_excel_from_json
from pathlib import Path

# Azure Config
# --------------------------
# CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
# CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=stintertekesusdev;AccountKey=YtSK+RvUKmkMRJDS8895whLoVFHf35yIMlBgOtqbXBvhdvPznk9fRbijQ5PeroYtn9AECeNL2uEw+AStV9/VUA==;EndpointSuffix=core.windows.net"
# print('CONNECTION_STRING', CONNECTION_STRING)
# QUEUE_CONN_STR = os.getenv("AZURE_QUEUE_CONNECTION_STRING")
QUEUE_CONN_STR = "DefaultEndpointsProtocol=https;AccountName=stintertekesusstage;AccountKey=X3xxXc+G6VT3GNShGEIO+boKEbI2jLbh0U9wg5/U2UME328bFHPVdeJDgp9fyKfs7IW/MoJnpi5Q+ASti9+IlA==;EndpointSuffix=core.windows.net"
# BLOB_CONTAINER = os.getenv("AZURE_CONTAINER_NAME")
BLOB_CONTAINER = "stintertekesusstage-blob"
# QUEUE_NAME = os.getenv("AZURE_QUEUE_NAME")
QUEUE_NAME = "stintertekesus-stage-queue"
CDR_QUEUE_NAME = "stintertekesus-stage-queue-cdr"

COSMOS_DB_URI="https://csdb-intertek-esus-stage.documents.azure.com:443/"
COSMOS_DB_KEY="HpRV1o6cIgx2jae8eh2XF6hSLUobpnUOg5F2ElDq4SeP1p4OPxf9QEWQko5lVFyQQtvCAOuejS55ACDbKGjKow=="
COSMOS_DB_DATABASE="intertek_poc_stage"
COSMOS_PROJECT_CONTAINER="projects"


# ---- Azure Clients ----
blob_service = BlobServiceClient.from_connection_string(QUEUE_CONN_STR)
queue_client = QueueClient.from_connection_string(QUEUE_CONN_STR, QUEUE_NAME)
queue_client_cdr = QueueClient.from_connection_string(QUEUE_CONN_STR, CDR_QUEUE_NAME)

cosmos_client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
db = cosmos_client.get_database_client(COSMOS_DB_DATABASE)
projects_container = db.get_container_client(COSMOS_PROJECT_CONTAINER)


############################ TRF OPENAI CREDENTIALS ###################################

# Load environment variables
AOAI_ENDPOINT      = os.getenv("AOAI_ENDPOINT")
AOAI_KEY           = os.getenv("AOAI_KEY")
API_VERSION        = os.getenv("API_VERSION")
EMBED_DEPLOY       = os.getenv("EMBED_DEPLOY")
RAG_AZURE_CONN_STRING  = os.getenv("AZURE_CONN_STRING")
RAG_COSMOS_URL         = os.getenv("COSMOS_URL")
RAG_COSMOS_KEY         = os.getenv("COSMOS_KEY")






########################################################################33


# resp=load_trf_json_from_blob(project_id)
# resp=load_trf_json_from_blob("G105581614")
# trf_json_ouput=resp.get("data")

# input_cdr_json=trf_json_ouput
# queue_client_cdr.send_message(json.dumps({
#     "projectId": "G105581614",
#     "action": "cdr_generation",
#     "timestamp": datetime.utcnow().isoformat()
# }))

#cdr return to fE
# updated_json=cdr_main
# data=fill_excel_from_json(updated_json)
# print("Completed--------")


##################################################################

BASE_DIR = Path(__file__).resolve().parent

BASE_PTA_JSON_PATH = BASE_DIR / "data" / "input_files" / "pta_final_6_3_1.json"
INPUT_JSON_FILENAMES = ["pta_final_6_3_1_part1.json","pta_final_6_3_1_part2.json","pta_final_6_3_1_part3.json","pta_final_6_3_1_part4.json", "pta_final_6_3_1_part5.json"]
INPUT_DOCX_PATH = BASE_DIR / "data" / "input_files" / "input.docx"

DOWNLOAD_DIR = BASE_DIR  / "src_files"

DATA_DIR = BASE_DIR / "data" 

IMAGE_URLS_PATH = BASE_DIR / "utility" / "image_urls.json"  # adjust if needed


app = FastAPI(title="Queue Worker Service")

# ==========================================================
# HELPER: UPDATE PROJECT PROGRESS
# ==========================================================
def update_project_progress(
    project_doc: dict,
    trf_stage: str,
    trf_percentage: int = 10,
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
    print(f" Progress updated → {trf_percentage}% | {trf_stage}")


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





# ==========================================================
# PROCESS TRF QUEUE MESSAGE (SAFE + IDEMPOTENT)
# ==========================================================

async def process_message(message) -> bool:
    print("\n Queue message received")

    try:
        if not message.content:
            print(" Empty queue message")
            return True

        event = json.loads(message.content)
        if not isinstance(event, dict):
            print(" Queue message is not a JSON object")
            return True

    except Exception as e:
        print(f" Invalid queue message format: {e}")
        return True

    project_id = event.get("projectId")
    if not project_id:
        print(" Missing projectId in queue message")
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
        print(f" Project not found: {project_id}")
        return True

    project_doc = docs[0]

    source_docs = project_doc.get("Source_Doc") or []

    blob_urls: list[str] = []
    for doc in source_docs:
        if isinstance(doc, dict) and "url" in doc:
            blob_urls.append(doc["url"])
        else:
            print(f" Skipping invalid Source_Doc entry: {doc}")

    if not blob_urls:
        print(f" No valid source documents for project {project_id}")
        return True
    
    print(f"blob_urls source_docs------{blob_urls}")
    print(f" Files to embed: {len(blob_urls)}")

    # ---------------------------------------------------------
    # DEFINE CALLBACK (MUST BE BEFORE TRF CALL)
    # ---------------------------------------------------------
    def on_first_json_ready():
        print("🚀 EVENT: First TRF JSON has been generated")

        update_project_progress(
            project_doc,
            trf_stage="First TRF JSON Generated",
            trf_percentage=30,          # ⚠️ NOT 100%
            trf_step="Initial TRF JSON ready",
            trf_completed=False
        )


    try:
        # Start at 10%
        update_project_progress(
            project_doc,
            trf_stage="Indexing in Progress",
            trf_percentage=10,
            trf_step="Starting embedding",
            trf_completed=False
        )
                
        ingest_files_from_blob_urls_create_embeddings(DOWNLOAD_DIR, blob_urls, project_id)

        print(f" Embeddings completed for project {project_id}")

        # Embedding Complete → 20%
        # update_project_progress(
        #     project_doc,
        #     trf_stage="Embedding Completed",
        #     trf_percentage=20,
        #     trf_step="Embeddings completed",
        #     trf_completed=False
        # )


        # --- TRF PROGRESS CALLBACK (20% → 95%) ---
        # def trf_progress_callback(processed, total):
        #     raw_percent = (processed / total) * 100
        #     ui_percent = int(20 + (raw_percent * 0.75))  # 0–100 → 20–95
        #     if ui_percent > 95:
        #         ui_percent = 95

        #     update_project_progress(
        #         project_doc,
        #         trf_stage="Generating TRF",
        #         trf_percentage=ui_percent,
        #         trf_step=f"Processed {processed}/{total}",
        #         trf_completed=False
        #     )

        project_data_dir = BASE_DIR / "data" / project_id

        OUTPUT_JSON_PATH = DATA_DIR / project_id / "final_output.json"
        OUTPUT_DOCX_PATH = DATA_DIR / project_id / "final_output.docx"

        INPUT_FILES = DATA_DIR / "input_files"

        INPUT_JSON_PATHS = [
            INPUT_FILES / filename
            for filename in INPUT_JSON_FILENAMES
        ]

        run_trf_generation(
            blob_urls,
            input_docx_path=INPUT_DOCX_PATH,
            output_docx_path=OUTPUT_DOCX_PATH,
            base_pta_path=BASE_PTA_JSON_PATH,
            input_json_paths=INPUT_JSON_PATHS,
            project_data_dir=project_data_dir,
            batch_size=150,
            final_output_path=OUTPUT_JSON_PATH,
            cooldown_sec=15,
            max_workers=10,
            on_first_json_generated=on_first_json_ready,
        )


        # 95% before saving
        # update_project_progress(
        #     project_doc,
        #     trf_stage="Saving TRF Report",
        #     trf_percentage=95,
        #     trf_step="Saving TRF output files",
        #     trf_completed=False
        # )

        print(f" TRF generation completed for project {project_id}")
        
        save_local_json_to_blob_and_cosmos(str(OUTPUT_JSON_PATH),str(OUTPUT_DOCX_PATH),project_id=project_id,update_only=False)

        # 100% completed
        update_project_progress(
            project_doc,
            trf_stage="Completed",
            trf_percentage=100,
            trf_step="TRF generated and stored",
            trf_completed=True
        )

        print(f" Saving TRF Report to the Blob")
        return True

    except Exception as e:
        print(f" Worker failed for project {project_id}: {e}")

        update_project_progress(
            project_doc,
            trf_stage="Failed",
            trf_percentage=0,
            trf_step="Processing failed",
            error=str(e),
            trf_completed=False
        )

        return False




# # # ==========================================================
# # # QUEUE LISTENER (15-SECOND POLLING, SAFE & STABLE)
# # # ==========================================================
async def queue_listener():
    print("\n Worker started — polling Azure Queue every 15 seconds...\n")

    POLL_INTERVAL_SEC = 15

    while True:
        try:
            messages = queue_client.receive_messages(
                messages_per_page=1,
                visibility_timeout=600,  # must be > max TRF processing time
            )

            message_found = False

            for message in messages:
                message_found = True
                print(f" Queue message fetched: {message.id}")

                try:
                    ok = await process_message(message)

                    if ok:
                        queue_client.delete_message(
                            message.id,
                            message.pop_receipt
                        )
                        print(f" Queue message deleted: {message.id}")

                except Exception as e:
                    print(f" Error while processing message {message.id}: {e}")

            if not message_found:
                print(" No queue messages found")

            # ✅ ALWAYS wait 15 seconds before next poll
            await asyncio.sleep(POLL_INTERVAL_SEC)

        except Exception as e:
            print(f" Queue listener failure: {e}")
            # short recovery backoff
            await asyncio.sleep(5)

# # -----------------------------------------------------------------------------------------
# # CDR QUEUE PROCESSING Code

async def process_message_cdr(message) -> bool:
    print("\n Queue message received for CDR")

    try:
        if not message.content:
            print(" Empty queue message")
            return True

        event = json.loads(message.content)
        if not isinstance(event, dict):
            print(" Queue message is not a JSON object")
            return True

    except Exception as e:
        print(f" Invalid queue message format: {e}")
        return True

    project_id = event.get("projectId")
    if not project_id:
        print(" Missing projectId in queue message for CDR")
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
        print(f" Project not found: {project_id}")
        return True

    project_doc = docs[0]

    source_docs = project_doc.get("Source_Doc") or []

    blob_urls: list[str] = []
    for doc in source_docs:
        if isinstance(doc, dict) and "url" in doc:
            blob_urls.append(doc["url"])
        else:
            print(f" Skipping invalid Source_Doc entry: {doc}")

    if not blob_urls:
        print(f" No valid source documents for project {project_id}")
        return True
    
    print(f"blob_urls source_docs------{blob_urls}")
    print(f" Files to embed: {len(blob_urls)}")

    try:
        # Start at 0%
        update_project_progress_CDR(
            project_doc,
            cdr_stage="steps in Progress",
            cdr_percentage=0,
            cdr_step="Starting runnig CDR",
            cdr_completed=False
        )
                

        print(f" Embeddings completed for project cdr {project_id}")


        def cdr_progress_callback(processed, total):
            raw_percent = (processed / total) * 100
            ui_percent = int(20 + (raw_percent * 0.75))  # 0–100 → 20–95
            if ui_percent > 95:
                ui_percent = 95

            update_project_progress_CDR(
                project_doc,
                cdr_stage="Generating CDR",
                cdr_percentage=ui_percent,
                cdr_step=f"Processed {processed}/{total}",
                cdr_completed=False
            )
        
        # resp=load_trf_json_from_blob("G105581614")
        # trf_json_ouput=resp.get("data")
        # input_cdr_json=trf_json_ouput
        # queue_client_cdr.send_message(json.dumps({
        #     "projectId": "G105581614",
        #     "action": "cdr_generation",
        #     "timestamp": datetime.utcnow().isoformat()
        # }))

        print("loading trf json from blob for cdr generation_____________________@@@@@@@@@@@@@@")
        # cdr_main=main2(input_cdr_json,progress_callback=cdr_progress_callback)
        resp=load_trf_json_from_blob(project_id)

        # fetch trf json from blob
        print("++++++++++++++++++++++ Fetching TRF JSON from Blob +++++++++++++++++++++++")
        input_cdr_json=resp.get("json_data")
        cdr_main=main2(input_cdr_json)
        #cdr return to fE
        updated_json=cdr_main
        data=fill_excel_from_json(updated_json)
        
        # print(f" CDR generation completed for project {project_id} \n\n",cdr_main)
        

        print(f" TRF generation completed for project {project_id}")
        # main2(cdr=cdr_payload')


        
        # save_local_json_to_blob_and_cosmos(str(OUTPUT_JSON),str(OUTPUT_DOCX),project_id=project_id,)

        update_project_progress_CDR(
                project_doc,
                cdr_stage="Completed",
                cdr_percentage=100,
                cdr_step=f"CDR generated and stored",
                cdr_completed=True
            )
        

        print(f" Saving TRF Report to the Blob")
        #generating the CDR Report code starts here
        # read the CDR payload from the generated TRF JSON from the blob storage
        
        return True

    except Exception as e:
        print(f" Worker failed for project {project_id}: {e}")

        update_project_progress_CDR(
            project_doc,
            cdr_stage="Failed",
            cdr_percentage=0,
            cdr_step="Processing failed",
            error="error",
            cdr_completed=False
        )

        return False




# # # ==========================================================
# # # QUEUE LISTENER (15-SECOND POLLING, SAFE & STABLE)
# # # ==========================================================
async def queue_listener_cdr():
    print("\n Worker started — polling Azure Queue every 15 seconds...\n")
    POLL_INTERVAL_SEC = 15

    while True:
        try:
            messages = queue_client_cdr.receive_messages(
                messages_per_page=1,
                visibility_timeout=600,  # must be > max TRF processing time
            )

            message_found = False

            for message in messages:
                message_found = True
                print(f" Queue message fetched: {message.id}")

                try:
                    ok = await process_message_cdr(message)

                    if ok:
                        queue_client_cdr.delete_message(
                            message.id,
                            message.pop_receipt
                        )
                        print(f" Queue message deleted for CDR : {message.id}")

                except Exception as e:
                    print(f" Error while processing  CDR message {message.id}: {e}")

            if not message_found:
                print(" No queue messages found for CDR")

            # ✅ ALWAYS wait 15 seconds before next poll
            await asyncio.sleep(POLL_INTERVAL_SEC)

        except Exception as e:
            print(f" Queue listener failure: {e}")
            # short recovery backoff
            await asyncio.sleep(5)



# ==========================================================
# START WORKER ON APPLICATION STARTUP
# ==========================================================
@app.on_event("startup")
async def start_worker():
    asyncio.create_task(queue_listener())
    # asyncio.create_task(queue_listener_cdr())
