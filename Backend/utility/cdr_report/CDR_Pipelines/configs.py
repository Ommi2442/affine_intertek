import os
from pathlib import Path
from dataclasses import dataclass
from threading import RLock
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Optional, Dict, Tuple


from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient, generate_container_sas, ContainerSasPermissions
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough


# ============================================================
# PROJECT RUNTIME (SAFE, MULTI-USER AWARE)
# ============================================================

@dataclass(frozen=True)
class RuntimeContext:
    project_id: str
    user_id: str              # <-- NEW (not used in path)
    base_dir: Path


# key = (project_id, user_id)
_runtime_registry: Dict[Tuple[str, str], RuntimeContext] = {}

# ---------------- LEGACY RUNTIME PROXY ----------------
class _LegacyRuntimeProxy:
    """
    Backward compatibility layer.
    Old code accessing `_runtime.project_id` will still work.
    Returns the most recently initialized runtime.
    """
    @property
    def project_id(self) -> Optional[str]:
        if not _runtime_registry:
            return None
        return next(reversed(_runtime_registry.values())).project_id

    @property
    def user_id(self) -> Optional[str]:
        if not _runtime_registry:
            return None
        return next(reversed(_runtime_registry.values())).user_id


# expose legacy name expected by old code
_runtime = _LegacyRuntimeProxy()

_lock = RLock()


# ============================================================
# API
# ============================================================

def init_runtime(*, project_id: str, user_id: str) -> RuntimeContext:
    """
    Initialize runtime for a (project_id, user_id) pair.
    Safe to call multiple times.
    """
    key = (project_id, user_id)

    with _lock:
        if key not in _runtime_registry:
            base = (
                Path(__file__)
                .resolve()
                .parents[3]
                / "data"
                / "cdr_files"
                / project_id     # <-- user_id intentionally NOT used here
            )
            base.mkdir(parents=True, exist_ok=True)

            _runtime_registry[key] = RuntimeContext(
                project_id=project_id,
                user_id=user_id,
                base_dir=base,
            )

        return _runtime_registry[key]


def get_runtime(*, project_id: str, user_id: str) -> RuntimeContext:
    """
    Fetch runtime for a specific user + project.
    """
    key = (project_id, user_id)
    try:
        return _runtime_registry[key]
    except KeyError:
        raise RuntimeError(
            f"Runtime not initialized for project_id={project_id}, user_id={user_id}"
        )


def clear_runtime(*, project_id: str, user_id: str) -> None:
    """
    Remove a runtime safely.
    """
    key = (project_id, user_id)
    with _lock:
        _runtime_registry.pop(key, None)


def require_runtime() -> None:
    """
    Legacy guard: ensures *some* runtime exists.
    """
    if not _runtime_registry:
        raise RuntimeError("Runtime not initialized")


def build_cosmos_cont_name() -> str:
    require_runtime()
    project_id = _runtime.project_id
    user_id = _runtime.user_id

    if not project_id or not user_id:
        raise RuntimeError("Runtime initialized but user_id or project_id missing")
    return f"vectorstorecontainer_new_itk_text_{user_id}_{project_id}"
 


# ============================================================
# LOAD ENV
# ============================================================

load_dotenv()

AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")
AOAI_KEY = os.getenv("AOAI_KEY")
API_VERSION = os.getenv("API_VERSION")
EMBED_DEPLOY = os.getenv("EMBED_DEPLOY")
CHAT_DEPLOY = os.getenv("CHAT_DEPLOY")

COSMOS_DB_TEXT = os.getenv("COSMOS_DB_TEXT")
#COSMOS_CONT_TEXT = os.getenv("COSMOS_CONT_TEXT")
COSMOS_DB_IMAGE = os.getenv("COSMOS_DB_IMAGE")
COSMOS_CONT_IMAGE = os.getenv("COSMOS_CONT_IMAGE")

COSMOS_URL = os.getenv("COSMOS_URL")
COSMOS_ENDPOINT = COSMOS_URL
COSMOS_KEY = os.getenv("COSMOS_KEY")

AZURE_CONN_STRING = os.getenv("AZURE_CONN_STRING_CDR")
BLOB_CONTAINER = os.getenv("BLOB_CONTAINER")
BLOB_CONT_NAME = os.getenv("BLOB_CONT_NAME")
SAS_URL = os.getenv("SAS_URL")
ENABLE_CAD_SCHEMATICS = os.getenv("ENABLE_CAD_SCHEMATICS")


# ============================================================
# LEGACY VARIABLE COMPATIBILITY
# ============================================================


class _DynamicPath:
    def __init__(self, resolver):
        self._resolver = resolver

    def __getattr__(self, name):
        return getattr(self._resolver(), name)

    def __fspath__(self):
        return str(self._resolver())

    def __str__(self):
        return str(self._resolver())

    def __truediv__(self, other):
        return self._resolver() / other


class _DynamicValue:
    def __init__(self, resolver):
        self._resolver = resolver
    def __str__(self):
        return str(self._resolver())
    def __repr__(self):
        return repr(self._resolver())
    def __call__(self):
        return self._resolver()


COSMOS_CONT_TEXT = _DynamicValue(build_cosmos_cont_name)
COSMOS_DB = COSMOS_DB_TEXT
COSMOS_CONT = COSMOS_CONT_TEXT

DB_NAME = COSMOS_DB
CONT_NAME = COSMOS_CONT
COSMOS_DB_NAME = COSMOS_DB
COSMOS_CONTAINER_NAME = COSMOS_CONT

AZURE_OPENAI_ENDPOINT = AOAI_ENDPOINT
AZURE_OPENAI_KEY = AOAI_KEY
AZURE_OPENAI_API_KEY = AOAI_KEY
AZURE_OPENAI_API_VERSION = API_VERSION

AZURE_BLOB_CONNECTION_STRING = AZURE_CONN_STRING
BLOB_CONTAINER_NAME = BLOB_CONTAINER
container = BLOB_CONTAINER
AZURE_CONTAINER_NAME = BLOB_CONTAINER

AZURE_BLOB_CONTAINER_SAS_URL = SAS_URL
AZURE_BLOB_CONTAINER_NAME_SAS_URL = SAS_URL

VECTOR_PATH = "/vector"
PARTITION_KEY = "/id"


# ============================================================
# CLIENTS (GLOBAL SAFE)
# ============================================================

cosmos_client = CosmosClient(url=COSMOS_URL, credential=COSMOS_KEY)
blob_service = BlobServiceClient.from_connection_string(AZURE_CONN_STRING)

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
    temperature=0.0,
)

 


# ============================================================
# PROJECT PATHS
# ============================================================

def project_paths(project_id: str):
    base = (
        Path(__file__)
        .resolve()
        .parents[3]
        / "data"
        / "cdr_files"
        / project_id
    )

    return {
        "BASE": base,
        "SRC": base / "src_files",
        "S3": base.parent / "s3.json",
        "S4": base.parent / "s4.json",
        "CDR_PAYLOAD": base.parent / "cdr_payload.json",
        "FINAL_JSON": base / "cdr_payload_v5_updated.json",
        "AI_RAW": base / "CDR_Report_AI.xlsx",
        "AI_FINAL": base / "CDR_Final_Report_AI.xlsx",
    }
 


# ============================================================
# LEGACY GLOBAL FILE PATHS (PROJECT SAFE)
# ============================================================


def _cur():
    if not _runtime_registry:
        raise RuntimeError("Runtime not initialized")
    return next(reversed(_runtime_registry.values())).base_dir


TEMPLATE_PATH = _DynamicPath(lambda: _cur().parent / "cdr_payload.json")
CDR_PAYLOAD_PATH = TEMPLATE_PATH

EXCEL_TEMPLATE = _DynamicPath(lambda: _cur().parent / "CDR_template.xlsx")

OUTPUT_JSON_S3 = _DynamicPath(lambda: _cur().parent / "s3.json")
OUTPUT_JSON_S4 = _DynamicPath(lambda: _cur().parent / "s4.json")
OUTPUT_JSON_COMPONENTS = _DynamicPath(lambda: _cur().parent / "s4.json")
OUTPUT_JSON_METADATA = _DynamicPath(lambda: _cur().parent / "s3.json")

BASE_DIR = _DynamicPath(lambda: _cur())
SRC_FILES_DIR = _DynamicPath(lambda: _cur() / "src_files")
DOWNLOAD_DIR = _DynamicPath(lambda: _cur() / "downloaded_guides")

OUTPUT_CDR_PATH = _DynamicPath(lambda: _cur() / "cdr_payload_v5_updated.json")
EXTRACTED_TXT_PATH = _DynamicPath(lambda: _cur() / "extracted.txt")

SRC_ROOT = _DynamicPath(lambda: _cur() / "src_files")
FLAT_ROOT = _DynamicPath(lambda: _cur() / "flattened_pdfs")
IMG_ROOT = _DynamicPath(lambda: _cur() / "page_images")

OUTPUT_EXCEL_AI_GEN_PATH = _DynamicPath(lambda: _cur() / "CDR_Report_AI.xlsx")
OUTPUT_EXCEL_AI_FINAL_PATH = _DynamicPath(lambda: _cur() / "CDR_Final_Report_AI.xlsx")

MASTER_SHEET_PATH = _DynamicPath(lambda: _cur() / "master_bom.xlsx")
OUTPUT_PATH_FINAL = _DynamicPath(lambda: _cur() / "s4c1_cc_raw.xlsx")
CRITICAL_ONLY_EXCEL = _DynamicPath(lambda: _cur() / "s4c1_cc_filtered.xlsx")
FINAL_OUTPUT_WITH_EVIDENCE = _DynamicPath(lambda: _cur() / "s4c1_cc_final.xlsx")
ALL_IMAGE_URLS_CSV = _DynamicPath(lambda: _cur() / "all_device_images.csv")
 

OUTPUT_EXCEL_RAW = _DynamicPath(lambda: _cur() / "s4c2_cc_raw.xlsx")
OUTPUT_EXCEL_CLASSIFIED = _DynamicPath(lambda: _cur() / "s4c2_cc_filtered.xlsx")
OUTPUT_EXCEL_DEDUPED = _DynamicPath(lambda: _cur() / "s4c2_cc_final.xlsx")



# ============================================================
# BLOB HELPERS
# ============================================================

def build_container_sas_url(container: str, expiry_hours=48):
    sas = generate_container_sas(
        blob_service.account_name,
        container,
        blob_service.credential.account_key,
        ContainerSasPermissions(read=True, list=True, write=True),
        datetime.utcnow() + timedelta(hours=expiry_hours),
    )
    return f"https://{blob_service.account_name}.blob.core.windows.net/{container}?{sas}"


def get_cosmos_container_client():
    """
    Returns Cosmos container client for *current* (user_id, project_id) runtime.
    Must be called after init_runtime().
    """
    ctx = require_runtime()
    cont_name = build_cosmos_cont_name()  # returns a REAL str
    return cosmos_client.get_database_client(DB_NAME).get_container_client(cont_name)



# def get_cosmos_container():
#     """
#     One-stop function:
#     - requires runtime (user_id + project_id)
#     - builds dynamic container name
#     - creates container if missing
#     - returns Cosmos ContainerProxy (client)
#     """
#     ctx = require_runtime()  # ensures init_runtime(project_id, user_id) was called

#     container_name = f"{ctx.project_id}_{ctx.user_id}"  # your desired format

#     db = cosmos_client.get_database_client(COSMOS_DB_NAME)
#     return db.create_container_if_not_exists(
#         id=container_name,
#         partition_key=PartitionKey(path=PARTITION_KEY),
#     )


# ============================================================
# CONSTANTS
# ============================================================

IMAGE_EXTS = {"jpg","jpeg","png","gif","bmp","tiff","tif","webp","svg"}
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
TOP_K = 5
EMBED_DIM = 1536
MAX_WORKERS = 4
IMAGE_BATCH_SIZE = 4
BATCH_SIZE = 15
CLASSIFICATION_BATCH_SIZE = 5

# ==================== MODEL CONFIG ====================
VISION_MODEL = CHAT_DEPLOY
EMBED_MODEL = EMBED_DEPLOY
CLASSIFICATION_MODEL = VISION_MODEL
LLM_CONTEXT_MODEL = VISION_MODEL

GUIDE_KEYWORDS = [
    "user guide", "user-guide", "manual",
    "operation manual", "operating manual",
    "instruction", "instructions"
]
