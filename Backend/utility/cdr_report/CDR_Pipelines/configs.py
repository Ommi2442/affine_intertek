# configs.py
 
import os
from pathlib import Path
from dotenv import load_dotenv
from azure.cosmos import CosmosClient
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough



# =======================
# RUNTIME CONTEXT
# =======================

from dataclasses import dataclass

@dataclass
class RuntimeContext:
    project_id: str | None = None
    _initialized: bool = False


runtime = RuntimeContext()


def init_runtime(*, project_id: str) -> None:
    """
    Initialize runtime context exactly once.
    Must be called before any pipeline logic.
    """
    if runtime._initialized:
        raise RuntimeError(
            "RuntimeContext already initialized. "
            "Multiple initializations are not allowed."
        )

    if not project_id or not isinstance(project_id, str):
        raise ValueError("Valid project_id is required to initialize runtime")

    runtime.project_id = project_id
    runtime._initialized = True


def require_runtime() -> None:
    """
    Guard to ensure runtime context is initialized.
    """
    if not runtime._initialized or not runtime.project_id:
        raise RuntimeError(
            "RuntimeContext not initialized. "
            "Call configs.init_runtime(project_id=...) before execution."
        )

from azure.storage.blob import (
    BlobServiceClient,
    generate_container_sas,
    ContainerSasPermissions
)
from datetime import datetime, timedelta


def build_container_sas_url(
    connection_string: str,
    container_name: str,
    expiry_hours: int = 24,
    read_only: bool = True,
):
    """
    Returns a SAS URL for an entire container.
    """

    blob_service_client = BlobServiceClient.from_connection_string(
        connection_string
    )

    account_name = blob_service_client.account_name
    account_key = blob_service_client.credential.account_key

    permissions = (
        ContainerSasPermissions(read=True, list=True)
        if read_only
        else ContainerSasPermissions(read=True, list=True, write=True, create=True)
    )

    sas_token = generate_container_sas(
        account_name=account_name,
        container_name=container_name,
        account_key=account_key,
        permission=permissions,
        expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
    )

    return (
        f"https://{account_name}.blob.core.windows.net/"
        f"{container_name}?{sas_token}"
    )


# =======================
# CONFIGURATIONS
# =======================


load_dotenv()


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
SAS_URL                = os.getenv("SAS_URL")



#container = "3and4"
container = BLOB_CONTAINER

IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "svg"}
# AZURE_CONN_STRING = "BlobEndpoint=https://stintertekesusdev.blob.core.windows.net/;QueueEndpoint=https://stintertekesusdev.queue.core.windows.net/;FileEndpoint=https://stintertekesusdev.file.core.windows.net/;TableEndpoint=https://stintertekesusdev.table.core.windows.net/;SharedAccessSignature=sv=2024-11-04&ss=bfqt&srt=sco&sp=rwdlacupiytfx&se=2025-12-28T15:11:45Z&st=2025-12-13T06:56:45Z&spr=https,http&sig=EZbXjVsN%2FFYp1%2BTbv4CmvDTKDHORkLvuIPLbfKw%2F%2BJo%3D%22
# AZURE_CONN_STRING ="BlobEndpoint=https://stintertekesusdev.blob.core.windows.net/;QueueEndpoint=https://stintertekesusdev.queue.core.windows.net/;FileEndpoint=https://stintertekesusdev.file.core.windows.net/;TableEndpoint=https://stintertekesusdev.table.core.windows.net/;SharedAccessSignature=sv=2024-11-04&ss=bfqt&srt=sco&sp=rwdlacupiytfx&se=2025-12-28T15:11:45Z&st=2025-12-13T06:56:45Z&spr=https,http&sig=EZbXjVsN%2FFYp1%2BTbv4CmvDTKDHORkLvuIPLbfKw%2F%2BJo%3D%22
#AZURE_CONN_STRING = "BlobEndpoint=https://stintertekesusdev.blob.core.windows.net/;QueueEndpoint=https://stintertekesusdev.queue.core.windows.net/;FileEndpoint=https://stintertekesusdev.file.core.windows.net/;TableEndpoint=https://stintertekesusdev.table.core.windows.net/;SharedAccessSignature=sv=2024-11-04&ss=bfqt&srt=sco&sp=rwdlacupiytfx&se=2025-12-28T15:11:45Z&st=2025-12-13T06:56:45Z&spr=https,http&sig=EZbXjVsN%2FFYp1%2BTbv4CmvDTKDHORkLvuIPLbfKw%2F%2BJo%3D%22%2FN8wstTCJs8FiY%3D"
#AZURE_CONN_STRING = "BlobEndpoint=https://stintertekesusdev.blob.core.windows.net/;QueueEndpoint=https://stintertekesusdev.queue.core.windows.net/;FileEndpoint=https://stintertekesusdev.file.core.windows.net/;TableEndpoint=https://stintertekesusdev.table.core.windows.net/;SharedAccessSignature=sv=2024-11-04&ss=bfqt&srt=sco&sp=rwdlacupiytfx&se=2027-01-01T17:24:00Z&st=2026-01-05T09:09:00Z&spr=https,http&sig=HizD5Onismg%2BPLykgFqZNTmjJ7A5Ee%2FDdJAcpBkFacQ%3D"


# AOAI_ENDPOINT = "https://oai-intertek-esus2-dev.openai.azure.com/"
# AOAI_KEY      = "4v5aVQDu1ZzGxEDldBahCMXEW3vDF4CUj4tNETLtP4VqeoCwEnTkJQQJ99BKACYeBjFXJ3w3AAABACOGrI05"
# API_VERSION   = "2024-12-01-preview"
# EMBED_DEPLOY  = "text-embedding-ada-002"
# CHAT_DEPLOY   = "gpt-4.1"
# COSMOS_URL    = "https://csdb-intertek-esus-dev.documents.azure.com:443/"
# COSMOS_KEY    = "azcUeVxFxoYoFkChvWI8Wr8lMijOuWXDYQsvMf6O2LmT0Uv3Zs7lDPiXSxWYOjq00MFDbK88ApotACDbODLFXA=="
# COSMOS_DB     = "csdb-intertek-esus-dev"
# COSMOS_CONT   = "vectorstorecontainer"

COSMOS_DB     = COSMOS_DB_TEXT
COSMOS_CONT   = COSMOS_CONT_TEXT
CHUNK_SIZE    = 1200
CHUNK_OVERLAP = 150
TOP_K         = 5
DB_NAME     = COSMOS_DB
CONT_NAME   = COSMOS_CONT
 
EMBED_DIM   = 1536
VECTOR_PATH = "/vector"
PARTITION_KEY = "/id"
AZURE_OPENAI_ENDPOINT = AOAI_ENDPOINT
AZURE_OPENAI_API_KEY      = AOAI_KEY
AZURE_OPENAI_API_VERSION   = API_VERSION
cosmos_client = CosmosClient(url=COSMOS_URL, credential=COSMOS_KEY)
 
 
 
 
llm = AzureChatOpenAI(
    azure_endpoint=AOAI_ENDPOINT,
    api_key=AOAI_KEY,
    openai_api_version=API_VERSION,
    azure_deployment=CHAT_DEPLOY,
    temperature=0.1,
)

llm2 = AzureChatOpenAI(
    azure_endpoint=AOAI_ENDPOINT,
    api_key=AOAI_KEY,
    openai_api_version=API_VERSION,
    azure_deployment=CHAT_DEPLOY,
    temperature=0.0,
)
 
score_llm = AzureChatOpenAI(
    azure_endpoint=AOAI_ENDPOINT,
    api_key=AOAI_KEY,
    openai_api_version=API_VERSION,
    azure_deployment=CHAT_DEPLOY,
    temperature=0.0,   # important for stable scoring
)
 
 
 
# ==================== API CONFIGURATION ====================
 
AZURE_OPENAI_ENDPOINT = AOAI_ENDPOINT
AZURE_OPENAI_KEY = AOAI_KEY
AZURE_OPENAI_API_VERSION = API_VERSION
 
COSMOS_ENDPOINT = COSMOS_URL
COSMOS_KEY = COSMOS_KEY
COSMOS_DB_NAME = COSMOS_DB
COSMOS_CONTAINER_NAME = COSMOS_CONT
 
AZURE_BLOB_CONNECTION_STRING = AZURE_CONN_STRING
BLOB_CONTAINER_NAME = container
AZURE_BLOB_CONTAINER_SAS_URL = SAS_URL
#AZURE_BLOB_CONTAINER_SAS_URL = "https://stintertekesusdev.blob.core.windows.net/cdr-test?sp=r&st=2025-12-17T13:00:21Z&se=2040-12-30T21:15:21Z&sv=2024-11-04&sr=c&sig=IvefAZb2x6KvlYtb22W5VK9DoQ2PDosWYtmtZO1pPCM%3D%22"
#AZURE_BLOB_CONTAINER_SAS_URL = "https://stintertekesusdev.blob.core.windows.net/3and4?sp=r&st=2026-01-05T09:07:03Z&se=2027-01-01T17:22:03Z&sv=2024-11-04&sr=c&sig=OQz72jtNDk%2Fp3BI3HHCAxULnfFjsS8XKz3USwZQryms%3D"
# AZURE_BLOB_CONTAINER_SAS_URL = build_container_sas_url(
#     AZURE_CONN_STRING,
#     container,
#     expiry_hours=120
# )

#print(container_sas_url)
 
# ==================== MODEL CONFIG ====================
VISION_MODEL = CHAT_DEPLOY
EMBED_MODEL = EMBED_DEPLOY
CLASSIFICATION_MODEL = VISION_MODEL
LLM_CONTEXT_MODEL = VISION_MODEL
 
# ==================== FILE PATHS ====================
 
# TEMPLATE_PATH = Path("cdr_payload.json")  # your uploaded template
 
# #c1
# MASTER_SHEET_PATH = "master_bom.xlsx"
# OUTPUT_PATH_FINAL = "s4c1_cc_raw.xlsx"
# CRITICAL_ONLY_EXCEL = "s4c1_cc_filtered.xlsx"
# FINAL_OUTPUT_WITH_EVIDENCE = "s4c1_cc_final.xlsx"
# OUTPUT_JSON_COMPONENTS = "s4.json"
# OUTPUT_JSON_METADATA = "s3.json"
 
# #c2
# OUTPUT_EXCEL_RAW = "s4c2_cc_raw.xlsx"
# OUTPUT_EXCEL_CLASSIFIED = "s4c2_cc_filtered.xlsx"
# OUTPUT_EXCEL_DEDUPED = "s4c2_cc_final.xlsx"
# OUTPUT_JSON_S4 = "s4.json"
# OUTPUT_JSON_S3 = "s3.json"
# DOWNLOAD_DIR = "downloaded_guides"
 
# ==================== SETTINGS ====================
MAX_WORKERS = 4
IMAGE_BATCH_SIZE = 4
BATCH_SIZE = 15
CLASSIFICATION_BATCH_SIZE = 5
 
 
GUIDE_KEYWORDS = [
    "user guide", "user-guide", "manual", "operation manual",
    "operating manual", "instruction", "instructions"
]
 
 
 
 
 
 
#hari changes
from pathlib import Path
 
# Base directory of this file (CDR_Pipelines)
BASE_DIR = Path(__file__).resolve().parent
 
# Templates / JSON
TEMPLATE_PATH = BASE_DIR / "cdr_payload.json"
OUTPUT_JSON_S4 = BASE_DIR / "s4.json"
OUTPUT_JSON_S3 = BASE_DIR / "s3.json"
OUTPUT_JSON_COMPONENTS = BASE_DIR / "s4.json"
OUTPUT_JSON_METADATA = BASE_DIR / "s3.json"

 
# Excel / sheets
MASTER_SHEET_PATH = BASE_DIR / "master_bom.xlsx"
OUTPUT_PATH_FINAL = BASE_DIR / "s4c1_cc_raw.xlsx"
CRITICAL_ONLY_EXCEL = BASE_DIR / "s4c1_cc_filtered.xlsx"
FINAL_OUTPUT_WITH_EVIDENCE = BASE_DIR / "s4c1_cc_final.xlsx"
 
OUTPUT_EXCEL_RAW = BASE_DIR / "s4c2_cc_raw.xlsx"
OUTPUT_EXCEL_CLASSIFIED = BASE_DIR / "s4c2_cc_filtered.xlsx"
OUTPUT_EXCEL_DEDUPED = BASE_DIR / "s4c2_cc_final.xlsx"
# report generation paths
OUTPUT_EXCEL_AI_GEN_PATH = BASE_DIR / "CDR_Report_AI.xlsx"
OUTPUT_EXCEL_AI_FINAL_PATH = BASE_DIR / "CDR_Final_Report_AI.xlsx"
 
 
# Directories
DOWNLOAD_DIR = BASE_DIR / "downloaded_guides"
SRC_FILES_DIR = BASE_DIR / "src_files"


# main.py paths
PIPELINE_DIR = Path(__file__).resolve().parent

EXTRACTED_TXT_PATH = PIPELINE_DIR / "extracted.txt"
CDR_PAYLOAD_PATH = PIPELINE_DIR / "cdr_payload.json"
OUTPUT_CDR_PATH = PIPELINE_DIR / "cdr_payload_v5_updated.json"

SRC_ROOT = PIPELINE_DIR / "src_files"
FLAT_ROOT = PIPELINE_DIR / "flattened_pdfs"
IMG_ROOT = PIPELINE_DIR / "page_images"