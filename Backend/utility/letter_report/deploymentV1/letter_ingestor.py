import sys
from azure.cosmos import CosmosClient, ConsistencyLevel
from openai import AzureOpenAI

# Core helpers (DO NOT MODIFY)
from utility.letter_report.deploymentV1.core import *

from utility.letter_report.deploymentV1.config import AZURE_CONN_STRING, DB_NAME_IMG, CONT_NAME_IMG, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K, EMBED_DIM, VECTOR_PATH, BLOB_CONTAINER_NAME, conn_str, IMAGE_EXTS, AOAI_ENDPOINT, AOAI_KEY, API_VERSION, EMBED_DEPLOY, CHAT_DEPLOY, COSMOS_URL, COSMOS_KEY, COSMOS_DB, COSMOS_CONT, DB_NAME, CONT_NAME, MAX_THREADS, MAX_RETRIES, INITIAL_BACKOFF


COSMOS_DB_IMAGE  = DB_NAME_IMG
COSMOS_CONT_IMAGE = CONT_NAME_IMG
BLOB_CONT_NAME= os.getenv("BLOB_CONT_NAME")
ENABLE_CAD_SCHEMATICS = os.getenv("ENABLE_CAD_SCHEMATICS")
# FLATTENED_DIR = os.getenv("FLATTENED_DIR")
# IMAGES_ROOT =os.getenv("IMAGES_ROOT")
DOWNLOAD_DIR = os.getenv("LT_DOWNLOAD_DIR")
COSMOS_CONT_TEXT = os.getenv("COSMOS_CONT_TEXT")
COSMOS_DB_TEXT=os.getenv("COSMOS_DB_TEXT")

print("FOR------DOWNLOAD_DIR ----",DOWNLOAD_DIR)

def main(blob_urls,text_container,image_container):
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

    # print("[INFO] Cleaning existing Cosmos container...")

    cosmos_client = CosmosClient(
        COSMOS_URL,
        credential=COSMOS_KEY,
        consistency_level=ConsistencyLevel.Eventual
    )

    # container = cosmos_client.get_database_client(DB_NAME).get_container_client(text_container)

    # items = container.read_all_items()
    # for item in items:
    #     container.delete_item(item=item, partition_key=item["id"])

    # print("[SUCCESS] All existing documents deleted.\n")

    # -------------------------------------------------------
    # STEP 2 — Download + extract blob files
    # -------------------------------------------------------

    container_blob = BLOB_CONTAINER_NAME  # from config.py

    print("[INFO] Downloading and extracting blob files...\n")

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

# # -------------------------------------------------------
# # CLI Runner
# # -------------------------------------------------------

# if __name__ == "__main__":

#     # blob_urls = [
#     #     'https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/Project%20Summary%20Report.pdf',
#     #         'https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/105709135MPK-001_TRF.doc',
#     #         # 'https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/105709135MPK-002_TRF.doc',
#     #         "https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/Lewco_CiS.pdf" ,
#     #         "https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/Qu-01414060-2.pdf"
#     #     ]
    
#     blob_urls =[
#         #'https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/Qu-01390131-0.pdf',
#     # 'https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/105709135MPK-002_TRF.doc',
#     "https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/CDR_105080268MPK-004.xlsx",
#     "https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/105581614MPK-001A_CR.docx",
#     # 'https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/Client_Information_Sheet_-_FUS_CIS_1_.pdf'
#     ]

#     main(blob_urls)


