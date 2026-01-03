import os
import time
from urllib.parse import urlparse, unquote
from azure.cosmos import CosmosClient, ConsistencyLevel
import json

# Import helpers from your existing utils
from utility.trf_utils import *
import re
import tempfile
import shutil
import requests
from urllib.parse import urlparse, unquote
from email import policy
from email.parser import BytesParser
import extract_msg
import fitz
import uuid
from langchain_core.documents import Document
import io
import openpyxl
import xlrd
# from utils import *
from azure.storage.blob import BlobClient
from azure.core.exceptions import ResourceNotFoundError, AzureError
# from templates import *
import pandas as pd
import math
import copy
import time
from azure.cosmos import CosmosClient, PartitionKey, exceptions
import json, os
from azure.cosmos import CosmosClient, ConsistencyLevel
from typing import List, Dict, Any, Tuple
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_azure_ai.vectorstores import AzureCosmosDBNoSqlVectorSearch
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from azure.cosmos import CosmosClient
from operator import itemgetter
from langchain_core.runnables import (
    RunnableParallel, RunnableLambda, RunnableMap
)
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_never, RetryCallState
from openai import RateLimitError  # Make sure this import exists
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor, as_completed
from azure.core.exceptions import HttpResponseError
import time
from langchain_community.callbacks import get_openai_callback
pd.set_option('display.max_colwidth', None)  # Don't truncate cell text
pd.set_option('display.max_rows', None)      # Show all rows (optional)
pd.set_option('display.max_columns', None)
from dotenv import load_dotenv
from pathlib import Path
from openai import AzureOpenAI


load_dotenv()

# Chunking config
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
EMBED_DIM = 1536
VECTOR_PATH = "/vector"
TOP_K = 5


# Load environment variables
AOAI_ENDPOINT      = os.getenv("AOAI_ENDPOINT")
AOAI_KEY           = os.getenv("AOAI_KEY")
API_VERSION        = os.getenv("API_VERSION")
EMBED_DEPLOY       = os.getenv("EMBED_DEPLOY")
COSMOS_DB_TEXT     = os.getenv("COSMOS_DB_TEXT")
COSMOS_CONT_TEXT   = os.getenv("COSMOS_CONT_TEXT")
AZURE_CONN_STRING  = os.getenv("AZURE_CONN_STRING")
BLOB_CONTAINER     = os.getenv("BLOB_CONTAINER")
COSMOS_URL         = os.getenv("COSMOS_URL")
COSMOS_KEY         = os.getenv("COSMOS_KEY")
CHAT_DEPLOY        = os.getenv("CHAT_DEPLOY")
BLOB_CONT_NAME     = os.getenv("BLOB_CONT_NAME")
COSMOS_DB_IMAGE    = os.getenv("COSMOS_DB_IMAGE")
COSMOS_CONT_IMAGE  = os.getenv("COSMOS_CONT_IMAGE")
ENABLE_CAD_SCHEMATICS  = os.getenv("ENABLE_CAD_SCHEMATICS")



print('AOAI_ENDPOINT', AOAI_ENDPOINT)

# ----------------------------------------------------------------------------------------
# Azure OpenAI Client (shared for whole pipeline)
# ----------------------------------------------------------------------------------------
aoai_client = AzureOpenAI(
    api_key=AOAI_KEY,
    api_version=API_VERSION,
    azure_endpoint=AOAI_ENDPOINT,
)


# ----------------------------------------------------------------------------------------
# Embedding Builder — same as notebook
# ----------------------------------------------------------------------------------------

def build_embeddings():
    return AzureOpenAIEmbeddings(
        azure_endpoint=AOAI_ENDPOINT,
        api_key=AOAI_KEY,
        openai_api_version=API_VERSION,
        azure_deployment=EMBED_DEPLOY,
    )


# ----------------------------------------------------------------------------------------
# Vector Store Builder (for TEXT)
# EXACT logic from notebook (not altered)
# ----------------------------------------------------------------------------------------


def build_vectorstore_text():
    cosmos_client = CosmosClient(
        url=COSMOS_URL,
        credential=COSMOS_KEY
    )

    return AzureCosmosDBNoSqlVectorSearch(
        cosmos_client=cosmos_client,
        embedding=build_embeddings(),
        database_name=COSMOS_DB_TEXT,
        container_name=COSMOS_CONT_TEXT,

        vector_embedding_policy={
            "vectorEmbeddings": [{
                "path": "/vector",
                "dataType": "float32",
                "dimensions": EMBED_DIM,
                "distanceFunction": "cosine"
            }]
        },
        indexing_policy={
            "includedPaths": [{"path": "/*"}],
            "excludedPaths": [{"path": "/\"_etag\"/?"}, {"path": "/vector/*"}],
            "vectorIndexes": [{"path": "/vector", "type": "quantizedFlat"}],
        },
        cosmos_container_properties={"partition_key": "/id"},
        cosmos_database_properties={},
        vector_search_fields={
            "text_field": "text",
            "embedding_field": "vector",
            "metadata_field": "metadata"
        }
    )


# ----------------------------------------------------------------------------------------
# Vector Store Builder (for IMAGES)
# EXACT logic from notebook (not altered)
# ----------------------------------------------------------------------------------------
def build_vectorstore_image():
    cosmos_client = CosmosClient(
        url=COSMOS_URL,
        credential=COSMOS_KEY
    )

    return AzureCosmosDBNoSqlVectorSearch(
        cosmos_client=cosmos_client,
        embedding=build_embeddings(),
        database_name=COSMOS_DB_IMAGE,
        container_name=COSMOS_CONT_IMAGE,

        vector_embedding_policy={
            "vectorEmbeddings": [{
                "path": "/vector",
                "dataType": "float32",
                "dimensions": EMBED_DIM,
                "distanceFunction": "cosine"
            }]
        },
        indexing_policy={
            "includedPaths": [{"path": "/*"}],
            "excludedPaths": [{"path": "/\"_etag\"/?"}, {"path": "/vector/*"}],
            "vectorIndexes": [{"path": "/vector", "type": "quantizedFlat"}],
        },
        cosmos_container_properties={"partition_key": "/id"},
        cosmos_database_properties={},
        vector_search_fields={
            "text_field": "text",
            "embedding_field": "vector",
            "metadata_field": "metadata"
        }
    )


# ingestion_tool.py (continued)
# --------------------------------------------------------
# SECTION 2.2 — PDF Text Loading, CAD/Schematic Image Extraction,
#                Chunking Logic, Image Upload to Azure Blob Storage
# --------------------------------------------------------


# -------------------------------------------------------------------------
# Utility: Sanitize blob names (same as in notebook)
# -------------------------------------------------------------------------
def sanitize_blob_name(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9_\-./]", "_", name)
    return name


# -------------------------------------------------------------------------
# STRICT CAD/Schematic Page Detector (EXACT logic from notebook)
# -------------------------------------------------------------------------
def extract_relevant_pdf_page_images(pdf_path, dpi=200):
    """
    STRICT selection of pages containing diagrams / CAD / schematics.
    EXACT code copied from your notebook. No modifications.
    """

    pdf = fitz.open(pdf_path)
    base = os.path.basename(pdf_path)

    image_page_metadata = []

    for i, page in enumerate(pdf):
        page_num = i + 1

        text = page.get_text().strip()
        images = page.get_images(full=True)
        drawings = page.get_drawings()
        blocks = page.get_text("blocks")

        text_len = len(text)
        num_blocks = len(blocks)
        vector_ops = len(drawings)

        raster_area = 0
        for img in images:
            try:
                w = img[2]
                h = img[3]
                raster_area += (w * h)
            except:
                continue

        # --- EXACT strict rules from notebook ---
        should_extract = False

        if raster_area > 500000:
            should_extract = True
        elif vector_ops > 150:
            should_extract = True
        elif text_len < 30:
            should_extract = True
        elif num_blocks > 30 and text_len < 150:
            should_extract = True
        elif (
            any(k in text.lower() for k in ["label", "regulatory"])
            and vector_ops > 20
            and text_len < 600
        ):
            should_extract = True
        elif any(k in base.lower() for k in ["schematic", "cad", "drawing", "layout", "wiring"]) and text_len < 80:
            should_extract = True
        elif len(pdf) <= 3 and (vector_ops > 20 or text_len < 600):
            should_extract = True

        if not should_extract:
            continue

        # ---- Extract the page image EXACTLY like notebook ----
        try:
            pix = page.get_pixmap(dpi=dpi)
            img_path = f"{pdf_path}_page_{page_num}.png"
            pix.save(img_path)

            image_page_metadata.append({
                "pdf_file": base,
                "page": page_num,
                "local_image_path": img_path,
                "text_length": text_len,
                "raster_area": raster_area,
                "vector_ops": vector_ops,
                "blocks": num_blocks,
            })

        except Exception as e:
            print(f"[WARN] Image extraction failed for {base} page {page_num}: {e}")

    return image_page_metadata


# -------------------------------------------------------------------------
# PDF Loader + Text Chunking (EXACT logic from notebook)
# -------------------------------------------------------------------------
def load_and_split_pdfs_text(
    pdf_paths,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    extracted_texts=None,
    cad_schematics=True
):
    """
    EXACT implementation from your notebook.
    Returns:
        chunks → list of text Document objects
        image_page_metadata → list of schematic image metadata
    """

    docs = []
    image_page_metadata = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
        keep_separator=False,
    )

    # ----- STEP 1: PDF TEXT EXTRACTION -----
    for path in pdf_paths:
        if not str(path).lower().endswith(".pdf"):
            continue

        loader = PyPDFLoader(str(path))
        raw_docs = loader.load()
        base = os.path.basename(str(path))

        for d in raw_docs:
            page = int(d.metadata.get("page", 1))
            d.metadata["source_file"] = base
            d.metadata["page"] = page
            d.metadata["citation"] = f"{base}#page={page}"

        docs.extend(raw_docs)

        # ----- STEP 2: CAD/Schematic Image Extraction -----
        if cad_schematics:
            try:
                extracted = extract_relevant_pdf_page_images(path)
                image_page_metadata.extend(extracted)
            except Exception as e:
                print(f"[WARN] selective image extraction failed for {path}: {e}")

    # ----- STEP 3: External extracted text -----
    # -------------------------------------------------------------
    # STEP 2 — Process externally extracted text files (unchanged)
    # -------------------------------------------------------------
    if extracted_texts:
        for item in extracted_texts:
            if not isinstance(item, dict):
                continue

            if "filename" in item and "text" in item:
                filename = item["filename"]
                text = item["text"]
            elif len(item) == 1:
                filename, text = next(iter(item.items()))
            elif "text" in item:
                filename = item.get("filename") or "unknown"
                text = item["text"]
            else:
                filename = item.get("filename") or "unknown"
                text = None
                for k, v in item.items():
                    if isinstance(v, str) and v.strip():
                        filename = k
                        text = v
                        break
                if text is None:
                    text = " ".join(str(v) for v in item.values())

            metadata = {
                "source_file": os.path.basename(str(filename)),
                "page": 1,
                "citation": os.path.basename(str(filename))
            }

            # ORIGINAL WORKING VERSION — KEEP SimpleNamespace
            docs.append(
                SimpleNamespace(
                    page_content=text or "",
                    metadata=metadata
                )
            )



    # ----- STEP 4: Chunking -----
    chunks = splitter.split_documents(docs)

    return chunks, image_page_metadata


# -------------------------------------------------------------------------
# Upload extracted PDF page images → Azure Blob Storage
# (EXACT logic from notebook)
# -------------------------------------------------------------------------
# def upload_pdf_images_and_append_urls(
#     image_page_metadata,
#     image_urls,
#     conn_str,
#     container
# ):
#     """
#     Takes CAD/schematic page images extracted above,
#     uploads each PNG to blob storage,
#     appends URLs in same format as notebook.
#     """

#     for item in image_page_metadata:
#         local_path = item["local_image_path"]
#         pdf_file = item["pdf_file"]
#         page = item.get("page") or item.get("page_num")

#         safe_pdf_name = sanitize_blob_name(pdf_file)
#         safe_image_filename = sanitize_blob_name(os.path.basename(local_path))

#         blob_name = f"{safe_pdf_name}/page_{page}.png"

#         try:
#             blob = BlobClient.from_connection_string(
#                 conn_str,
#                 container_name=container,
#                 blob_name=blob_name,
#             )

#             with open(local_path, "rb") as f:
#                 blob.upload_blob(f, overwrite=True)

#             blob_url = blob.url

#             # EXACT return structure from notebook
#             image_urls.append({
#                 "url": blob_url,
#                 "image_file": safe_image_filename,
#                 "pdf_file": pdf_file,
#                 "page": page
#             })

#         except Exception as e:
#             print(f"[ERROR] Upload failed for {local_path}: {e}")

#     return image_urls



def upload_pdf_images_and_append_urls(
    image_page_metadata,
    image_urls,
    conn_str,
    container,
    max_workers=8
):
    """
    Takes CAD/schematic page images extracted above,
    uploads each PNG to blob storage in parallel,
    appends URLs in same format as notebook.
    """

    def upload_single(item):
        local_path = item["local_image_path"]
        pdf_file = item["pdf_file"]
        page = item.get("page") or item.get("page_num")

        safe_pdf_name = sanitize_blob_name(pdf_file)
        safe_image_filename = sanitize_blob_name(os.path.basename(local_path))

        blob_name = f"{safe_pdf_name}/page_{page}.png"

        try:
            blob = BlobClient.from_connection_string(
                conn_str,
                container_name=container,
                blob_name=blob_name,
            )

            with open(local_path, "rb") as f:
                blob.upload_blob(f, overwrite=True)

            blob_url = blob.url

            return {
                "url": blob_url,
                "image_file": safe_image_filename,
                "pdf_file": pdf_file,
                "page": page
            }

        except Exception as e:
            print(f"[ERROR] Upload failed for {local_path}: {e}")
            return None

    # -------------------------------------------------
    # PARALLEL EXECUTION
    # -------------------------------------------------
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(upload_single, item)
            for item in image_page_metadata
        ]

        for future in as_completed(futures):
            result = future.result()
            if result:
                image_urls.append(result)

    return image_urls


# ingestion_tool.py (continued)
# --------------------------------------------------------
# SECTION 3.1 — Image URL Extraction + Agent-Based OCR Pipeline
# --------------------------------------------------------


# --------------------------------------------------------
# Extract image name from blob URL — EXACT as notebook
# --------------------------------------------------------
def extract_clean_image_name(blob_url: str):
    parsed = urlparse(blob_url)
    path = parsed.path
    parts = path.split("/")

    pdf_file = None
    for part in parts:
        if part.lower().endswith(".pdf"):
            pdf_file = part
            break

    image_filename = os.path.basename(path)

    if pdf_file:
        return f"{pdf_file}/{image_filename}"
    else:
        return image_filename


# --------------------------------------------------------
# Wrapper: turn mixed list into plain list of URLs
# --------------------------------------------------------
def extract_urls(mixed_list):
    urls = []

    for item in mixed_list:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict) and "url" in item:
            urls.append(item["url"])

    return urls


# --------------------------------------------------------
# The ORIGINAL process_single_image replaced by an AGENT CALL
# --------------------------------------------------------
MAX_THREADS = 10
MAX_RETRIES = 5
INITIAL_BACKOFF = 3


def _direct_llm_fallback(url, index, total, vision_deploy_name):
    """
    Only used if agent not triggered correctly.
    Matches original notebook LLM behavior exactly.
    """

    resp = requests.get(url, timeout=20)
    resp.raise_for_status()

    completion = aoai_client.chat.completions.create(
        model=vision_deploy_name,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": url},
                    {
                        "type": "text",
                        "text": (
                            "Perform OCR on this image and also provide a detailed "
                            "description. Combine both into one response."
                        ),
                    },
                ],
            }
        ],
        max_tokens=2048,
    )

    extracted_text = completion.choices[0].message.content.strip()
    image_name = extract_clean_image_name(url)

    return Document(
        page_content=extracted_text,
        metadata={
            "image_name": image_name,
            "blob_url": url,
            "source_type": "image",
        },
    )


# --------------------------------------------------------
# Agent Function Schema (EXACT as notebook)
# --------------------------------------------------------
image_desc_schema = {
    "name": "image_description_agent",
    "description": "OCR + description on an Azure Blob image URL.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "vision_deploy_name": {"type": "string"},
            "index": {"type": "integer"},
            "total": {"type": "integer"},
        },
        "required": ["url", "vision_deploy_name"],
    }
}


# --------------------------------------------------------
# run_function_agent_llm — EXACT as notebook
# --------------------------------------------------------
def run_function_agent_llm(client, user_prompt: str, function_schema: dict, python_callback: callable):
    response = client.chat.completions.create(
        model=CHAT_DEPLOY,
        messages=[{"role": "user", "content": user_prompt}],
        functions=[function_schema],
    )

    msg = response.choices[0].message

    if msg.function_call:
        fn_args = json.loads(msg.function_call.arguments)
        return python_callback(**fn_args)

    return msg.content


# --------------------------------------------------------
# Callback executed when LLM triggers function_call
# --------------------------------------------------------
def image_desc_callback(url, vision_deploy_name, index=1, total=1):
    """
    Internally calls _direct_llm_fallback so that return format matches EXACT original logic.
    """
    try:
        return _direct_llm_fallback(url, index, total, vision_deploy_name)
    except Exception as e:
        print(f"[ERROR] Fallback LLM failed for {url}: {e}")
        return None


# --------------------------------------------------------
# Main Agent Wrapper — same structure as notebook
# --------------------------------------------------------
def image_desc_agent(blob_url, vision_deploy_name="gpt-4.1", index=1, total=1):

    payload = {
        "url": blob_url,
        "vision_deploy_name": vision_deploy_name,
        "index": index,
        "total": total,
    }

    return run_function_agent_llm(
        aoai_client,
        user_prompt="Use the image_description_agent tool on: " + json.dumps(payload),
        function_schema=image_desc_schema,
        python_callback=image_desc_callback,
    )


# --------------------------------------------------------
# NEW process_single_image → replaced with AGENT call
# --------------------------------------------------------
def process_single_image(url, index, total, vision_deploy_name):
    """
    Calls the agent and ALWAYS returns a Document object.
    This guarantees downstream ingestion will not break.
    """

    print(f"[INFO] Processing image {index}/{total} → {url}")
    backoff = INITIAL_BACKOFF

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            # Validate URL
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()

            # Call the agent
            result = image_desc_agent(
                blob_url=url,
                vision_deploy_name=vision_deploy_name,
                index=index,
                total=total
            )

            # -------------------------------------------------------------------
            # NORMALIZE OUTPUT → ALWAYS A Document (required for add_ids_to_chunks)
            # -------------------------------------------------------------------
            cleaned_name = extract_clean_image_name(url)

            # CASE 1: Agent correctly returned Document
            if isinstance(result, Document):
                return result

            # CASE 2: Agent returned dict (tool responses sometimes do this)
            if isinstance(result, dict):
                text = result.get("text") or result.get("content") or str(result)
                return Document(
                    page_content=text,
                    metadata={"image_name": cleaned_name, "blob_url": url, "source_type": "image"}
                )

            # CASE 3: Agent returned string
            if isinstance(result, str):
                return Document(
                    page_content=result,
                    metadata={"image_name": cleaned_name, "blob_url": url, "source_type": "image"}
                )

            # CASE 4: Anything else (fallback)
            return Document(
                page_content=str(result),
                metadata={"image_name": cleaned_name, "blob_url": url, "source_type": "image"}
            )

        except Exception as e:
            print(f"[WARN] Attempt {attempt}/{MAX_RETRIES} failed for image {index} → {url}: {e}")

            if attempt == MAX_RETRIES:
                print(f"[ERROR] Giving up after {MAX_RETRIES} attempts → {url}")
                return Document(
                    page_content="OCR extraction failed.",
                    metadata={"image_name": extract_clean_image_name(url), "blob_url": url, "source_type": "image", "error": str(e)}
                )

            print(f"[INFO] Cooling down {backoff}s before retry…")
            time.sleep(backoff)
            backoff *= 2



# --------------------------------------------------------
# Multi-threaded loader (unchanged except for agent call inside)
# --------------------------------------------------------
def load_and_process_images(image_urls, vision_deploy_name=CHAT_DEPLOY):
    docs = []
    total = len(image_urls)

    print(f"[START] Processing {total} images with up to {MAX_THREADS} threads.\n")

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:

        futures = {
            executor.submit(process_single_image, url, idx + 1, total, vision_deploy_name): idx
            for idx, url in enumerate(image_urls)
        }

        for future in as_completed(futures):
            idx = futures[future]
            url = image_urls[idx]

            try:
                result = future.result()
                if result is not None:
                    docs.append(result)
                else:
                    print(f"[ERROR] Image {idx+1}/{total} → returned None")

            except Exception as e:
                print(f"[FATAL] Unexpected error for {url}: {e}")

    print(f"\n[COMPLETE] Finished processing {total} images.\n")
    return docs


# ingestion_tool.py (continued)
# --------------------------------------------------------
# SECTION 4 — Full Orchestration: run_full_ingestion()
# --------------------------------------------------------

def clear_cosmos_container(database_name, container_name):
    """
    Clears all items from a Cosmos DB container.
    EXACT logic from notebook.
    """
    client = CosmosClient(COSMOS_URL, credential=COSMOS_KEY)

    container = client.get_database_client(database_name).get_container_client(container_name)

    print(f"[INFO] Deleting all items in {database_name}.{container_name} ...")

    try:
        items = container.read_all_items()
        for item in items:
            try:
                container.delete_item(item=item, partition_key=item["id"])
            except Exception as e:
                print(f"[WARN] Failed deleting item {item.get('id')}: {e}")

        print("[SUCCESS] All documents deleted successfully!\n")

    except Exception as e:
        print(f"[ERROR] Could not list/delete items: {e}")



def ingest_files_from_blob_urls_create_embeddings(download_dir,blob_urls: list, project_id: str, keep_files: bool = True, verbose: bool = True):
    """
    Single-call function that performs the full notebook ingestion pipeline.
    - blob_urls: list of full blob URLs
    - download_dir: local directory to store downloads and converted pdfs
    - keep_files: whether to keep local downloaded files
    - verbose: print progress

    NOTE: This function will DELETE ALL DOCUMENTS in the target Cosmos container (as per notebook).
    """

    # 1) Cosmos client and container
    client = CosmosClient(COSMOS_URL, credential=COSMOS_KEY, consistency_level=ConsistencyLevel.Eventual)
    db_client = client.get_database_client(COSMOS_DB_TEXT)
    container_client = db_client.get_container_client(COSMOS_CONT_TEXT)

    # 2) Delete all items (not reversible)
    try:
        items = container_client.read_all_items()
        for item in items:
            try:
                container_client.delete_item(item=item, partition_key=item["id"])
            except Exception as e:
                print(f"[WARN] Failed to delete item {item.get('id')}: {e}")
        print("All documents deleted successfully!")
    except Exception as e:
        print(f"[WARN] Could not enumerate/delete items: {e}")

    BASE_DIR = Path(__file__).resolve().parent
    DOWNLOAD_DIR = BASE_DIR  / "src_files"

    # 3) Process blob URLs (download/convert/extract)
    extracted_texts, image_urls_raw, downloaded_pdf_paths, converted_pdf_paths = process_blob_urls_2(
        blob_urls, AZURE_CONN_STRING, BLOB_CONTAINER,
        download_dir=DOWNLOAD_DIR, keep_files=keep_files, verbose=verbose
    )

    pdf_paths = downloaded_pdf_paths + converted_pdf_paths

    print(f"[INFO] Extracted text files: {len(extracted_texts)}")
    print(f"[INFO] Initial image URLs: {len(image_urls_raw)}")
    print(f"[INFO] Total PDFs: {len(pdf_paths)}\n")


    print("\n======================================")
    print("   STEP 2 — LOAD + SPLIT PDF TEXT      ")
    print("======================================\n")

    chunks, image_page_metadata = load_and_split_pdfs_text(
        pdf_paths,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
        extracted_texts=extracted_texts,
        cad_schematics=ENABLE_CAD_SCHEMATICS,
    )

    print(f"[INFO] Total text chunks produced: {len(chunks)}")
    print(f"[INFO] CAD/Schematic pages extracted: {len(image_page_metadata)}\n")


    print("\n======================================")
    print("   STEP 3 — CREATE TEXT VECTOR STORE   ")
    print("======================================\n")

    # Clear DB (EXACT notebook logic)
    clear_cosmos_container(COSMOS_DB_TEXT, COSMOS_CONT_TEXT)

    vectorstore_text = build_vectorstore_text()

    # Assign UUIDs to each chunk
    chunks_uuid = add_ids_to_chunks(chunks)

    # Ingest in parallel
    ingest_to_cosmos_parallel(vectorstore_text, chunks_uuid, batch_size=10, max_workers=10)

    print("\n[SUCCESS] Text ingestion completed.\n")


    print("\n=====================================================")
    print("   STEP 4 — UPLOAD CAD/SCHEMATIC PAGE IMAGES         ")
    print("=====================================================\n")

    image_urls = upload_pdf_images_and_append_urls(
        image_page_metadata=image_page_metadata,
        image_urls=image_urls_raw,
        conn_str=AZURE_CONN_STRING,
        container=BLOB_CONT_NAME,   # same notebook container
    )

    # Turn into flat list
    img_links = extract_urls(image_urls)

    print(f"[INFO] Total images for OCR (blob URLs): {len(img_links)}\n")


    print("\n==============================================")
    print("   STEP 5 — IMAGE OCR USING AGENT PIPELINE     ")
    print("==============================================\n")

    docs_image = load_and_process_images(img_links, vision_deploy_name=CHAT_DEPLOY)

    print(f"[SUCCESS] Finished OCR for {len(docs_image)} images.\n")


    print("\n==============================================")
    print("   STEP 6 — CREATE IMAGE VECTOR STORE          ")
    print("==============================================\n")

    # Clear DB (EXACT notebook logic)
    clear_cosmos_container(COSMOS_DB_IMAGE, COSMOS_CONT_IMAGE)

    vectorstore_image = build_vectorstore_image()

    # Assign UUIDs to image docs
    docs_image_uuid = add_ids_to_chunks(docs_image)

    # Ingest
    ingest_to_cosmos_parallel(vectorstore_image, docs_image_uuid, batch_size=10, max_workers=10)

    print("\n[SUCCESS] Image ingestion completed.\n")


    print("\n==============================================")
    print("         FULL INGESTION PIPELINE DONE         ")
    print("==============================================\n")

    
    return {
            "project_id": project_id,
            "image_urls": img_links,
            "pdf_paths": pdf_paths,
            "downloaded_pdfs": downloaded_pdf_paths,
            "converted_pdfs": converted_pdf_paths,
            "image_page_metadata": image_page_metadata,
            "chunks_count": len(chunks)
        }



