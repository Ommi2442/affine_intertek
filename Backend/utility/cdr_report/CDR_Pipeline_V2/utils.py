# utils.py

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
from azure.storage.blob import BlobClient
from azure.core.exceptions import ResourceNotFoundError, AzureError
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

from configs import (
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

def get_blob_urls(conn_str: str, container: str, sas_token: str | None = None):
    """
    Returns a list of full blob URLs for all blobs in the given container.

    - Uses the connection string + container name to list blobs.
    - Builds URLs as:
        https://<account>.blob.core.windows.net/<container>/<blob-name>?<sas>
    - If sas_token is None, returns plain URLs without SAS.
    """

    # --- inner helper to repair malformed URLs (defensive) ---
    def _fix_sas_blob_url(url: str) -> str:
        """
        Converts malformed
          https://.../container?sv=...&sig=.../blobname
        into
          https://.../container/blobname?sv=...&sig=...
        If the URL is already OK, returns it unchanged.
        """
        qpos = url.find("?")
        slashpos = url.rfind("/")

        # Only "fix" if ? comes before last /
        if qpos != -1 and qpos < slashpos:
            prefix = url[:slashpos]       # up to before blob name
            blob_name = url[slashpos+1:]  # after last /

            base, qs = prefix.split("?", 1)
            return f"{base}/{blob_name}?{qs}"

        # already OK or no query → return as-is
        return url

    # --- list blobs and build URLs ---
    service_client = BlobServiceClient.from_connection_string(conn_str)
    container_client = service_client.get_container_client(container)

    container_url = container_client.url
    print(f"Container URL: {container_url}")

    # normalize SAS once
    qs = ""
    if sas_token:
        qs = "?" + sas_token.lstrip("?")

    blob_urls: list[str] = []

    for blob in container_client.list_blobs():
        # raw correct URL we intend to use
        raw_url = f"{container_url}/{quote(blob.name)}{qs}"
        # run through fixer (no-op for correct URLs, fixes any bad ones)
        fixed_url = _fix_sas_blob_url(raw_url)
        blob_urls.append(fixed_url)

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
    download_dir: str = "src_files",   # ✅ same folder as your other docs
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
    print("→ Ensuring database...")
    #db = client.create_database_if_not_exists(DB_NAME)
    db = cosmos_client.create_database_if_not_exists(DB_NAME)
    print("✔ Database ready:", DB_NAME)

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

    print("→ Removing old container if exists (to avoid schema conflicts)...")
    try:
        c_old = db.get_container_client(CONT_NAME)
        c_old.read()  # will throw if not found
        db.delete_container(CONT_NAME)
        print("✔ Old container deleted")
    except exceptions.CosmosResourceNotFoundError:
        print(" ℹ No old container")

    print("→ Creating container with vector policy...")
    try:
        container = db.create_container(
            id=CONT_NAME,
            partition_key=PartitionKey(path="/id"),
            indexing_policy=indexing_policy,
            vector_embedding_policy=vector_embedding_policy,
            # If your account requires explicit RU: uncomment next line
            # offer_throughput=400,
        )
        print("✔ Container created:", CONT_NAME)
        return container
    except exceptions.CosmosHttpResponseError as e:
        print("❌ Failed to create container")
        print("StatusCode:", getattr(e, "status_code", None))
        print("Message:", getattr(e, "message", str(e)))
        raise


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


def load_and_split_pdfs_text(pdf_paths, extracted_texts=None):
    """
    pdf_paths: iterable of file paths (existing behavior — only PDFs processed)
    extracted_texts: optional list of dicts. Supported shapes:
        - { "filename.ext": "text..." }
        - { "filename": "...", "text": "..." }
        - mixed list containing either form
    Returns: list of chunks (output of splitter.split_documents)
    """
    print('START OF CHUNKING')
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
            metadata = {
                "source_file": base,
                "page": 1,
                "citation": f"{base}"
            }

            # Create a simple Document-like object expected by splitter
            # splitter expects attributes like .page_content and .metadata
            doc = SimpleNamespace(page_content=text or "", metadata=metadata)

            docs.append(doc)
    print('END OF CHUNKING FUNCTION')
    # finally split all collected documents (pdf chunks + plain-text docs)
    return splitter.split_documents(docs)

def add_batch(batch, idx_start, vs):
    # helpful for logging
    print(f"Ingesting batch starting at {idx_start} (size={len(batch)})")
    vs.add_documents(batch)
    return idx_start, len(batch)

def ingest_chunks(vs, chunks, max_workers=5, batch_size=10):
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            futures.append(executor.submit(add_batch, batch, i, vs))

        for f in as_completed(futures):
            idx_start, size = f.result()
            print(f"✅ Finished batch starting at {idx_start}, size={size}")







