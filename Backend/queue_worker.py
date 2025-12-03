import time
import json
import os
import asyncio
from fastapi import FastAPI
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
# from utility.embeddings import ingest_files_from_blob_urls_create_embeddings

# --------------------------
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


blob_service = BlobServiceClient.from_connection_string(CONNECTION_STRING)
queue_client = QueueClient.from_connection_string(QUEUE_CONN_STR, QUEUE_NAME)


app = FastAPI(title="Queue Worker Service")

# --------------------------
# PROCESS MESSAGE
# --------------------------
async def process_message(msg):
    event = json.loads(msg.content)

    print("\n====== QUEUE MESSAGE RECEIVED ======")
    print("Key:", event["key"])
    print("Filename:", event["filename"])
    print("Blob Path:", event["blob_path"])
    print("Blob URL:", event["blob_url"])
    print("====================================\n")

    # Download blob
    blob_client = blob_service.get_blob_client(
        container=BLOB_CONTAINER,
        blob=event["blob_path"]  # instead of blob_name
    )


    file_bytes = blob_client.download_blob().readall()
    print(f"Downloaded Blob ({len(file_bytes)} bytes)")

    # ---- Your embedding logic goes here ----
    print("Embedding Logic Completed.")

#     blob_urls = [
#     "https://stintertekesusdev.blob.core.windows.net/testing-blob/22726_Block-Diagram_Rev3.pdf",
#     "https://stintertekesusdev.blob.core.windows.net/testing-blob/999-051754_Critical_Components_List.xlsx",
#     "https://stintertekesusdev.blob.core.windows.net/testing-blob/Product1_Product_Requirements_Document.docx",
#     "https://stintertekesusdev.blob.core.windows.net/testing-blob/Product1_User_Guide_RevA.docx",
#    "https://stintertekesusdev.blob.core.windows.net/testing-blob/marking_label.JPG"
#     ]

#     ingest_files_from_blob_urls_create_embeddings(blob_urls)

    return True


# --------------------------
# QUEUE LISTENER (runs forever)
# --------------------------
async def queue_listener():

    print("Queue Worker Started... Listening for messages...\n")

    while True:
        messages = queue_client.receive_messages(
            messages_per_page=1,
            visibility_timeout=30
        )

        for msg in messages:
            try:
                ok = await process_message(msg)
                if ok:
                    queue_client.delete_message(msg)
                    print("✔ Message processed & deleted")
            except Exception as e:
                print("❌ Error processing message:", e)

        await asyncio.sleep(2)  # Non-blocking sleep


# --------------------------
# HEARTBEAT LOGGER (every 15 seconds)
# --------------------------
async def heartbeat_printer():
    while True:
        print("[Heartbeat] Queue Worker Listening...")
        await asyncio.sleep(15)


# --------------------------
# FASTAPI STARTUP EVENT
# --------------------------
@app.on_event("startup")
async def start_background_worker():
    asyncio.create_task(queue_listener())      # queue processor
    asyncio.create_task(heartbeat_printer())   # heartbeat printer


