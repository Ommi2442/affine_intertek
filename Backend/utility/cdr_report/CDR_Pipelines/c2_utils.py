# utils.py
import os
import re
from urllib.parse import quote, urlparse
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, PartitionKey
from openai import AzureOpenAI
from docx import Document
from pypdf import PdfReader

import utility.cdr_report.CDR_Pipelines.configs as configs

# ===================== CLIENTS =====================
def get_openai_client():
    return AzureOpenAI(
        api_key=configs.AZURE_OPENAI_KEY,
        azure_endpoint=configs.AZURE_OPENAI_ENDPOINT,
        api_version=configs.AZURE_OPENAI_API_VERSION
    )

def get_cosmos_container():
    client = CosmosClient(configs.COSMOS_ENDPOINT, configs.COSMOS_KEY)
    db = client.get_database_client(configs.COSMOS_DB_NAME)
    return db.create_container_if_not_exists(
        id=configs.COSMOS_CONTAINER_NAME,
        partition_key=PartitionKey(path=configs.PARTITION_KEY)
    )

# ===================== TOKEN TRACKING =====================
TOTAL_TOKENS = {
    "prompt": 0,
    "completion": 0,
    "total": 0
}
_token_lock = Lock()

def track_usage(resp):
    if hasattr(resp, "usage") and resp.usage:
        with _token_lock:
            TOTAL_TOKENS["prompt"] += resp.usage.prompt_tokens
            TOTAL_TOKENS["completion"] += resp.usage.completion_tokens
            TOTAL_TOKENS["total"] += resp.usage.total_tokens

# ===================== BLOB & FILE UTILS =====================
def get_image_urls_from_container_sas():
    configs.require_runtime()
    project_id = configs.runtime.project_id

    prefix = f"Documents/{project_id}/source_documents/device_images/"

    blob_service = BlobServiceClient.from_connection_string(
        configs.AZURE_BLOB_CONNECTION_STRING
    )
    container_client = blob_service.get_container_client(
        configs.BLOB_CONTAINER_NAME
    )

    blob_names = sorted([
        blob.name
        for blob in container_client.list_blobs(name_starts_with=device_prefix)
        if blob.name.lower().endswith((".jpg", ".jpeg", ".png"))
    ])

    
    print("Blobs found in container:", len(blob_names))
    if not blob_names:
        return []

    base, sas = configs.AZURE_BLOB_CONTAINER_SAS_URL.split("?", 1)
    base = base.rstrip("/")
    
    image_urls = [f"{base}/{quote(blob_name)}?{sas}" for blob_name in blob_names]
    print("Image URLs constructed:", len(image_urls))
    return image_urls


# from azure.storage.blob import BlobServiceClient
from urllib.parse import quote

def find_user_guide_blob():
    configs.require_runtime()
    project_id = configs.runtime.project_id

    prefix = f"Documents/{project_id}/"

    blob_service = BlobServiceClient.from_connection_string(
        configs.AZURE_BLOB_CONNECTION_STRING
    )
    container_client = blob_service.get_container_client(
        configs.BLOB_CONTAINER_NAME
    )

    all_blobs = [
        blob.name
        for blob in container_client.list_blobs(name_starts_with=prefix)
    ]


    if not all_blobs:
        print("❌ Container is empty.")
        return None, None

    guide_keywords = ["user", "guide", "manual", "operation", "instruction"]
    candidates = []

    for name in all_blobs:
        name_l = name.lower()
        if not name_l.endswith((".pdf", ".docx")):
            continue
        if any(k in name_l for k in guide_keywords):
            candidates.append(name)

    if not candidates:
        print("❌ No guide/manual detected.")
        return None, None

    candidates.sort(key=len)
    blob_name = candidates[0]

    # ✅ extract account name safely from SDK
    account_name = blob_service.account_name

    # ✅ normalize SAS
    sas = configs.AZURE_BLOB_CONTAINER_SAS_URL
    if sas and not sas.startswith("?"):
        sas = "?" + sas

    blob_url = (
        f"https://{account_name}.blob.core.windows.net/"
        f"{configs.BLOB_CONTAINER_NAME}/"
        f"{quote(blob_name)}"
    )

    print("✔ Selected user guide:", blob_name)
    return blob_name, blob_url

 

def build_blob_sas_url(blob_name: str) -> str:
    base, sas = configs.AZURE_BLOB_CONTAINER_SAS_URL.split("?", 1)
    base = base.rstrip("/")
    return f"{base}/{quote(blob_name)}?{sas}"

def download_blob(blob_name: str) -> str:
    os.makedirs(configs.DOWNLOAD_DIR, exist_ok=True)
    local_path = os.path.join(configs.DOWNLOAD_DIR, os.path.basename(blob_name))

    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        return local_path

    blob_service = BlobServiceClient.from_connection_string(configs.AZURE_BLOB_CONNECTION_STRING)
    blob_client = blob_service.get_blob_client(container=configs.BLOB_CONTAINER_NAME, blob=blob_name)
    data = blob_client.download_blob().readall()

    if not data:
        print(f"Downloaded blob is empty: {blob_name}")
        return

    with open(local_path, "wb") as f:
        f.write(data)
    return local_path

def extract_text_from_file(path: str) -> str:
    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if path.lower().endswith(".docx"):
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    print("Unsupported guide format")
    return

# ===================== NORMALIZATION =====================
def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r"\b(x\d+|\(\d+\)|\d+)\b", "", name)
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def normalize_image_url(url):
    if not isinstance(url, str) or not url.strip():
        return None
    parsed = urlparse(url.strip())
    return parsed.path.lower().strip()

def clean_value(v):
    import pandas as pd
    if pd.isna(v) or v == "":
        return None
    return v