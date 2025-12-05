# embedding.py
import os
from azure.cosmos import CosmosClient, ConsistencyLevel
from langchain_openai import AzureOpenAIEmbeddings
from langchain_azure_ai.vectorstores import AzureCosmosDBNoSqlVectorSearch
from utility.trf_utils import *
from dotenv import load_dotenv

load_dotenv()

# Chunking config
CHUNK_SIZE = 1200
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
COSMOS_URL         = os.getenv("COSMOS_URL")
COSMOS_KEY         = os.getenv("COSMOS_KEY")

print('AOAI_ENDPOINT', AOAI_ENDPOINT)

client = CosmosClient(COSMOS_URL, credential=COSMOS_KEY, consistency_level=ConsistencyLevel.Eventual)
container = client.get_database_client(DB_NAME).get_container_client(CONT_NAME)


def ingest_files_from_blob_urls_create_embeddings(project_id: str, blob_urls: list) -> dict:
    """
    Full ingestion pipeline for a specific project.
    project_id = Project_Id (PRJ_xxx)
    blob_urls = list of blob URLs from Cosmos Source_Doc
    """

    print(f"\n===== 🚀 Starting Embedding for Project {project_id} =====")
    print("Files:", len(blob_urls))

    # ---- Step 1: Blob download + extract ----
    (
        extracted_texts,
        image_urls,
        downloaded_pdf_paths,
        converted_pdf_paths,
    ) = process_blob_urls_2(
        blob_urls,
        AZURE_CONN_STRING,
        container="stintertekesusdev-blob",
        download_dir=f"src_files/{project_id}",
        keep_files=True,
        verbose=True,
    )

    pdf_paths = downloaded_pdf_paths + converted_pdf_paths

    print("✔ Files downloaded & extracted")

    # ---- Step 2: Create Vector DB container ----
    container = create_db_and_container(
        client, DB_NAME, VECTOR_PATH, EMBED_DIM, CONT_NAME
    )

    print("✔ CosmosDB vector container ready")

    # ---- Step 3: Embeddings ----
    embeddings = build_embeddings(AOAI_ENDPOINT, AOAI_KEY, API_VERSION, EMBED_DEPLOY)
    vectorstore = build_vectorstore(embeddings)

    # ---- Step 4: Chunk documents ----
    chunks = load_and_split_pdfs_text(
        pdf_paths,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
        extracted_texts=extracted_texts,
    )

    print(f"✔ Chunking complete → {len(chunks)} chunks")

    docs = add_ids_to_chunks(chunks)

    # ---- Step 5: Ingest vectors ----
    ingest_to_cosmos_parallel(vectorstore, docs, batch_size=10, max_workers=10)

    print("✔ Vector ingestion finished")

    return {
        "projectId": project_id,
        "chunks_count": len(chunks),
        "files_processed": pdf_paths,
        "images_found": image_urls
    }
