import re
import docx2pdf
import tempfile
import shutil
import requests
from urllib.parse import urlparse, unquote
from email import policy
from email.parser import BytesParser
import extract_msg
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
from docx import Document as WordDocument
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
import os
import subprocess
import shutil
import platform



pd.set_option('display.max_colwidth', None)  # Don't truncate cell text
pd.set_option('display.max_rows', None)      # Show all rows (optional)
pd.set_option('display.max_columns', None) 


IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "svg"}

def set_checkbox_checked(docx_path, out_path, checkbox_index=0):
    doc = WordDocument(docx_path)

    count = 0
    for field in doc._element.body.iter():
        if field.tag == qn("w:fldSimple"):
            continue
        if field.tag == qn("w:fldChar") and field.get(qn("w:fldCharType")) == "begin":
            # potential checkbox start
            parent = field.getparent()
            ffData = parent.find(".//w:ffData", namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"})
            if ffData is not None:
                checkBox = ffData.find(".//w:checkBox", namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"})
                if checkBox is not None:
                    if count == checkbox_index:
                        default = checkBox.find(".//w:default", namespaces={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"})
                        if default is None:
                            default = OxmlElement("w:default")
                            checkBox.append(default)
                        default.set(qn("w:val"), "1")  # ✔ check
                    count += 1

    doc.save(out_path)


### If chunks ingested don't run
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


### If chunks ingested don't run
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

### If chunks ingested don't run
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

### If chunks ingested don't run
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

### If chunks ingested don't run
def _guess_ext_from_url(url):
    path = urlparse(url).path
    path = unquote(path)
    _, ext = os.path.splitext(path)
    if ext:
        return ext.lstrip(".").lower()
    return None

### If chunks ingested don't run
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


#### For Windows
# def convert_doc_to_pdf(input_path, output_path=None):
#     """
#     Convert .doc or .docx to PDF using LibreOffice.
#     Works on Windows + Linux.
#     """

#     if not os.path.isfile(input_path):
#         raise FileNotFoundError(f"Input file not found: {input_path}")

#     # Determine output path
#     if output_path is None:
#         base, _ = os.path.splitext(input_path)
#         output_path = base + ".pdf"

#     out_dir = os.path.dirname(os.path.abspath(output_path))

#     # Detect libreoffice binary
#     system = platform.system().lower()

#     if system == "windows":
#         # Try typical install locations
#         possible_paths = [
#             r"C:\Program Files\LibreOffice\program\soffice.exe",
#             r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
#         ]
#         soffice = next((p for p in possible_paths if os.path.isfile(p)), None)

#         if soffice is None:
#             soffice = shutil.which("soffice")  # last fallback

#         if soffice is None:
#             raise RuntimeError("LibreOffice not found. Install from https://www.libreoffice.org/")
#     else:
#         # Linux/macOS
#         soffice = shutil.which("libreoffice") or shutil.which("soffice")

#         if soffice is None:
#             raise RuntimeError("LibreOffice not installed. Install using your package manager.")

#     cmd = [
#         soffice,
#         "--headless",
#         "--convert-to", "pdf",
#         "--outdir", out_dir,
#         input_path
#     ]

#     try:
#         subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#     except subprocess.CalledProcessError as e:
#         raise RuntimeError(f"PDF conversion failed: {e.stderr.decode()}")

#     return output_path



#### For Linux ######
def convert_doc_to_pdf_linux(doc_path: str, pdf_path: str):
    system = platform.system().lower()

    if system == "linux":
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                os.path.dirname(pdf_path),
                doc_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    raise RuntimeError(f"Unsupported OS for DOC conversion: {system}")
 


##### For Windows
# def pdf_convert(file1,file2):
#     """file1 is docx and file2 is pdf""" 
#     return docx2pdf.convert(file1,file2)


#### For Linux ######
def convert_docx_to_pdf_linux(docx_path: str, pdf_path: str):
    system = platform.system().lower()

    if system == "linux":
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                os.path.dirname(pdf_path),
                docx_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    raise RuntimeError(f"Unsupported OS for DOCX conversion: {system}")




### If chunks ingested don't run
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

### If chunks ingested don't run
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


# def create_db_and_container(client,DB_NAME,VECTOR_PATH,EMBED_DIM,CONT_NAME):
#     print("→ Ensuring database...")
#     db = client.create_database_if_not_exists(DB_NAME)
#     print("✔ Database ready:", DB_NAME)

#     vector_embedding_policy = {
#         "vectorEmbeddings": [
#             {
#                 "path": VECTOR_PATH,
#                 "dataType": "float32",
#                 "dimensions": EMBED_DIM,
#                 "distanceFunction": "cosine",
#             }
#         ]
#     }

#     indexing_policy = {
#         "includedPaths": [{"path": "/*"}],
#         "excludedPaths": [{"path": "/\"_etag\"/?"}, {"path": f"{VECTOR_PATH}/*"}],
#         "vectorIndexes": [{"path": VECTOR_PATH, "type": "quantizedFlat"}],
#     }

#     print("→ Removing old container if exists (to avoid schema conflicts)...")
#     try:
#         c_old = db.get_container_client(CONT_NAME)
#         c_old.read()  # will throw if not found
#         db.delete_container(CONT_NAME)
#         print("✔ Old container deleted")
#     except exceptions.CosmosResourceNotFoundError:
#         print(" ℹ No old container")

#     print("→ Creating container with vector policy...")
#     try:
#         container = db.create_container(
#             id=CONT_NAME,
#             partition_key=PartitionKey(path="/id"),
#             indexing_policy=indexing_policy,
#             vector_embedding_policy=vector_embedding_policy,
#             # If your account requires explicit RU: uncomment next line
#             # offer_throughput=400,
#         )
#         print("✔ Container created:", CONT_NAME)
#         return container
#     except exceptions.CosmosHttpResponseError as e:
#         print("❌ Failed to create container")
#         print("StatusCode:", getattr(e, "status_code", None))
#         print("Message:", getattr(e, "message", str(e)))
#         raise



def ensure_cosmos_database(client, DB_NAME):
    """
    Ensures Cosmos DB database exists.
    - If exists → do nothing
    - If missing → create it
    """

    print("→ Ensuring database...")

    try:
        db = client.get_database_client(DB_NAME)
        db.read()
        print("✔ Database exists:", DB_NAME)
        return db

    except exceptions.CosmosResourceNotFoundError:
        db = client.create_database(DB_NAME)
        print("✔ Database created:", DB_NAME)
        return db



# Builders
# -----------------------
def build_embeddings(AOAI_ENDPOINT,AOAI_KEY,API_VERSION,EMBED_DEPLOY):
    return AzureOpenAIEmbeddings(
        azure_endpoint=AOAI_ENDPOINT,
        api_key=AOAI_KEY,
        openai_api_version=API_VERSION,
        azure_deployment=EMBED_DEPLOY,
    )


def add_ids_to_chunks(chunks):
    docs = []
    for ch in chunks:
        docs.append(
            Document(
                page_content=ch.page_content,
                metadata={
                    **ch.metadata,
                    "id": str(uuid.uuid4())  # REQUIRED for Cosmos DB
                }
            )
        )
    return docs

def process_blob_urls_2(blob_urls, conn_str, container,
                      download_dir=None, keep_files=False, verbose=True):
    """
    Robust process_blob_urls:
      - expects list of full blob URLs (SAS tokens OK)
      - downloads docx, txt, eml, msg, xls, xlsx, pdf via download_blob_file (via safe_download_blob_file)
      - converts docx -> pdf via pdf_convert then (previously extracted text; now we only record converted pdf path)
      - does not download images; returns their URLs in image_urls
      - returns (extracted_texts, image_urls, downloaded_pdf_paths, converted_pdf_paths)
        extracted_texts: list of dicts { 'filename': ..., 'text': ..., optional 'pages': [...] }
    """
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
                # basename might be '/container/path/file.ext' -> take last part
                base = os.path.basename(path)
                ext = os.path.splitext(base)[1].lstrip(".").lower() if base else ""

                # blob_name must be container-relative
                blob_name = _blob_name_from_url(url, container)
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

                # Download using safe_download_blob_file (which uses BlobClient and checks existence)
                ok, err = safe_download_blob_file(conn_str, container, blob_name, local_path)
                if not ok:
                    if verbose:
                        print(f"[WARN] Failed to download '{blob_name}': {err}")
                    extracted_texts.append({"filename": base_name, "text": ""})
                    continue

                # If extension missing, try to infer from downloaded file name
                if not ext:
                    ext = os.path.splitext(local_path)[1].lstrip(".").lower()

                ext = (ext or "").lower()

                # DOCX -> convert to pdf then record pdf path (do NOT extract text)
                if ext == "docx":
                    pdf_path = os.path.splitext(local_path)[0] + ".pdf"
                    try:
                        system = platform.system().lower()
                        if system == "windows":
                            import pythoncom
                            from docx2pdf import convert
                            pythoncom.CoInitialize()
                            try:
                                convert(local_path, pdf_path)
                            finally:
                                pythoncom.CoUninitialize()
                        else:
                            convert_docx_to_pdf_linux(local_path, pdf_path)

                        converted_pdf_paths.append(pdf_path)
                        if verbose:
                            print(f"[INFO] Converted DOCX to PDF: {local_path} -> {pdf_path}")

                    except Exception as e:
                        if verbose:
                            print(f"[WARN] docx->pdf conversion failed for {base_name}: {e}")

                    continue

                # 🆕 DOC → convert to pdf (using your working helper) (windows)
                # if ext == "doc":
                #     try:
                #         pdf_path = convert_doc_to_pdf(local_path)  # your working function
                #         converted_pdf_paths.append(pdf_path)
                #         if verbose:
                #             print(f"[INFO] Converted DOC to PDF: {local_path} -> {pdf_path}")
                #     except Exception as e:
                #         if verbose:
                #             print(f"[WARN] .doc conversion failed for {base_name}: {e}")
                #     continue

                if ext == "doc":
                    pdf_path = os.path.splitext(local_path)[0] + ".pdf"
                    try:
                        convert_doc_to_pdf_linux(local_path, pdf_path)
                        converted_pdf_paths.append(pdf_path)
                        if verbose:
                            print(f"[INFO] Converted DOC to PDF: {local_path} -> {pdf_path}")
                    except Exception as e:
                        if verbose:
                            print(f"[WARN] .doc conversion failed for {base_name}: {e}")
                    continue
 
 


                # PDF -> record downloaded path (do NOT extract text)
                if ext == "pdf":
                    downloaded_pdf_paths.append(local_path)
                    if verbose:
                        print(f"[INFO] Downloaded PDF recorded: {local_path}")
                    # do NOT extract text for pdf as per request
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
                # Per-file catch: keep processing others
                if verbose:
                    print(f"[ERROR] Unexpected error for url {url}: {e}")
                extracted_texts.append({"filename": os.path.basename(url), "text": ""})

        # return the original outputs plus lists of pdf paths
        return extracted_texts, image_urls, downloaded_pdf_paths, converted_pdf_paths

    finally:
        if tempdir and not keep_files:
            try:
                shutil.rmtree(tempdir)
            except Exception:
                pass

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
                    print(f"⚠️ 429 Rate Limit → retrying in {wait}s")
                    time.sleep(wait)
                else:
                    print(f"❌ Unhandled error: {e}")
                    return None
        print("❌ Failed after retries")
        return None

    # Sequential batches (safe for Cosmos)
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        print(f"\n🔵 Ingesting batch {i} → {i + len(batch) - 1}")

        # Parallel within each batch
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(safe_add, doc): doc for doc in batch}

            for future in as_completed(future_map):
                doc = future_map[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"❌ Error inserting doc: {e}")