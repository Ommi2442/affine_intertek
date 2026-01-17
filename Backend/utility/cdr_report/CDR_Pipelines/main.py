import os
import json
import time
import shutil
from pathlib import Path
from urllib.parse import quote

from utility.cdr_report.CDR_Pipelines.configs import (
    init_runtime,
    clear_runtime,
    project_paths,
    cosmos_client,
    AZURE_BLOB_CONNECTION_STRING,
    BLOB_CONTAINER_NAME,
    AZURE_CONN_STRING,
    container,
    DB_NAME
)

import utility.cdr_report.CDR_Pipelines.configs as configs

from utility.cdr_report.CDR_Pipelines.postprocessor import post_process_cdr
from utility.cdr_report.CDR_Pipelines.form_utils import build_ref
from utility.cdr_report.CDR_Pipelines.references import references_main
from utility.cdr_report.CDR_Pipelines.features_agent import features_tools_main
from utility.cdr_report.CDR_Pipelines.description import description_main, build_product_section_items
from utility.cdr_report.CDR_Pipelines.components_agent import run_sheet_3_and_4_agentic
import utility.cdr_report.CDR_Pipelines.compiler as compiler
import utility.cdr_report.CDR_Pipelines.utils as utils
from utility.cdr_report.CDR_Pipelines.utils import get_image_urls_from_container_sas, move_device_images_in_blob, get_blob_urls
from utility.cdr_report.CDR_Pipelines.editable_processing import extract_cis
from langchain_azure_ai.vectorstores import AzureCosmosDBNoSqlVectorSearch


# ============================================================
# UTILITIES
# ============================================================

def progress(step: int, total: int, msg: str, extra=None):
    payload = {
        "type": "progress",
        "step": step,
        "total": total,
        "percent": round((step / total) * 100, 2),
        "message": msg,
        "ts": time.time(),
    }
    if extra:
        payload["extra"] = extra
    print(json.dumps(payload), flush=True)


def get_trf_blob_url(conn_str, container, blob_name):
    p = dict(x.split("=", 1) for x in conn_str.split(";") if "=" in x)
    return f"{p['BlobEndpoint'].rstrip('/')}/{container}/{quote(blob_name, safe='/')}?{p['SharedAccessSignature'].lstrip('?')}"


def build_vectorstore():
    ctx = configs.require_runtime()
    COSMOS_CONTAINER_NAME = configs.build_cosmos_cont_name()
    return AzureCosmosDBNoSqlVectorSearch(
        cosmos_client=cosmos_client,
        embedding=utils.build_embeddings(),
        database_name=configs.COSMOS_DB_NAME,
        container_name=COSMOS_CONTAINER_NAME,
        vector_embedding_policy={
            "vectorEmbeddings": [{
                "path": "/vector",
                "dataType": "float32",
                "dimensions": configs.EMBED_DIM,
                "distanceFunction": "cosine"
            }]
        },
        indexing_policy={
            "includedPaths": [{"path": "/*"}],
            "excludedPaths": [{"path": "/\"_etag\"/?"}, {"path": "/vector/*"}],
            "vectorIndexes": [{"path": "/vector", "type": "quantizedFlat"}],
        },
        cosmos_container_properties={"partition_key": "/id"},
        cosmos_database_properties={},
        vector_search_fields={
            "text_field": "text",
            "embedding_field": "vector",
            "metadata_field": "metadata"
        }
    )


# ============================================================
# PIPELINE ENTRYPOINTS
# ============================================================


def main2(project_id, user_id, input_json, output_excel_path):
    """
    Safe entrypoint used by FastAPI, queue_worker, and CLI.
    """
    init_runtime(project_id=project_id, user_id=user_id)
    try:
        return main3(project_id, user_id, input_json, output_excel_path)
    finally:
        clear_runtime(project_id=project_id, user_id=user_id)


def main3(project_id, user_id, input_json, output_excel_path):
    paths = project_paths(project_id)

    print(f"[RUNTIME] Running project {project_id}")

    TOTAL = 16
    step = 0

    conn_str = AZURE_CONN_STRING

    # --------------------------------------------------
    # Prepare workspace
    # --------------------------------------------------
    if paths["SRC"].parent.exists():
        shutil.rmtree(paths["SRC"].parent)
    paths["SRC"].mkdir(parents=True, exist_ok=True)

    step += 1; progress(step, TOTAL, "Starting pipeline")

    # --------------------------------------------------
    # Blob cleanup
    # --------------------------------------------------
    device_prefix = f"Documents/{project_id}/source_documents/device_images"
    count = utils.delete_folder_if_exists(
        AZURE_BLOB_CONNECTION_STRING,
        BLOB_CONTAINER_NAME,
        device_prefix
    )
    step += 1; progress(step, TOTAL, "Device images cleaned", {"deleted": count})

    # --------------------------------------------------
    # TRF document
    # --------------------------------------------------
    trf_blob = get_trf_blob_url(
        AZURE_BLOB_CONNECTION_STRING,
        BLOB_CONTAINER_NAME,
        f"Documents/{project_id}/Generated_trf_Report/final_output_{project_id}.docx"
    )
    
    step += 1; progress(step, TOTAL, "Listing blob URLs")
    prefix = f"Documents/{project_id}/source_documents"
    blob_urls = get_blob_urls(conn_str, container)
    
    blob_urls.append(trf_blob)


    step += 1; progress(step, TOTAL, "Downloading TRF")
    extracted_texts, image_urls, _, _ = utils.process_blob_urls_2(
        blob_urls,
        AZURE_BLOB_CONNECTION_STRING,
        BLOB_CONTAINER_NAME,
        download_dir=paths["SRC"],
        keep_files=True,
        verbose=True
    )

    step += 1; progress(step, TOTAL, "Downloading images from blobs")
    image_urls = get_image_urls_from_container_sas()


    # --------------------------------------------------
    # CIS Extraction
    # --------------------------------------------------

    step += 1; progress(step, TOTAL, "Extracting CIS info")
    cis_info = extract_cis()
    extracted_texts += cis_info

    # --------------------------------------------------
    # Save extracted text
    # --------------------------------------------------
    step += 1; progress(step, TOTAL, "Saving extracted text")
    with open(paths["BASE"] / "extracted.txt", "w", encoding="utf-8") as f:
        json.dump(extracted_texts, f, indent=2)

    # --------------------------------------------------
    # Collect PDFs
    # --------------------------------------------------
    pdf_paths = [paths["SRC"] / f for f in os.listdir(paths["SRC"]) if f.lower().endswith(".pdf")]


    # --------------------------------------------------
    # Container Creation Cosmos
    # --------------------------------------------------
    step += 1; progress(step, TOTAL, "Creating DB/container (Cosmos)")
    container_obj = utils.create_db_and_container()

    db = cosmos_client.get_database_client(DB_NAME)
    print(f"db_created:{db}", flush=True)
    
    
    # --------------------------------------------------
    # Vector store
    # --------------------------------------------------
    
    step += 1; progress(step, TOTAL, "Building embeddings + vector store")
    # embeddings = utils.build_embeddings()
    vs = build_vectorstore()

    step += 1; progress(step, TOTAL, "Chunking + ingesting documents into vector store")
    chunks = utils.load_and_split_pdfs_text(pdf_paths, extracted_texts=extracted_texts)
    utils.ingest_chunks(vs, chunks, max_workers=5, batch_size=10)

    # --------------------------------------------------
    # Reference generation
    # --------------------------------------------------
    step += 1; progress(step, TOTAL, "Building references")
    ref = build_ref(input_json)

    step += 1; progress(step, TOTAL, "Generating references")
    template = references_main(vs, ref)

    # --------------------------------------------------
    # Description
    # --------------------------------------------------
    step += 1; progress(step, TOTAL, "Generating description")
    product_info = description_main(vs, ref)
    description = build_product_section_items(product_info, trf_blob)

    # --------------------------------------------------
    # Features
    # --------------------------------------------------
    step += 1; progress(step, TOTAL, "Running features")
    features = features_tools_main(vs, image_urls, run_audit=True)

    step += 1; progress(step, TOTAL, "Moving device images")
    moved = move_device_images_in_blob(
        image_urls=image_urls,
        connection_string=configs.AZURE_BLOB_CONNECTION_STRING,
        container_name=configs.BLOB_CONTAINER_NAME,
    )
    progress(step, TOTAL, "Device images moved", {"count": len(moved)})

    # --------------------------------------------------
    # Sheets 3 & 4
    # --------------------------------------------------
    step += 1; progress(step, TOTAL, "Running Sheets 3 & 4")
    run_sheet_3_and_4_agentic(vs=vs)

    # --------------------------------------------------
    # Post-processing
    # --------------------------------------------------
    step += 1; progress(step, TOTAL, "Post processing")

    with open(paths["CDR_PAYLOAD"], "r") as f:
        cdr = json.load(f)
    with open(paths["S3"], "r") as f:
        s3 = json.load(f)
    with open(paths["S4"], "r") as f:
        s4 = json.load(f)

    cdr = post_process_cdr(cdr, template, description, features, s3, s4)

    cdr, _ = utils.add_urls_sheet_1_and_6(cdr, configs.AZURE_BLOB_CONTAINER_SAS_URL)

    with open(paths["FINAL_JSON"], "w", encoding="utf-8") as f:
        json.dump(cdr, f, indent=2, ensure_ascii=False)

    # --------------------------------------------------
    # Excel
    # --------------------------------------------------
    step += 1; progress(step, TOTAL, "Generating Excel")
    compiler.fill_excel_from_json(cdr, output_excel_path)

    progress(TOTAL, TOTAL, "Done", {"project": project_id})

    Container_name = f"vectorstorecontainer_new_itk_text_{user_id}_{project_id}"

    utils.delete_cosmos_container(configs.COSMOS_URL,configs.COSMOS_KEY,configs.DB_NAME,Container_name)

    if paths["SRC"].parent.exists():
        shutil.rmtree(paths["SRC"].parent)

    return cdr
