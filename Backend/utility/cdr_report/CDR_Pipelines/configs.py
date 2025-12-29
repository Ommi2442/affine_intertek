# configs.py

import os
from pathlib import Path
from azure.cosmos import CosmosClient
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
container = "cdr-test"
IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "svg"}
AZURE_CONN_STRING = "BlobEndpoint=https://stintertekesusdev.blob.core.windows.net/;QueueEndpoint=https://stintertekesusdev.queue.core.windows.net/;FileEndpoint=https://stintertekesusdev.file.core.windows.net/;TableEndpoint=https://stintertekesusdev.table.core.windows.net/;SharedAccessSignature=sv=2024-11-04&ss=bfqt&srt=sco&sp=rwdlacupiytfx&se=2025-12-28T15:11:45Z&st=2025-12-13T06:56:45Z&spr=https,http&sig=EZbXjVsN%2FFYp1%2BTbv4CmvDTKDHORkLvuIPLbfKw%2F%2BJo%3D"

AOAI_ENDPOINT = "https://oai-intertek-esus2-dev.openai.azure.com/"
AOAI_KEY      = "4v5aVQDu1ZzGxEDldBahCMXEW3vDF4CUj4tNETLtP4VqeoCwEnTkJQQJ99BKACYeBjFXJ3w3AAABACOGrI05"
API_VERSION   = "2024-12-01-preview"
EMBED_DEPLOY  = "text-embedding-ada-002"
CHAT_DEPLOY   = "gpt-4.1"
COSMOS_URL    = "https://csdb-intertek-esus-dev.documents.azure.com:443/"
COSMOS_KEY    = "azcUeVxFxoYoFkChvWI8Wr8lMijOuWXDYQsvMf6O2LmT0Uv3Zs7lDPiXSxWYOjq00MFDbK88ApotACDbODLFXA=="
COSMOS_DB     = "csdb-intertek-esus-dev"
COSMOS_CONT   = "vectorstorecontainer"
CHUNK_SIZE    = 1200
CHUNK_OVERLAP = 150
TOP_K         = 5
DB_NAME     = COSMOS_DB
CONT_NAME   = COSMOS_CONT

EMBED_DIM   = 1536
VECTOR_PATH = "/vector"
PARTITION_KEY = "/id"
AZURE_OPENAI_ENDPOINT = "https://oai-intertek-esus2-dev.openai.azure.com/"
AZURE_OPENAI_API_KEY      = "4v5aVQDu1ZzGxEDldBahCMXEW3vDF4CUj4tNETLtP4VqeoCwEnTkJQQJ99BKACYeBjFXJ3w3AAABACOGrI05"
AZURE_OPENAI_API_VERSION   = "2024-12-01-preview"
cosmos_client = CosmosClient(url=COSMOS_URL, credential=COSMOS_KEY)




llm = AzureChatOpenAI(
    azure_endpoint=AOAI_ENDPOINT,
    api_key=AOAI_KEY,
    openai_api_version=API_VERSION,
    azure_deployment=CHAT_DEPLOY,
    temperature=0.1,
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
AZURE_BLOB_CONTAINER_SAS_URL = "https://stintertekesusdev.blob.core.windows.net/cdr-test?sp=r&st=2025-12-17T13:00:21Z&se=2040-12-30T21:15:21Z&sv=2024-11-04&sr=c&sig=IvefAZb2x6KvlYtb22W5VK9DoQ2PDosWYtmtZO1pPCM%3D"


# ==================== MODEL CONFIG ====================
VISION_MODEL = CHAT_DEPLOY
EMBED_MODEL = EMBED_DEPLOY
CLASSIFICATION_MODEL = VISION_MODEL
LLM_CONTEXT_MODEL = VISION_MODEL

# ==================== FILE PATHS ====================

TEMPLATE_PATH = Path("cdr_payload.json")  # your uploaded template

#c1
MASTER_SHEET_PATH = "master_bom.xlsx"
OUTPUT_PATH_FINAL = "s4c1_cc_raw.xlsx"
CRITICAL_ONLY_EXCEL = "s4c1_cc_filtered.xlsx"
FINAL_OUTPUT_WITH_EVIDENCE = "s4c1_cc_final.xlsx"
OUTPUT_JSON_COMPONENTS = "s4.json"
OUTPUT_JSON_METADATA = "s3.json"

#c2
OUTPUT_EXCEL_RAW = "s4c2_cc_raw.xlsx"
OUTPUT_EXCEL_CLASSIFIED = "s4c2_cc_filtered.xlsx"
OUTPUT_EXCEL_DEDUPED = "s4c2_cc_final.xlsx"
OUTPUT_JSON_S4 = "s4.json"
OUTPUT_JSON_S3 = "s3.json"
DOWNLOAD_DIR = "downloaded_guides"

# ==================== SETTINGS ====================
MAX_WORKERS = 4
IMAGE_BATCH_SIZE = 4
BATCH_SIZE = 15
CLASSIFICATION_BATCH_SIZE = 5


GUIDE_KEYWORDS = [
    "user guide", "user-guide", "manual", "operation manual",
    "operating manual", "instruction", "instructions"
]






