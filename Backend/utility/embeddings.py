import os
from azure.cosmos import CosmosClient, ConsistencyLevel
from langchain_openai import AzureOpenAIEmbeddings
from langchain_azure_ai.vectorstores import AzureCosmosDBNoSqlVectorSearch

from trf_utils import (
    process_blob_urls_2,
    create_db_and_container,
    build_embeddings,
    build_vectorstore,
    load_and_split_pdfs_text,
    ingest_to_cosmos_parallel
)

# Chunking config
CHUNK_SIZE    = 1200
CHUNK_OVERLAP = 150
EMBED_DIM     = 1536
VECTOR_PATH   = "/vector"
TOP_K         = 5


def ingest_files_from_blob_urls_create_embeddings(blob_urls: list) -> dict:
    """
    Full ingestion pipeline:
    1. Download from blob URLs
    2. Extract text & convert docs
    3. Chunk
    4. Embed
    5. Ingest into Cosmos Vector DB
    """

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

    # Connect Cosmos
    client = CosmosClient(
        COSMOS_URL,
        credential=COSMOS_KEY,
        consistency_level=ConsistencyLevel.Eventual
    )

    print("✔ Connected to CosmosDB")

    # Step 1: Blob downloads + extraction
    extracted_texts, image_urls,
    downloaded_pdf_paths, converted_pdf_paths = process_blob_urls_2(
        blob_urls,
        AZURE_CONN_STRING,
        container="testing-blob",
        download_dir="src_files",
        keep_files=True,
        verbose=True
    )

    pdf_paths = downloaded_pdf_paths + converted_pdf_paths
    print("✔ Files downloaded & extracted")

    # Step 2: Create DB & containers
    container = create_db_and_container(
        client, DB_NAME, VECTOR_PATH, EMBED_DIM, CONT_NAME
    )
    print("✔ CosmosDB container ready")

    # Step 3: Embeddings
    embeddings = build_embeddings(
        AOAI_ENDPOINT, AOAI_KEY, API_VERSION, EMBED_DEPLOY
    )
    vs = build_vectorstore(embeddings)
    print("✔ Embeddings + vectorstore ready")

    # Step 4: Chunk PDFs
    chunks = load_and_split_pdfs_text(
        pdf_paths,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
        extracted_texts=extracted_texts
    )
    print(f"✔ Chunking completed → {len(chunks)} chunks")

    # Step 5: Ingest
    ingest_to_cosmos_parallel(vs, chunks, batch_size=10, max_workers=10)
    print("✔ Vector ingestion completed")

    return {
        "chunks_count": len(chunks),
        "pdfs_processed": pdf_paths,
        "images_found": image_urls,
        "vectorstore": vs
    }
