AZURE_CONN_STRING = "BlobEndpoint=https://saaffine.blob.core.windows.net/;QueueEndpoint=https://saaffine.queue.core.windows.net/;FileEndpoint=https://saaffine.file.core.windows.net/;TableEndpoint=https://saaffine.table.core.windows.net/;SharedAccessSignature=sv=2024-11-04&ss=bfqt&srt=sco&sp=rwdlacupiytfx&se=2026-02-27T19:14:19Z&st=2026-01-05T10:59:19Z&spr=https&sig=yi4FlLyZsq94IYX0taVVkbaYtil4Nv7qeWIVyhUNGP8%3D"


# for image processing (don't run)

DB_NAME_IMG    = "ragdatabase_new_itk2"
CONT_NAME_IMG  = "vectorstorecontainer_new_itk2"

# Chunking / Retrieval knobs
CHUNK_SIZE    = 1000   # RecursiveCharacterTextSplitter is char-based
CHUNK_OVERLAP = 150
TOP_K         = 5
# Match your embedding model (Azure OpenAI text-embedding-3-* = 1536)
EMBED_DIM   = 1536
VECTOR_PATH = "/vector"   # must start with "/"



# container = "nasa-ebooks-pdfs-all"
BLOB_CONTAINER_NAME="nasa-ebooks-pdfs-all"
conn_str = AZURE_CONN_STRING


IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "svg"}


# -----------------------
# Config
# -----------------------
# AOAI_ENDPOINT = "https://llm-intertek.openai.azure.com/"
# AOAI_KEY      = "9NIydcGzV6uSUiHecTK1HaeuM3iKn4lMGQh2Z6irgq57NWUmA0J2JQQJ99BJACYeBjFXJ3w3AAABACOGdprE"
AOAI_ENDPOINT = "https://oai-intertek-esus2-dev.openai.azure.com/"
AOAI_KEY = "4v5aVQDu1ZzGxEDldBahCMXEW3vDF4CUj4tNETLtP4VqeoCwEnTkJQQJ99BKACYeBjFXJ3w3AAABACOGrI05"
API_VERSION   = "2024-12-01-preview"

EMBED_DEPLOY  = "text-embedding-ada-002"#"text-embedding-3-large"
CHAT_DEPLOY   = "gpt-4.1"#"gpt-4o"#"gpt-4.1"


# COSMOS_URL    = "https://csdb-intertek-esus-dev.documents.azure.com:443/"
# COSMOS_KEY    = "azcUeVxFxoYoFkChvWI8Wr8lMijOuWXDYQsvMf6O2LmT0Uv3Zs7lDPiXSxWYOjq00MFDbK88ApotACDbODLFXA=="
# COSMOS_DB     = "ragdatabase"
# COSMOS_CONT   = "vectorstorecontainer"
# DB_NAME = "ragdatabase"
# CONT_NAME = "vectorstorecontainer"

COSMOS_URL    = "https://rag-intertek.documents.azure.com:443/"
COSMOS_KEY    = "AbhkomWJLtf8TR7odpABPqx1OrjlmCcpTXlKr9Vvp3RulZmFGollxQflIp3LLUAFt4XcMh70RbRxACDbuxyZLg=="
# COSMOS_URL    = "https://csdb-intertek-esus-dev.documents.azure.com:443/"
# COSMOS_KEY    = "azcUeVxFxoYoFkChvWI8Wr8lMijOuWXDYQsvMf6O2LmT0Uv3Zs7lDPiXSxWYOjq00MFDbK88ApotACDbODLFXA=="
COSMOS_DB     = "ragdatabase_new_itk"
COSMOS_CONT   = "vectorstorecontainer_new_itk"
DB_NAME = "ragdatabase_new_itk"
CONT_NAME = "vectorstorecontainer_new_itk"


MAX_THREADS = 10
MAX_RETRIES = 5
INITIAL_BACKOFF = 3
