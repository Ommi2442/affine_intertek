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
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_azure_ai.vectorstores import AzureCosmosDBNoSqlVectorSearch
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from azure.cosmos import CosmosClient
from langchain_openai import AzureOpenAIEmbeddings
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
DB_NAME            = os.getenv("DB_NAME")
CONT_NAME          = os.getenv("CONT_NAME")
AZURE_CONN_STRING  = os.getenv("AZURE_CONN_STRING")
BLOB_CONTAINER     = os.getenv("BLOB_CONTAINER")
COSMOS_URL         = os.getenv("COSMOS_URL")
COSMOS_KEY         = os.getenv("COSMOS_KEY")
CHAT_DEPLOY        = os.getenv("CHAT_DEPLOY")

print('AOAI_ENDPOINT', AOAI_ENDPOINT)

def extract_relevant_pdf_page_images(pdf_path, dpi=200):
    """
    STRICT version:
    Extracts ONLY highly-likely diagram/CAD/schematic pages.
    This is the same function from your notebook.
    """
    if fitz is None:
        print("[WARN] PyMuPDF (fitz) not available. Skipping image extraction.")
        return []

    pdf = fitz.open(pdf_path)
    base = os.path.basename(pdf_path)

    image_page_metadata = []

    for i, page in enumerate(pdf):
        page_num = i + 1

        try:
            text = page.get_text().strip()
        except Exception:
            text = ""
        try:
            images = page.get_images(full=True)
        except Exception:
            images = []
        try:
            drawings = page.get_drawings()
        except Exception:
            drawings = []
        try:
            blocks = page.get_text("blocks")
        except Exception:
            blocks = []

        text_len = len(text)
        num_blocks = len(blocks)
        vector_ops = len(drawings)

        # COMPUTE TOTAL RASTER AREA (sum of w*h for each image)
        raster_area = 0
        for img in images:
            try:
                w = img[2]
                h = img[3]
                raster_area += (w * h)
            except:
                continue

        # ---------------- STRICT RULES ----------------
        should_extract = False

        # 1. Large raster content (ignore tiny icons)
        if raster_area > 500000:
            should_extract = True

        # 5. Filename hint PLUS low text
        elif any(k in base.lower() for k in ["schematic", "cad", "drawing", "layout", "wiring"]) and text_len < 80:
            should_extract = True

        if not should_extract:
            continue

        # ---------------- Extract image ----------------
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


# #### load_and_split_pdfs_text---updated: ## CAD and Schematic Support TOGGLE SWITCH
def load_and_split_pdfs_text(
        pdf_paths,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
        extracted_texts=None,
        cad_schematics=True   # ⭐ NEW PARAM
    ):
    """
    pdf_paths: iterable of file paths
    extracted_texts: optional list

    Returns:
        chunks → text-only chunks
        image_page_metadata → selective CAD/schematic/table images 
                              (or empty list if cad_schematics=False)
    """

    docs = []
    image_page_metadata = []   # NEW
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
        keep_separator=False,
    )

    # -------------------------------------------------------------
    # STEP 1 — Process PDFs (Text + optional CAD/Schematic images)
    # -------------------------------------------------------------
    for path in pdf_paths:
        if not str(path).lower().endswith(".pdf"):
            continue

        # ---- TEXT EXTRACTION ----
        loader = PyPDFLoader(str(path))
        raw_docs = loader.load()
        base = os.path.basename(str(path))

        for d in raw_docs:
            page = int(d.metadata.get("page", 1))
            d.metadata["source_file"] = base
            d.metadata["page"] = page
            d.metadata["citation"] = f"{base}#page={page}"

        docs.extend(raw_docs)
        # print("Raw docs------",docs)

        # ---- OPTIONAL: CAD / SCHEMATIC IMAGE EXTRACTION ----
        if cad_schematics:   # ⭐ ONLY RUN IF ENABLED
            try:
                extracted_pages = extract_relevant_pdf_page_images(path)
                image_page_metadata.extend(extracted_pages)
            except Exception as e:
                print(f"[WARN] selective image extraction failed for {path}: {e}")
        else:
            # When disabled → return empty image list
            pass

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
                filename, text = None, None
                for k, v in item.items():
                    if isinstance(v, str) and v.strip():
                        filename = k
                        text = v
                        break
                if text is None:
                    filename = item.get("filename") or "unknown"
                    text = " ".join(str(v) for v in item.values())

            metadata = {
                "source_file": os.path.basename(str(filename)),
                "page": 1,
                "citation": os.path.basename(str(filename))
            }

            docs.append(SimpleNamespace(page_content=text or "", metadata=metadata))

    # -------------------------------------------------------------
    # STEP 3 — Chunking
    # -------------------------------------------------------------
    chunks = splitter.split_documents(docs)

    # -------------------------------------------------------------
    # FINAL RETURN
    # -------------------------------------------------------------
    return chunks, image_page_metadata

# upload_pdf_images_and_append_urls from notebook (verbatim)
from azure.storage.blob import BlobClient
import re


def sanitize_blob_name(name: str) -> str:
    """Azure Blob safe-name converter (removes unsafe characters)."""
    name = name.replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9_\-./]", "_", name)
    return name


def upload_pdf_images_and_append_urls(
        image_page_metadata,
        image_urls,
        conn_str,
        container):
    """
    Uploads only relevant PDF page images to Azure Blob Storage and
    appends blob URLs to image_urls in the correct vision-RAG format.
    """

    for item in image_page_metadata[:25]:
        local_path = item["local_image_path"]
        pdf_file = item["pdf_file"]

        page = item.get("page") or item.get("page_num")

        safe_pdf_name = sanitize_blob_name(pdf_file)

        image_filename = os.path.basename(local_path)
        safe_image_filename = sanitize_blob_name(image_filename)

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

            image_urls.append({
                "url": blob_url,
                "image_file": safe_image_filename,
                "pdf_file": pdf_file,
                "page": page
            })

        except Exception as e:
            print(f"[ERROR] Upload failed for {local_path}: {e}")

    return image_urls

# Main runner that mirrors the notebook logic

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
    db_client = client.get_database_client(DB_NAME)
    container_client = db_client.get_container_client(CONT_NAME)

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
    from pathlib import Path
    BASE_DIR = Path(__file__).resolve().parent
    DOWNLOAD_DIR = BASE_DIR  / "src_files"

    # 3) Process blob URLs (download/convert/extract)
    extracted_texts, image_urls, downloaded_pdf_paths, converted_pdf_paths = process_blob_urls_2(
        blob_urls, AZURE_CONN_STRING, BLOB_CONTAINER,
        download_dir=DOWNLOAD_DIR, keep_files=keep_files, verbose=verbose
    )

    pdf_paths = downloaded_pdf_paths + converted_pdf_paths

    # 4) (Re)create container with vector settings
    container = create_db_and_container(client, DB_NAME, VECTOR_PATH, EMBED_DIM, CONT_NAME)

    # 5) Build embeddings and vectorstore
    embeddings = build_embeddings(AOAI_ENDPOINT, AOAI_KEY, API_VERSION, EMBED_DEPLOY)
    vs = build_vectorstore(embeddings, client, DB_NAME, CONT_NAME)

    # 6) CAD/Schematic image extraction (notebook uses cad_schematics=False when calling)
    # We'll follow the notebook and run extraction if needed. Here we run extraction always but the
    # loader call below uses cad_schematics=False (match notebook call). To replicate notebook exactly,
    # we will set cad_schematics=False in load_and_split_pdfs_text call later.

    image_page_metadata = []
    try:
        # extract for each pdf
        for p in pdf_paths:
            try:
                pages_meta = extract_relevant_pdf_page_images(p)
                image_page_metadata.extend(pages_meta)
            except Exception as e:
                print(f"[WARN] extract_relevant_pdf_page_images failed for {p}: {e}")
    except Exception as e:
        print(f"[WARN] CAD extraction loop failed: {e}")

    # 7) Upload extracted images and append to image_urls
    try:
        image_urls = upload_pdf_images_and_append_urls(image_page_metadata, image_urls, AZURE_CONN_STRING, BLOB_CONTAINER)
    except Exception as e:
        print(f"[WARN] upload_pdf_images_and_append_urls failed: {e}")

    print("+++++++++++++++++",pdf_paths)
    print("--------------",converted_pdf_paths)
    # 8) Chunk PDFs and any extracted texts — notebook calls with cad_schematics=False
    chunks, image_page_metadata_returned = load_and_split_pdfs_text(
        pdf_paths, CHUNK_SIZE, CHUNK_OVERLAP, extracted_texts=extracted_texts, cad_schematics=True
    )

    # 9) Add IDs to chunks and ingest
    # Notebook had a commented line `chunks = add_ids_to_chunks(chunks)` but ingestion function expects docs/objects
    # The trf_utils.ingest_to_cosmos_parallel expects `vs` and `chunks` as documents with necessary fields.
    # We will call ingest_to_cosmos_parallel directly to mimic notebook behavior.

    try:
        ingest_to_cosmos_parallel(vs, chunks, batch_size=10, max_workers=10)
        
        
        BASE_DIR = Path(__file__).resolve().parent
        IMAGE_URLS_PATH = BASE_DIR / "image_urls.json"  # adjust if needed
        

        with open(IMAGE_URLS_PATH, "w") as f:
            json.dump(image_urls, f, indent=2)

    except Exception as e:
        print(f"[ERROR] ingest_to_cosmos_parallel failed: {e}")

    
    return {
            "project_id": project_id,
            "vs": vs,
            "image_urls": image_urls,
            "pdf_paths": pdf_paths,
            "downloaded_pdfs": downloaded_pdf_paths,
            "converted_pdfs": converted_pdf_paths,
            "image_page_metadata": image_page_metadata,
            "chunks_count": len(chunks)
        }