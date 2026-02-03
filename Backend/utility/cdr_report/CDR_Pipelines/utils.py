# utils.py
from langchain_core.documents import Document as LCDocument
import uuid
import os
import re
import tempfile
import shutil
import requests
from urllib.parse import urlparse, unquote
from email import policy
from email.parser import BytesParser
import extract_msg
import io
import openpyxl
import xlrd
from concurrent.futures import ThreadPoolExecutor, as_completed
import utility.cdr_report.CDR_Pipelines.configs as configs
from azure.storage.blob import BlobClient
from azure.core.exceptions import ResourceNotFoundError, AzureError, HttpResponseError

import pandas as pd
from docx import Document
import math
import copy
import time

from azure.storage.blob import BlobServiceClient
from urllib.parse import quote

from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_azure_ai.vectorstores import AzureCosmosDBNoSqlVectorSearch
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from azure.cosmos import CosmosClient, PartitionKey, exceptions
import json

from types import SimpleNamespace
from collections import defaultdict
import subprocess
import threading
import time
import random
from openai import RateLimitError

import random, time, logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore, Lock
from openai import RateLimitError
from azure.core.exceptions import ServiceResponseError, ServiceRequestError
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

_EMBED_SEMAPHORE = Semaphore(5)  # Limit concurrent embeddings
_VS_LOCK = Lock()  # Protect vector store if not thread-safe

from utility.cdr_report.CDR_Pipelines.configs import (
    container,
    IMAGE_EXTS,
    AZURE_CONN_STRING,
    AOAI_ENDPOINT,
    AOAI_KEY,
    API_VERSION,
    EMBED_DEPLOY,
    CHAT_DEPLOY,
    COSMOS_URL,
    COSMOS_KEY,
    COSMOS_DB,
    COSMOS_CONT,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K,
    DB_NAME,
    CONT_NAME,
    EMBED_DIM,
    VECTOR_PATH,
    PARTITION_KEY,
    cosmos_client
)

# Data Extraction

def _extract_from_msg(path):
    try:
        m = extract_msg.Message(path)
        m_message = m.body or ""
        # also include subject and from/to if helpful
        hdrs = []
        if getattr(m, "subject", None):
            hdrs.append(f"Subject: {m.subject}")
        if getattr(m, "sender", None):
            hdrs.append(f"From: {m.sender}")
        if getattr(m, "to", None):
            hdrs.append(f"To: {m.to}")
        header_text = "\n".join(hdrs)
        return (header_text + "\n\n" + m_message).strip()
    except Exception as e:
        # fallback to empty string on failure
        return ""

def _extract_from_eml(path):
    with open(path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    # prefer plain text body
    body = ""
    if msg.is_multipart():
        # prefer 'plain' parts
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    body += part.get_content().strip() + "\n"
                except Exception:
                    # fallback decode
                    payload = part.get_payload(decode=True)
                    if payload:
                        try:
                            body += payload.decode(errors="ignore").strip() + "\n"
                        except Exception:
                            pass
        if not body:
            # try html fallback (strip tags lightly)
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try:
                        html = part.get_content()
                    except Exception:
                        payload = part.get_payload(decode=True)
                        html = payload.decode(errors="ignore") if payload else ""
                    # naive strip tags
                    text = re.sub("<[^<]+?>", "", html)
                    body += text.strip()
    else:
        try:
            body = msg.get_content()
        except Exception:
            payload = msg.get_payload(decode=True)
            body = payload.decode(errors="ignore") if payload else ""
    return body

def _extract_from_xlsx(path):
    out = []
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            # join non-None cells with space
            row_vals = [str(c) for c in row if c is not None]
            if row_vals:
                out.append(" ".join(row_vals))
    return "\n".join(out)

def _extract_from_xls(path):
    out = []
    book = xlrd.open_workbook(path, on_demand=True)
    for i in range(book.nsheets):
        sheet = book.sheet_by_index(i)
        for r in range(sheet.nrows):
            vals = []
            for c in sheet.row(r):
                try:
                    vals.append(str(c.value))
                except Exception:
                    pass
            if vals:
                out.append(" ".join(vals))
    return "\n".join(out)

def _guess_ext_from_url(url):
    path = urlparse(url).path
    path = unquote(path)
    _, ext = os.path.splitext(path)
    if ext:
        return ext.lstrip(".").lower()
    return None

def _extract_from_txt(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        try:
            with open(path, "rb") as f:
                return f.read().decode("utf-8", errors="ignore")
        except Exception:
            return ""

def _blob_name_from_url(url, container):
    """
    Given a blob URL and container name, return the blob_name relative to container.
    Example URL: https://account.blob.core.windows.net/container/path/to/blob.txt
    returns: "path/to/blob.txt"
    """
    p = urlparse(url).path  # '/container/path/to/blob.txt'
    p = unquote(p)
    # remove leading slash
    if p.startswith("/"):
        p = p[1:]
    # if container prefix present, strip it
    if container and p.startswith(container + "/"):
        return p[len(container) + 1 :]
    # if container matches exactly (no path), return empty blob name -> caller should handle
    if container and p == container:
        return ""
    # otherwise return the full path (best-effort)
    return p

## Getting Blob urls

from azure.storage.blob import BlobServiceClient
import utility.cdr_report.CDR_Pipelines.configs as configs

def get_blob_urls(conn_str: str, container: str) -> list[str]:
    """
    Returns correct, downloadable blob URLs for the current project.
    """

    configs.require_runtime()
    project_id = configs._runtime.project_id

    service_client = BlobServiceClient.from_connection_string(conn_str)
    container_client = service_client.get_container_client(container)

    blob_urls: list[str] = []

    prefix = f"Documents/{project_id}/source_documents/"
    for blob in container_client.list_blobs(name_starts_with=prefix):
        blob_client = container_client.get_blob_client(blob.name)
        blob_urls.append(blob_client.url)   # ✅ ALWAYS CORRECT

    return blob_urls

def safe_download_blob_file(conn_str, container, blob_name, local_path):
    """
    Try to download blob; returns (ok: bool, error_message_or_None)
    Uses BlobClient.get_blob_properties() to check existence first for clearer errors.
    """
    try:
        blob = BlobClient.from_connection_string(conn_str, container, blob_name)
    except Exception as e:
        return False, f"BlobClient creation failed: {e}"

    try:
        blob.get_blob_properties()
    except ResourceNotFoundError:
        return False, f"Blob not found: {blob_name}"
    except AzureError as e:
        # could be auth or network
        return False, f"Azure error checking blob properties: {e}"

    try:
        with open(local_path, "wb") as f:
            f.write(blob.download_blob().readall())
        return True, None
    except AzureError as e:
        return False, f"Azure download error: {e}"
    except Exception as e:
        return False, f"General download error: {e}"


def pdf_convert(file1, file2):
    # 1) Try env var (optional)
    soffice = os.environ.get("LIBREOFFICE_SOFFICE")

    # 2) Fallback: default Windows install path (works in your case)
    if not soffice:
        default_win = r"C:\Program Files\LibreOffice\program\soffice.exe"
        if os.path.exists(default_win):
            soffice = default_win

    # 3) Last fallback: PATH lookup
    if not soffice:
        soffice = shutil.which("soffice") or shutil.which("libreoffice")

    if not soffice:
        raise RuntimeError("LibreOffice not found (soffice.exe).")

    outdir = os.path.dirname(os.path.abspath(file2))
    os.makedirs(outdir, exist_ok=True)

    cmd = [
        soffice,
        "--headless", "--nologo", "--nofirststartwizard",
        "--convert-to", "pdf",
        "--outdir", outdir,
        os.path.abspath(file1),
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed:\n{result.stderr}")

    produced = os.path.join(outdir, os.path.splitext(os.path.basename(file1))[0] + ".pdf")

    if not os.path.exists(produced):
        raise RuntimeError(f"PDF not produced at expected location: {produced}")

    # Ensure output is exactly file2
    if os.path.abspath(produced) != os.path.abspath(file2):
        if os.path.exists(file2):
            os.remove(file2)
        os.replace(produced, file2)

    return file2


def process_blob_urls_2(blob_urls, conn_str, container,
                        download_dir=None, keep_files=False, verbose=True):
    """
    Robust process_blob_urls:
      - expects list of full blob URLs (SAS tokens OK)
      - downloads docx, txt, eml, msg, xls, xlsx, pdf via download_blob_file (via safe_download_blob_file)
      - converts docx -> pdf via pdf_convert then (previously extracted text; now we only record converted pdf path)
      - does not download images; returns their URLs in image_urls
      - returns (extracted_texts, image_urls, downloaded_pdf_paths, converted_pdf_paths)
    """

    # 🔹 1. Normalize `container` to a *string* name (handles ContainerClient/ContainerProxy)
    if hasattr(container, "container_name"):
        container_name = container.container_name
    elif hasattr(container, "name"):
        container_name = container.name
    else:
        container_name = container  # assume it's already a string or None

    container_name = str(container_name) if container_name is not None else None

    tempdir = None
    if download_dir:
        os.makedirs(download_dir, exist_ok=True)
        out_dir = download_dir
    else:
        tempdir = tempfile.mkdtemp(prefix="blob_download_")
        out_dir = tempdir

    extracted_texts = []
    image_urls = []
    downloaded_pdf_paths = []   # newly added: local paths of downloaded PDFs
    converted_pdf_paths = []    # newly added: pdf paths produced from docx conversion

    try:
        for idx, url in enumerate(blob_urls):
            if verbose:
                print(f"[INFO] Processing URL #{idx}: {url}")

            try:
                # determine extension from URL path
                parsed = urlparse(url)
                path = unquote(parsed.path)
                base = os.path.basename(path)
                ext = os.path.splitext(base)[1].lstrip(".").lower() if base else ""

                # 🔹 2. Use container_name (string), NOT container object
                blob_name = _blob_name_from_url(url, container_name)
                if not blob_name:
                    if verbose:
                        print(f"[WARN] Could not determine blob_name for url: {url}")
                    extracted_texts.append({"filename": base or f"file_{idx}", "text": ""})
                    continue

                # If it's an image (by extension), skip download and collect url
                if ext and ext in IMAGE_EXTS:
                    if verbose:
                        print(f"[INFO] Detected image, skipping download: {base}")
                    image_urls.append(url)
                    continue

                # local filename and download path
                base_name = os.path.basename(blob_name) or f"download_{idx}"
                local_path = os.path.join(out_dir, base_name)

                # 🔹 3. Also pass container_name to safe_download_blob_file
                ok, err = safe_download_blob_file(conn_str, container_name, blob_name, local_path)
                if not ok:
                    if verbose:
                        print(f"[WARN] Failed to download '{blob_name}': {err}")
                    extracted_texts.append({"filename": base_name, "text": ""})
                    continue

                # If extension missing, try to infer from downloaded file name
                if not ext:
                    ext = os.path.splitext(local_path)[1].lstrip(".").lower()

                ext = (ext or "").lower()
                
                if ext in ("docx", "doc"):
                    pdf_path = os.path.splitext(local_path)[0] + ".pdf"
                    try:
                        pdf_convert(local_path, pdf_path)  # your existing docx2pdf-based function
                        converted_pdf_paths.append(pdf_path)
                        if verbose:
                            print(f"[INFO] Converted {ext.upper()} to PDF: {local_path} -> {pdf_path}")
                    except Exception as e:
                        if verbose:
                            print(f"[WARN] {ext}->pdf conversion failed for {base_name}: {e}")
                    continue

                # PDF -> record downloaded path (do NOT extract text)
                if ext == "pdf":
                    downloaded_pdf_paths.append(local_path)
                    if verbose:
                        print(f"[INFO] Downloaded PDF recorded: {local_path}")
                    continue

                # TXT
                if ext == "txt":
                    try:
                        text = _extract_from_txt(local_path)
                        extracted_texts.append({"filename": base_name, "text": text or ""})
                    except Exception as e:
                        if verbose:
                            print(f"[WARN] TXT extract failed for {base_name}: {e}")
                        extracted_texts.append({"filename": base_name, "text": ""})
                    continue

                # EML
                if ext == "eml":
                    try:
                        text = _extract_from_eml(local_path)
                        extracted_texts.append({"filename": base_name, "text": text or ""})
                    except Exception as e:
                        if verbose:
                            print(f"[WARN] EML extract failed for {base_name}: {e}")
                        extracted_texts.append({"filename": base_name, "text": ""})
                    continue

                # MSG
                if ext == "msg":
                    try:
                        text = _extract_from_msg(local_path)
                        extracted_texts.append({"filename": base_name, "text": text or ""})
                    except Exception as e:
                        if verbose:
                            print(f"[WARN] MSG extract failed for {base_name}: {e}")
                        extracted_texts.append({"filename": base_name, "text": ""})
                    continue

                # XLSX
                if ext == "xlsx":
                    try:
                        text = _extract_from_xlsx(local_path)
                        extracted_texts.append({"filename": base_name, "text": text or ""})
                    except Exception as e:
                        if verbose:
                            print(f"[WARN] XLSX extract failed for {base_name}: {e}")
                        extracted_texts.append({"filename": base_name, "text": ""})
                    continue

                # XLS
                if ext == "xls":
                    try:
                        text = _extract_from_xls(local_path)
                        extracted_texts.append({"filename": base_name, "text": text or ""})
                    except Exception as e:
                        if verbose:
                            print(f"[WARN] XLS extract failed for {base_name}: {e}")
                        extracted_texts.append({"filename": base_name, "text": ""})
                    continue

                # Unknown extension -> try reading as text
                try:
                    text = _extract_from_txt(local_path)
                    extracted_texts.append({"filename": base_name, "text": text or ""})
                except Exception:
                    extracted_texts.append({"filename": base_name, "text": ""})

            except Exception as e:
                if verbose:
                    print(f"[ERROR] Unexpected error for url {url}: {e}")
                extracted_texts.append({"filename": os.path.basename(url), "text": ""})

        return extracted_texts, image_urls, downloaded_pdf_paths, converted_pdf_paths

    finally:
        if tempdir and not keep_files:
            try:
                shutil.rmtree(tempdir)
            except Exception:
                pass


def download_images_from_blob_urls(
    blob_urls,
    conn_str: str,
    container: str,
    download_dir: str = configs.SRC_FILES_DIR,   # ✅ same folder as your other docs
    overwrite: bool = False,
    verbose: bool = True,
):
    """
    Given a list of blob URLs, download ONLY image blobs into `download_dir`
    (e.g. 'src_files'), without creating any extra subfolder.

    Returns a list of local file paths for successfully downloaded images.
    """
    service_client = BlobServiceClient.from_connection_string(conn_str)
    container_client = service_client.get_container_client(container)

    downloaded_paths = []

    for idx, url in enumerate(blob_urls):
        if verbose:
            print(f"[INFO] Processing URL #{idx}: {url}")

        try:
            # 1) Get filename + extension from URL path
            parsed = urlparse(url)
            path = unquote(parsed.path)          # e.g. "/cdr-test/IMG_4663.jpg"
            filename = os.path.basename(path)    # "IMG_4663.jpg"

            if not filename:
                if verbose:
                    print(f"[WARN] No filename in URL path: {url}")
                continue

            ext = os.path.splitext(filename)[1].lstrip(".").lower()

            # 2) Skip non-images
            if ext not in IMAGE_EXTS:
                if verbose:
                    print(f"[SKIP] Not an image ({ext}): {filename}")
                continue

            # 3) Derive blob_name from URL path & container
            # path_no_lead: "cdr-test/IMG_4663.jpg"
            path_no_lead = path.lstrip("/")
            prefix = f"{container}/"
            if path_no_lead.startswith(prefix):
                blob_name = path_no_lead[len(prefix):]   # "IMG_4663.jpg"
            else:
                # Fallback: just use the remaining path
                blob_name = path_no_lead

            if verbose:
                print(f"[INFO] Resolved blob_name: {blob_name}")

            # 4) Local path in SAME directory (e.g. src_files/IMG_4663.jpg)
            dest_path = os.path.join(download_dir, filename)

            if os.path.exists(dest_path) and not overwrite:
                if verbose:
                    print(f"[SKIP] Already exists: {dest_path}")
                downloaded_paths.append(dest_path)
                continue

            # 5) Download the blob
            blob_client = container_client.get_blob_client(blob_name)
            with open(dest_path, "wb") as f:
                f.write(blob_client.download_blob().readall())

            downloaded_paths.append(dest_path)
            if verbose:
                print(f"[OK] Downloaded: {blob_name} -> {dest_path}")

        except Exception as e:
            if verbose:
                print(f"[ERROR] Failed to download from {url}: {e}")

    return downloaded_paths


# Deleting & Recreating Database and Vectorestore

#client = CosmosClient(COSMOS_URL, credential=COSMOS_KEY)

def create_db_and_container():
    ctx = configs.require_runtime()
    CONT_NAME = configs.build_cosmos_cont_name()
    #print("→ Ensuring database...")
    #db = client.create_database_if_not_exists(DB_NAME)
    db = cosmos_client.create_database_if_not_exists(DB_NAME)
    #print("✔ Database ready:", DB_NAME)

    vector_embedding_policy = {
        "vectorEmbeddings": [
            {
                "path": VECTOR_PATH,
                "dataType": "float32",
                "dimensions": EMBED_DIM,
                "distanceFunction": "cosine",
            }
        ]
    }

    indexing_policy = {
        "includedPaths": [{"path": "/*"}],
        "excludedPaths": [{"path": "/\"_etag\"/?"}, {"path": f"{VECTOR_PATH}/*"}],
        "vectorIndexes": [{"path": VECTOR_PATH, "type": "quantizedFlat"}],
    }

    #print("→ Removing old container if exists (to avoid schema conflicts)...")
    try:
        c_old = db.get_container_client(CONT_NAME)
        c_old.read()  # will throw if not found
        db.delete_container(CONT_NAME)
        #print("✔ Old container deleted")
    except exceptions.CosmosResourceNotFoundError:
        #print(" ℹ No old container")
        print("----------------------------------------------------------------------")


    #print("→ Creating container with vector policy...")
    try:
        container = db.create_container(
            id=CONT_NAME,
            partition_key=PartitionKey(path="/id"),
            indexing_policy=indexing_policy,
            vector_embedding_policy=vector_embedding_policy,
            # If your account requires explicit RU: uncomment next line
            # offer_throughput=400,
        )
        #print("✔ Container created:", CONT_NAME)
        return container
    except exceptions.CosmosHttpResponseError as e:
        #print("❌ Failed to create container")
        print("StatusCode:", getattr(e, "status_code", None))
        #print("Message:", getattr(e, "message", str(e)))
        raise

def add_ids_to_chunks(chunks):
    docs = []
    for ch in chunks:
        docs.append(
            LCDocument(
                page_content=ch.page_content,
                metadata={
                    **ch.metadata,
                    "id": str(uuid.uuid4())  # REQUIRED for Cosmos DB
                }
            )
        )
    return docs

def ingest_to_cosmos_parallel(vs, chunks, batch_size=2, max_workers=2):

    def safe_add(doc):
        """Add a single document with retry for CosmosDB 429 throttling."""
        retries = 5
        for attempt in range(retries):
            try:
                return vs.add_documents([doc])
            except HttpResponseError as e:
                if "Request rate is large" in str(e) or e.status_code == 429:
                    wait = (attempt + 1) * 2
                    #print(f"⚠️ 429 Rate Limit → retrying in {wait}s")
                    time.sleep(wait)
                else:
                    #print(f"❌ Unhandled error: {e}")
                    return None
        #print("❌ Failed after retries")
        return None

    # Sequential batches (safe for Cosmos)
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        #print(f"\n🔵 Ingesting batch {i} → {i + len(batch) - 1}")

        # Parallel within each batch
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(safe_add, doc): doc for doc in batch}

            for future in as_completed(future_map):
                doc = future_map[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"!!! Error inserting doc: {e}")
                    print("-----------------------------------------------------------")

def build_vectorstore(embeddings):
    # cosmos_client = CosmosClient(
    #     url=COSMOS_URL,
    #     credential=COSMOS_KEY
    # )

    # keep your existing policy helpers if your constructor requires them
    return AzureCosmosDBNoSqlVectorSearch(
        cosmos_client=cosmos_client,
        embedding=embeddings,
        database_name=DB_NAME,
        container_name=CONT_NAME,

        # if your version requires explicit policies, keep these as you already had:
        vector_embedding_policy={"vectorEmbeddings":[{"path":"/vector","dataType":"float32","dimensions":1536,"distanceFunction":"cosine"}]},
        indexing_policy={"includedPaths":[{"path":"/*"}],
                         "excludedPaths":[{"path":"/\"_etag\"/?"},{"path":"/vector/*"}],
                         "vectorIndexes":[{"path":"/vector","type":"quantizedFlat"}]},
        cosmos_container_properties={"partition_key":"/id"},
        cosmos_database_properties={}, # _db_props()

        # IMPORTANT: pass a dict, not a list
        vector_search_fields={
            "text_field": "text",
            "embedding_field": "vector",
            "metadata_field": "metadata"
        }
    )


# -----------------------
# Builders
# -----------------------
def build_embeddings():
    return AzureOpenAIEmbeddings(
        azure_endpoint=AOAI_ENDPOINT,
        api_key=AOAI_KEY,
        openai_api_version=API_VERSION,
        azure_deployment=EMBED_DEPLOY,
    )

# def load_and_split_pdfs_text(
#     pdf_paths,
#     CHUNK_SIZE,
#     CHUNK_OVERLAP,
#     extracted_texts=None,
#     cad_schematics=False
# ):
#     """
#     EXACT implementation from your notebook.
#     Returns:
#         chunks → list of text Document objects
#         image_page_metadata → list of schematic image metadata
#     """

#     docs = []
#     image_page_metadata = []

#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=CHUNK_SIZE,
#         chunk_overlap=CHUNK_OVERLAP,
#         separators=["\n\n", "\n", ". ", " "],
#         keep_separator=False,
#     )

#     # ----- STEP 1: PDF TEXT EXTRACTION -----
#     for path in pdf_paths:
#         if not str(path).lower().endswith(".pdf"):
#             continue

#         loader = PyPDFLoader(str(path))
#         raw_docs = loader.load()
#         base = os.path.basename(str(path))

#         for d in raw_docs:
#             page = int(d.metadata.get("page", 1))
#             d.metadata["source_file"] = base
#             d.metadata["page"] = page
#             d.metadata["citation"] = f"{base}#page={page}"

#         docs.extend(raw_docs)

#         # ----- STEP 2: CAD/Schematic Image Extraction -----
#         # if cad_schematics:
#         #     try:
#         #         extracted = extract_relevant_pdf_page_images(path)
#         #         image_page_metadata.extend(extracted)
#         #     except Exception as e:
#         #         #print(f"[WARN] selective image extraction failed for {path}: {e}")

#     # ----- STEP 3: External extracted text -----
#     # -------------------------------------------------------------
#     # STEP 2 — Process externally extracted text files (unchanged)
#     # -------------------------------------------------------------
#     if extracted_texts:
#         for item in extracted_texts:
#             if not isinstance(item, dict):
#                 continue

#             if "filename" in item and "text" in item:
#                 filename = item["filename"]
#                 text = item["text"]
#             elif len(item) == 1:
#                 filename, text = next(iter(item.items()))
#             elif "text" in item:
#                 filename = item.get("filename") or "unknown"
#                 text = item["text"]
#             else:
#                 filename = item.get("filename") or "unknown"
#                 text = None
#                 for k, v in item.items():
#                     if isinstance(v, str) and v.strip():
#                         filename = k
#                         text = v
#                         break
#                 if text is None:
#                     text = " ".join(str(v) for v in item.values())

#             metadata = {
#                 "source_file": os.path.basename(str(filename)),
#                 "page": 1,
#                 "citation": os.path.basename(str(filename))
#             }

#             # ORIGINAL WORKING VERSION — KEEP SimpleNamespace
#             docs.append(
#                 SimpleNamespace(
#                     page_content=text or "",
#                     metadata=metadata
#                 )
#             )



#     # ----- STEP 4: Chunking -----
#     chunks = splitter.split_documents(docs)

#     return chunks
#     # return chunks, image_page_metadata



# def load_and_split_pdfs_text(pdf_paths, extracted_texts=None):
#     """
#     pdf_paths: iterable of file paths (existing behavior — only PDFs processed)
#     extracted_texts: optional list of dicts. Supported shapes:
#         - { "filename.ext": "text..." }
#         - { "filename": "...", "text": "..." }
#         - mixed list containing either form
#     Returns: list of chunks (output of splitter.split_documents)
#     """
#     #print('START OF CHUNKING')
#     docs = []
#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=CHUNK_SIZE,
#         chunk_overlap=CHUNK_OVERLAP,
#         separators=["\n\n", "\n", ". ", " "],
#         keep_separator=False,
#     )

#     # --- existing PDF flow (unchanged) ---
#     for path in pdf_paths:
#         if not str(path).lower().endswith(".pdf"):
#             continue
#         loader = PyPDFLoader(str(path))
#         raw_docs = loader.load()
#         base = os.path.basename(str(path))
#         for d in raw_docs:
#             page = int(d.metadata.get("page", 1))
#             d.metadata["source_file"] = base
#             d.metadata["page"] = page
#             d.metadata["citation"] = f"{base}#page={page}"
#         docs.extend(raw_docs)

#     # --- new: accept extracted_texts in multiple sensible shapes ---
#     if extracted_texts:
#         for item in extracted_texts:
#             if not isinstance(item, dict):
#                 continue

#             # Case A: explicit keys 'filename' and 'text'
#             if "filename" in item and "text" in item:
#                 filename = item["filename"]
#                 text = item["text"]
#             # Case B: single-key mapping { "actual_filename": "text..." }
#             elif len(item) == 1:
#                 filename, text = next(iter(item.items()))
#             # Case C: has 'text' but no filename key
#             elif "text" in item:
#                 filename = item.get("filename") or item.get("name") or "unknown"
#                 text = item["text"]
#             else:
#                 # Fallback: pick first string value
#                 filename = None
#                 text = None
#                 for k, v in item.items():
#                     if isinstance(v, str) and v.strip():
#                         filename = k
#                         text = v
#                         break
#                 if text is None:
#                     filename = item.get("filename") or "unknown"
#                     text = " ".join(str(v) for v in item.values())

#             base = os.path.basename(str(filename))
#             metadata = {
#                 "source_file": base,
#                 "page": 1,
#                 "citation": f"{base}"
#             }

#             # Create a simple Document-like object expected by splitter
#             # splitter expects attributes like .page_content and .metadata
#             doc = SimpleNamespace(page_content=text or "", metadata=metadata)

#             docs.append(doc)
#     #print('END OF CHUNKING FUNCTION')
#     # finally split all collected documents (pdf chunks + plain-text docs)
#     return splitter.split_documents(docs)


from types import SimpleNamespace
from collections import defaultdict
import os
from types import SimpleNamespace
import os

def load_and_split_pdfs_text(pdf_paths, extracted_texts=None):
    """
    pdf_paths: iterable of file paths (existing behavior — only PDFs processed)
    extracted_texts: optional list of dicts. Supported shapes:
        - { "filename.ext": "text..." }
        - { "filename": "...", "text": "..." }
        - mixed list containing either form
    Returns: list of chunks (output of splitter.split_documents)
    """
    docs = []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
        keep_separator=False,
    )

    # --- existing PDF flow (unchanged) ---
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

    # --- new: accept extracted_texts in multiple sensible shapes ---
    if extracted_texts:
        for item in extracted_texts:
            if not isinstance(item, dict):
                continue

            # Case A: explicit keys 'filename' and 'text'
            if "filename" in item and "text" in item:
                filename = item["filename"]
                text = item["text"]
            # Case B: single-key mapping { "actual_filename": "text..." }
            elif len(item) == 1:
                filename, text = next(iter(item.items()))
            # Case C: has 'text' but no filename key
            elif "text" in item:
                filename = item.get("filename") or item.get("name") or "unknown"
                text = item["text"]
            else:
                # Fallback: pick first string value
                filename = None
                text = None
                for k, v in item.items():
                    if isinstance(v, str) and v.strip():
                        filename = k
                        text = v
                        break
                if text is None:
                    filename = item.get("filename") or "unknown"
                    text = " ".join(str(v) for v in item.values())

            base = os.path.basename(str(filename))
            #NEW: page support (default 1)
            page = item.get("page", 1)
            try:
                page = int(page)
            except Exception:
                page = 1

            is_pdf = base.lower().endswith(".pdf")
            metadata = {
            "source_file": base,
            "page": page,
            "citation": f"{base}#page={page}" if is_pdf else f"{base}" # ✅ match PDF style
            }
            doc = SimpleNamespace(page_content=text or "", metadata=metadata)
            docs.append(doc)
    return splitter.split_documents(docs)

# def add_batch(batch, idx_start, vs):
#     # helpful for logging
#     print(f"Ingesting batch starting at {idx_start} (size={len(batch)})")
#     vs.add_documents(batch)
#     return idx_start, len(batch)

# def ingest_chunks(vs, chunks, max_workers=5, batch_size=10):
#     futures = []
#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         for i in range(0, len(chunks), batch_size):
#             batch = chunks[i:i + batch_size]
#             futures.append(executor.submit(add_batch, batch, i, vs))

#         for f in as_completed(futures):
#             idx_start, size = f.result()
#             print(f"✅ Finished batch starting at {idx_start}, size={size}")

def _compute_wait(attempt: int, cap: float = 30.0) -> float:
    return min((2 ** attempt) + random.random(), cap)

def add_batch(batch, idx_start, vs, max_retries=7):
    # logger.info(f"Ingesting batch starting at {idx_start} (size={len(batch)})")
    last_err = None
    
    for attempt in range(max_retries):
        try:
            with _EMBED_SEMAPHORE:
                with _VS_LOCK:  # Add if vs is not thread-safe
                    vs.add_documents(batch)
            return idx_start, len(batch)
        
        except RateLimitError as e:
            last_err = e
            wait = _compute_wait(attempt)
            # logger.warning(f"OpenAI rate limited at batch {idx_start}, retrying in {wait:.1f}s")
            time.sleep(wait)
        
        except CosmosHttpResponseError as e:
            last_err = e
            retry_after_ms = e.headers.get("x-ms-retry-after-ms")
            wait = min(float(retry_after_ms) / 1000.0, 60.0) if retry_after_ms else _compute_wait(attempt, 60.0)
            # logger.warning(f"CosmosHttpResponseError (status={e.status_code}) at batch {idx_start}, retrying in {wait:.1f}s")
            time.sleep(wait)
        
        except (ServiceResponseError, ServiceRequestError, TimeoutError, ConnectionError, OSError, CosmosResourceNotFoundError) as e:
            last_err = e
            wait = _compute_wait(attempt, 60.0)
            # logger.warning(f"Network error at batch {idx_start}: {type(e).__name__}. Retrying in {wait:.1f}s")
            time.sleep(wait)
        
        except ValueError as e:
            if any(kw in str(e).lower() for kw in ["token", "length", "size"]):
                # logger.error(f"Skipping batch {idx_start} due to validation error: {e}")
                return idx_start, 0  # Skip this batch
            raise
    
    raise RuntimeError(f"Failed batch at {idx_start} after {max_retries} retries. Last error: {last_err}")

def ingest_chunks(vs, chunks, max_workers=2, batch_size=2, fail_threshold=0.3):
    futures = []
    failed = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            futures.append(executor.submit(add_batch, batch, i, vs))
        
        for f in as_completed(futures):
            try:
                idx_start, size = f.result()
                # logger.info(f"✅ Finished batch starting at {idx_start}, size={size}")
            except Exception as e:
                # logger.error(f"❌ Batch failed: {e}")
                failed.append(e)
    
    if failed and len(failed) / len(futures) > fail_threshold:
        raise RuntimeError(f"{len(failed)}/{len(futures)} batches failed (>{fail_threshold*100}% threshold)")


from azure.storage.blob import BlobServiceClient

def delete_folder_if_exists(connection_string: str, container: str, folder_name: str) -> int:
    """
    Deletes a virtual folder (prefix) in an Azure Blob container.
    Example folder_name: "device_images"
    Deletes all blobs under "device_images/".
    Returns: number of blobs deleted (0 if folder doesn't exist).
    """
    
    configs.require_runtime()
    bsc = BlobServiceClient.from_connection_string(connection_string)
    cc = bsc.get_container_client(container)

    prefix = folder_name.strip("/\\") + "/"

    deleted = 0
    for blob in cc.list_blobs(name_starts_with=prefix):
        cc.delete_blob(blob.name, delete_snapshots="include")
        deleted += 1

    return deleted




import json
import re
from pathlib import Path
from urllib.parse import urlparse
from azure.storage.blob import BlobServiceClient

# ============================================================
# IMAGE ANALYSIS (UNCHANGED)
# ============================================================

def analyze_image(url: str) -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a visual inspector helping to prepare a CB test report.\n"
                "Decide if the image is the main physical product/device.\n"
                "If yes, generate a short caption like 'Front view', 'Back view'.\n"
                "Return ONLY JSON:\n"
                "{ \"is_device\": true|false, \"caption\": string|null }"
            ),
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Is this the main device?"},
                {"type": "image_url", "image_url": {"url": url}},
            ],
        },
    ]

    from utility.cdr_report.CDR_Pipelines.configs import llm

    resp = llm.invoke(messages)
    text = resp.content if isinstance(resp.content, str) else resp.content[0].text

    try:
        data = json.loads(text)
    except Exception:
        data = {"is_device": False, "caption": None}

    data["is_device"] = bool(data.get("is_device"))
    caption = data.get("caption")
    data["caption"] = caption if isinstance(caption, str) and caption.strip() else None
    return data


# ============================================================
# STEP 1: GET IMAGE URLs FROM CONTAINER
# ============================================================

def get_image_urls_from_container_sas() -> list[str]:
    """
    Lists image blobs from the configured container
    and returns FULL blob URLs (required by analyze_image).
    """
    import utility.cdr_report.CDR_Pipelines.configs as configs
    configs.require_runtime()
    project_id = configs._runtime.project_id
    
    blob_service = BlobServiceClient.from_connection_string(
        configs.AZURE_BLOB_CONNECTION_STRING
    )
    container_client = blob_service.get_container_client(
        configs.BLOB_CONTAINER_NAME
    )

    image_urls = []
    prefix = f"Documents/{project_id}/source_documents/"
    blobs = list(container_client.list_blobs(name_starts_with=prefix))

    #print(f"Blobs found in container: {len(blobs)}")

    for blob in blobs:
        name = blob.name.lower()
        if name.endswith((".jpg", ".jpeg", ".png", ".webp")):
            blob_client = container_client.get_blob_client(blob.name)
            image_urls.append(blob_client.url)

    #print(f"Image URLs collected: {len(image_urls)}")
    return image_urls


# ============================================================
# STEP 2: MOVE DEVICE IMAGES
# ============================================================

def move_device_images_in_blob(
    image_urls: list[str],
    connection_string: str,
    container_name: str,
) -> list[str]:
    
    configs.require_runtime()
    project_id = configs._runtime.project_id
    device_prefix = f"Documents/{project_id}/source_documents/device_images/"


    def slugify(text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^a-z0-9]+", "-", text)
        return text.strip("-")

    def blob_name_from_url(url: str, container: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")

        if not path.startswith(container + "/"):
            raise ValueError(f"URL not in container '{container}': {url}")

        return path[len(container) + 1:]

    blob_service = BlobServiceClient.from_connection_string(
        connection_string
    )
    container_client = blob_service.get_container_client(
        container_name
    )

    moved_blobs = []
    photo_idx = 1

    for url in image_urls:
        info = analyze_image(url)
        if not info.get("is_device"):
            continue

        caption = info.get("caption") or "device-view"
        slug = f"{slugify(caption)}"

        try:
            src_blob_name = blob_name_from_url(url, container_name)
        except ValueError as e:
            #print(f"⚠ {e}")
            continue

        src_blob_client = container_client.get_blob_client(src_blob_name)
        if not src_blob_client.exists():
            #print(f"❌ Source blob missing: {src_blob_name}")
            continue

        ext = Path(src_blob_name).suffix or ".png"
        dest_blob_name = f"{device_prefix}{slug}{ext}"
        dest_blob_client = container_client.get_blob_client(dest_blob_name)

        ctr = 1
        while dest_blob_client.exists():
            dest_blob_name = f"{device_prefix}{slug}-{ctr}{ext}"
            dest_blob_client = container_client.get_blob_client(dest_blob_name)
            ctr += 1

        dest_blob_client.start_copy_from_url(src_blob_client.url)
        #src_blob_client.delete_blob()

        moved_blobs.append(dest_blob_name)
        photo_idx += 1

        #print(f"✅ Moved device image → {dest_blob_name}")

    return moved_blobs


import json
from urllib.parse import urlparse, quote

def make_blob_url(container_sas_url: str, filename: str) -> str:
    configs.require_runtime()
    u = urlparse(container_sas_url)
    container_base = f"{u.scheme}://{u.netloc}{u.path}".rstrip("/")
    sas_query = u.query
    encoded = quote(filename, safe="")
    return f"{container_base}/Documents/{configs._runtime.project_id}/source_documents/{encoded}?{sas_query}" if sas_query else f"{container_base}/{encoded}"


def add_urls_sheet_1_and_6(payload: dict, container_sas_url: str):
    """
    Returns:
      updated_payload (dict): same object updated in-place (also returned)
      updated_count (int): number of text_support items updated
    Updates ONLY:
      Sheets where sheet_no in (1, 6)
    """
    configs.require_runtime()
    updated = 0

    def walk(node):
        nonlocal updated
        if isinstance(node, dict):
            ts = node.get("text_support")
            if isinstance(ts, list):
                for item in ts:
                    if (
                        isinstance(item, dict)
                        and item.get("filename")
                        and not item.get("url")  # only fill missing/empty url
                    ):
                        item["url"] = make_blob_url(container_sas_url, item["filename"])
                        updated += 1

            for v in node.values():
                walk(v)

        elif isinstance(node, list):
            for it in node:
                walk(it)

    for sheet in payload.get("Sheets", []):
        if sheet.get("sheet_no") in (1, 6):  # ✅ only 1 and 6
            walk(sheet)

    return payload, updated

import time
import random
from typing import Optional

def _get_status_code_from_exception(e: Exception) -> Optional[int]:
    """
    Try to extract HTTP status code from different exception shapes:
    - openai.* exceptions (often have .status_code)
    - httpx.HTTPStatusError (has .response.status_code)
    - generic wrappers
    """
    # openai exceptions sometimes expose status_code directly
    code = getattr(e, "status_code", None)
    if isinstance(code, int):
        return code

    # httpx style
    resp = getattr(e, "response", None)
    if resp is not None:
        sc = getattr(resp, "status_code", None)
        if isinstance(sc, int):
            return sc

    # some exceptions wrap another exception
    inner = getattr(e, "__cause__", None) or getattr(e, "__context__", None)
    if inner and inner is not e:
        return _get_status_code_from_exception(inner)

    return None


def is_rate_limit_error(e: Exception) -> bool:
    """
    Return True if this looks like a rate limit / quota / 429 error.
    We check both status codes and message text because LangChain/OpenAI/Azure
    may wrap the error differently.
    """
    status_code = _get_status_code_from_exception(e)
    if status_code == 429:
        return True

    msg = (str(e) or "").lower()
    # common Azure/OpenAI rate limit messages
    keywords = [
        "rate limit",
        "429",
        "too many requests",
        "quota",
        "exceeded",
        "throttl",
        "retry after",
    ]
    return any(k in msg for k in keywords)


def invoke_with_rate_limit_retry(
    llm,
    messages,
    *,
    retries: int = 6,
    wait_seconds: float = 5.0,
    jitter: float = 0.5,   # small randomness helps when many threads retry together
):
    """
    Calls llm.invoke(messages) with retry ONLY for rate-limit errors.
    Waits wait_seconds (plus small jitter) before retrying.
    """
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return llm.invoke(messages)
        except Exception as e:
            last_err = e

            if not is_rate_limit_error(e):
                # Not a rate limit -> fail fast
                raise

            # Rate limit -> wait and retry
            sleep_for = wait_seconds + random.uniform(0, jitter)
            #print(f"[RATE_LIMIT] attempt {attempt}/{retries} -> sleeping {sleep_for:.2f}s then retrying...")
            time.sleep(sleep_for)

    # exhausted
    raise last_err



def delete_cosmos_container(
    endpoint: str,
    key: str,
    database_name: str,
    container_name: str
):
    """
    Deletes a Cosmos DB container.
    """

    client = CosmosClient(endpoint, credential=key)

    try:
        database = client.get_database_client(database_name)
        database.delete_container(container_name)
        
        #print("\n===============================================")
        #print(f" DELETING THE VECTOR COSMOS DB Container '{container_name}'")
        #print("===============================================")

        #print(f"Container '{container_name}' deleted successfully.")


    except ResourceNotFoundError:
        print(f"Container '{container_name}' or database '{database_name}' not found.")

    except Exception as e:
        raise RuntimeError(f"Failed to delete container: {e}")