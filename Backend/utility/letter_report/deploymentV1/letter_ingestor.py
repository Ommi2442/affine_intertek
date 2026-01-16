import sys
from azure.cosmos import CosmosClient, ConsistencyLevel
from openai import AzureOpenAI

# Core helpers (DO NOT MODIFY)

from utility.letter_report.deploymentV1.core import *



from dotenv import load_dotenv

load_dotenv()
import os

AZURE_CONN_STRING = os.getenv("AZURE_CONN_STRING")
DB_NAME_IMG = os.getenv("DB_NAME_IMG")
CONT_NAME_IMG = os.getenv("COSMOS_CONT_IMAGE")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP"))
TOP_K = int(os.getenv("TOP_K"))
EMBED_DIM = int(os.getenv("EMBED_DIM"))
VECTOR_PATH = os.getenv("VECTOR_PATH")
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME")
CONN_STR = os.getenv("conn_str")
IMAGE_EXTS = os.getenv("IMAGE_EXTS")
AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")
AOAI_KEY = os.getenv("AOAI_KEY")
API_VERSION = os.getenv("API_VERSION")
EMBED_DEPLOY = os.getenv("EMBED_DEPLOY")
CHAT_DEPLOY = os.getenv("CHAT_DEPLOY")
COSMOS_URL = os.getenv("COSMOS_URL")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB = os.getenv("COSMOS_DB")
COSMOS_CONT = os.getenv("COSMOS_CONT")
DB_NAME = os.getenv("DB_NAME")
CONT_NAME = os.getenv("CONT_NAME")
MAX_THREADS = int(os.getenv("MAX_THREADS"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES"))
INITIAL_BACKOFF = int(os.getenv("INITIAL_BACKOFF"))
  




def main(blob_urls):
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

    print("[INFO] Cleaning existing Cosmos container...")

    cosmos_client = CosmosClient(
        COSMOS_URL,
        credential=COSMOS_KEY,
        consistency_level=ConsistencyLevel.Eventual
    )

    # container = cosmos_client.get_database_client(DB_NAME).get_container_client(CONT_NAME)

    # items = container.read_all_items()
    # for item in items:
    #     container.delete_item(item=item, partition_key=item["id"])

    print("[SUCCESS] All existing documents deleted.\n")

    # -------------------------------------------------------
    # STEP 2 — Download + extract blob files
    # -------------------------------------------------------

    container_blob = BLOB_CONTAINER_NAME  

    print("[INFO] Downloading and extracting blob files...\n")

    extracted_texts, image_urls, downloaded_pdf_paths, converted_pdf_paths = process_blob_urls_2(
        blob_urls,
        AZURE_CONN_STRING,
        container_blob,
        download_dir="src_files",
        keep_files=True,
        verbose=True
    )

    pdf_paths = downloaded_pdf_paths + converted_pdf_paths

    # -------------------------------------------------------
    # STEP 3 — Create Vector DB for TEXT
    # -------------------------------------------------------

    print("\n[INFO] Creating Vector DB for TEXT...")

    # container = create_db_and_container(
    #     cosmos_client,
    #     DB_NAME,
    #     VECTOR_PATH,
    #     EMBED_DIM,
    #     CONT_NAME
    # )

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
        CONT_NAME
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

    # container_IMG = create_db_and_container(
    #     cosmos_client,
    #     DB_NAME_IMG,
    #     VECTOR_PATH,
    #     EMBED_DIM,
    #     CONT_NAME_IMG
    # )

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
        CONT_NAME_IMG
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

