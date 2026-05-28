import os
from pathlib import Path

from azure.cosmos import CosmosClient, ConsistencyLevel
from openai import AzureOpenAI

from projects.keyvault_load import load_keyvault_secrets

# Core helpers (DO NOT MODIFY)
from utility.letter_report.deploymentV1.core import *
from utility.letter_report.deploymentV1.trf_utils import *

from utility.letter_report.deploymentV1.config import (
    AOAI_ENDPOINT,
    AOAI_KEY,
    API_VERSION,
    AZURE_CONN_STRING,
    BLOB_CONTAINER_NAME,
    CHAT_DEPLOY,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CONT_NAME_IMG,
    COSMOS_KEY,
    COSMOS_URL,
    DB_NAME,
    DB_NAME_IMG,
    EMBED_DEPLOY,
    INITIAL_BACKOFF,
    MAX_RETRIES,
    MAX_THREADS,
)

load_keyvault_secrets()

COSMOS_DB_IMAGE  = DB_NAME_IMG
COSMOS_CONT_IMAGE = CONT_NAME_IMG

ENABLE_CAD_SCHEMATICS = os.getenv("enable-cad-schematics")

LT_DOWNLOAD_DIR = os.getenv("lt-download-dir")
COSMOS_CONT_TEXT = os.getenv("cosmos-cont-text")
COSMOS_DB_TEXT=os.getenv("cosmos-db-text")

print("FOR------LT_DOWNLOAD_DIR ----",LT_DOWNLOAD_DIR)

def main(project_id,blob_urls,text_container,image_container):
    """
    Main ingestion pipeline.
    Takes list of blob URLs and ingests:
      - Text chunks → Vector DB 1
      - Image OCR chunks → Vector DB 2
    """

    print("\n==============================")
    print("🚀 LETTER INGESTOR PIPELINE")
    print("==============================\n")

    # -------------------------------------------------------
    # STEP 1 — Cleanup existing vector container
    # -------------------------------------------------------


    cosmos_client = CosmosClient(
        COSMOS_URL,
        credential=COSMOS_KEY,
        consistency_level=ConsistencyLevel.Eventual
    )


    # -------------------------------------------------------
    # STEP 2 — Download + extract blob files
    # -------------------------------------------------------

    container_blob = BLOB_CONTAINER_NAME  # from config.py

    print("[INFO] Downloading and extracting blob files...\n")

    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

    DOWNLOAD_DIR = BASE_DIR / "data" / project_id / LT_DOWNLOAD_DIR


    extracted_texts, image_urls, downloaded_pdf_paths, converted_pdf_paths = process_blob_urls_2(
        blob_urls,
        AZURE_CONN_STRING,
        container_blob,
        download_dir=DOWNLOAD_DIR,
        keep_files=True,
        verbose=True
    )

    pdf_paths = downloaded_pdf_paths + converted_pdf_paths

    # -------------------------------------------------------
    # STEP 3 — Create Vector DB for TEXT
    # -------------------------------------------------------

    print("\n[INFO] Creating Vector DB for TEXT...")


    embeddings = build_embeddings(
        AOAI_ENDPOINT,
        AOAI_KEY,
        API_VERSION,
        EMBED_DEPLOY
    )

    vs = build_vectorstore(
        embeddings,
        COSMOS_URL,
        COSMOS_KEY,
        DB_NAME,
        text_container
    )

    # -------------------------------------------------------
    # STEP 4 — Load PDFs and create text chunks
    # -------------------------------------------------------

    print("\n[INFO] Loading PDFs and creating text chunks...")

    chunks, image_page_metadata = load_and_split_pdfs_text(
        pdf_paths,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
        extracted_texts=extracted_texts,
        cad_schematics=False
    )

    # -------------------------------------------------------
    # STEP 5 — Upload CAD / schematic images to Blob
    # -------------------------------------------------------

    print("\n[INFO] Uploading CAD/Schematic images to blob...")

    image_urls = upload_pdf_images_and_append_urls(
        image_page_metadata,
        image_urls,
        AZURE_CONN_STRING,
        container_blob
    )

    # -------------------------------------------------------
    # STEP 6 — Ingest TEXT chunks to Vector DB
    # -------------------------------------------------------

    print("\n[INFO] Ingesting TEXT chunks into Vector DB...")

    ingest_to_cosmos_parallel(
        vs,
        chunks,
        batch_size=10,
        max_workers=10
    )

    print("[SUCCESS] Text ingestion completed.\n")

    # -------------------------------------------------------
    # STEP 7 — Create Vector DB for IMAGE OCR
    # -------------------------------------------------------

    print("[INFO] Creating Vector DB for IMAGE OCR...")

    cosmos_client = CosmosClient(
        COSMOS_URL,
        credential=COSMOS_KEY,
        consistency_level=ConsistencyLevel.Eventual
    )


    embeddings = build_embeddings(
        AOAI_ENDPOINT,
        AOAI_KEY,
        API_VERSION,
        EMBED_DEPLOY
    )

    vs2 = build_vectorstore2(
        embeddings,
        COSMOS_URL,
        COSMOS_KEY,
        DB_NAME_IMG,
        image_container
    )

    # -------------------------------------------------------
    # STEP 8 — Extract image URLs
    # -------------------------------------------------------

    print("\n[INFO] Extracting image URLs...")

    img_links = extract_urls(image_urls)

    # -------------------------------------------------------
    # STEP 9 — OCR images using Azure Vision GPT
    # -------------------------------------------------------

    print("\n[INFO] Running Vision OCR on images...")

    aoai_client = AzureOpenAI(
        api_key=AOAI_KEY,
        api_version=API_VERSION,
        azure_endpoint=AOAI_ENDPOINT,
    )

    t = load_and_process_images(
        img_links,
        MAX_THREADS,
        MAX_RETRIES,
        INITIAL_BACKOFF,
        aoai_client,
        CHAT_DEPLOY
    )

    # -------------------------------------------------------
    # STEP 10 — Ingest IMAGE OCR chunks
    # -------------------------------------------------------

    print("\n[INFO] Ingesting IMAGE OCR chunks into Vector DB...")

    ingest_to_cosmos_parallel(
        vs2,
        t,
        batch_size=10,
        max_workers=10
    )

    print("\n==============================")
    print("✅ INGESTION PIPELINE COMPLETED")
    print("==============================\n")
    return True

