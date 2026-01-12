# main.py

import os
from pathlib import Path
import json
import shutil

from utility.cdr_report.CDR_Pipelines.postprocessor import post_process_cdr
from utility.cdr_report.CDR_Pipelines.editable_processing import extract_cis
from utility.cdr_report.CDR_Pipelines.configs import (
    container,
    AZURE_CONN_STRING,
    DB_NAME,
    CONT_NAME,
    cosmos_client
)
from utility.cdr_report.CDR_Pipelines.form_utils import build_ref
from utility.cdr_report.CDR_Pipelines.references import references_main
#from utility.cdr_report.CDR_Pipelines.features import features_main
from utility.cdr_report.CDR_Pipelines.features_agent import features_tools_main
from utility.cdr_report.CDR_Pipelines.utils import (
    get_blob_urls,
    process_blob_urls_2,
    download_images_from_blob_urls,
    create_db_and_container,
    build_embeddings,
    load_and_split_pdfs_text,
    ingest_chunks,
)
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_azure_ai.vectorstores import AzureCosmosDBNoSqlVectorSearch
from utility.cdr_report.CDR_Pipelines.description import (description_main, build_product_section_items)
import utility.cdr_report.CDR_Pipelines.utils as utils
from utility.cdr_report.CDR_Pipelines.switch import find_bom_blob_url
import utility.cdr_report.CDR_Pipelines.c1_main as c1_main
import utility.cdr_report.CDR_Pipelines.c2_main as c2_main
import utility.cdr_report.CDR_Pipelines.configs as configs
#import configs as configs


from utility.cdr_report.CDR_Pipelines.utils import move_device_images_in_blob
from utility.cdr_report.CDR_Pipelines.c2_utils import get_image_urls_from_container_sas
from utility.cdr_report.CDR_Pipelines.utils import get_image_urls_from_container_sas, move_device_images_in_blob
from utility.cdr_report.CDR_Pipelines.utils import delete_folder_if_exists
from utility.cdr_report.CDR_Pipelines.utils import add_urls_sheet_1_and_6
from utility.cdr_report.CDR_Pipelines.components_agent import run_sheet_3_and_4_agentic
import utility.cdr_report.CDR_Pipelines.compiler as compiler


project_id = "PRJ001"

def build_vectorstore():
    

    return AzureCosmosDBNoSqlVectorSearch(
        cosmos_client=configs.cosmos_client,
        embedding=build_embeddings(),
        database_name=configs.COSMOS_DB_NAME,
        container_name=configs.COSMOS_CONTAINER_NAME,

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

def main2(project_id,input_json_file, output_excel_path: Path, progress_callback=None):
    print("@@@@@@@@@@@@@@@@@@@  ----   CDR pipelines running-----    @@@@@@@@@@@@@@@@@@@@@@@@2")
    configs.init_runtime(project_id=project_id)
    return main3(input_json_file,output_excel_path)


# def run_sheet_3_and_4():
#     bom_url = find_bom_blob_url()
#     if bom_url:
#         c1_main.run_case1_pipeline()    
#     else:
#         c2_main.run_case2_pipeline()

import json, time

def progress(step: int, total: int, msg: str, extra: dict | None = None):
    """
    Prints progress in a frontend-friendly JSON line.
    Frontend can parse each line and update a progress bar.
    """
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

# from urllib.parse import quote

# def trf_blob_url(conn_str, container, blob):
#     p = dict(x.split("=",1) for x in conn_str.split(";") if "=" in x)
#     return f"{p['BlobEndpoint'].rstrip('/')}/{container}/{quote(blob.lstrip('/'), safe='/')}?{p['SharedAccessSignature'].lstrip('?')}"
from urllib.parse import quote

def get_trf_blob_url(conn_str, container, blob_name):
    p = dict(x.split("=",1) for x in conn_str.split(";") if "=" in x)
    return f"{p['BlobEndpoint'].rstrip('/')}/{container}/{quote(blob_name, safe='/')}?{p['SharedAccessSignature'].lstrip('?')}"



def main3(input_json_file,output_excel_path, progress_callback=None):
    configs.require_runtime()
    print(f"[RUNTIME] project_id = {configs.runtime.project_id}")

    
    # print(os)
    #os.chdir(r'.\utility\cdr_report\CDR_Pipelines')

    # ABSOLUTE BASE DIR (CDR_Pipelines)
    # --------------------------------------------------
        
    folder_path = configs.SRC_FILES_DIR
 
    if folder_path.exists():
        shutil.rmtree(folder_path)
    
    folder_path.mkdir(parents=True, exist_ok=True)

    

    TOTAL = 16
    step = 0

    conn_str = AZURE_CONN_STRING

    step += 1; progress(step, TOTAL, "Starting pipeline")

    
    step += 1; progress(step, TOTAL, "Deleting device_images folder if exists")
    device_prefix = f"Documents/{configs.runtime.project_id}/source_documents/device_images"
    count = delete_folder_if_exists(conn_str, container, device_prefix)
    progress(step, TOTAL, "device_images cleanup done", {"deleted_blobs": count})

    step += 1; progress(step, TOTAL, "Listing blob URLs")
    prefix = f"Documents/{configs.runtime.project_id}/source_documents"
    blob_urls = get_blob_urls(conn_str, container)

    step += 1; progress(step, TOTAL, "Listing blob URLs")
    prefix = f"Documents/{configs.runtime.project_id}/source_documents"
    trf_blob_url = get_trf_blob_url(conn_str, configs.container, f"Documents/{configs.runtime.project_id}/Generated_trf_report/final_output_{configs.runtime.project_id}.docx")


    step += 1; progress(step, TOTAL, "Processing blobs (extracting text/images/pdfs)")
    extracted_texts, image_urls, downloaded_pdf_paths, converted_pdf_paths = process_blob_urls_2(
    [trf_blob_url], conn_str, container,
    download_dir=configs.SRC_FILES_DIR, keep_files=True, verbose=True
    )

    step += 1; progress(step, TOTAL, "Downloading images from blobs")
    image_urls = get_image_urls_from_container_sas()


    # step += 1; progress(step, TOTAL, "Extracting CIS info")
    # cis_info = extract_cis()
    # extracted_texts += cis_info

    step += 1; progress(step, TOTAL, "Saving extracted text")
    with open(configs.EXTRACTED_TXT_PATH, "w", encoding="utf-8") as f:
        json.dump(extracted_texts, f, indent=4, default=str)

    step += 1; progress(step, TOTAL, "Collecting PDF paths")
    pdf_files = [f for f in os.listdir(configs.SRC_FILES_DIR) if f.lower().endswith(".pdf")]
    pdf_paths = [os.path.join(configs.SRC_FILES_DIR, f) for f in pdf_files]

    # step += 1; progress(step, TOTAL, "Creating DB/container (Cosmos)")
    # container_obj = create_db_and_container()

    # db = cosmos_client.get_database_client(DB_NAME)
    # print(f"db_created:{db}", flush=True)

    step += 1; progress(step, TOTAL, "Building embeddings + vector store")
    #embeddings = build_embeddings()
    vs = build_vectorstore()

    step += 1; progress(step, TOTAL, "Chunking + ingesting documents into vector store")
    # chunks = load_and_split_pdfs_text(pdf_paths, extracted_texts=extracted_texts)
    print("pdf_paths---",pdf_paths)
    chunks = load_and_split_pdfs_text(
    pdf_paths,
    configs.CHUNK_SIZE,
    configs.CHUNK_OVERLAP,
    extracted_texts=None,                                                                           #CHECK
    cad_schematics=False
    )
    chunks_uuid = utils.add_ids_to_chunks(chunks)
    
    utils.ingest_to_cosmos_parallel(vs, chunks_uuid, batch_size=10, max_workers=10)
    # ingest_chunks(vs, chunks, max_workers=5, batch_size=10)
    
    print("\n[SUCCESS] Image ingestion completed.\n")

    # print("text_chunks_ingested": len(chunks_uuid),"images_ingested": len(docs_image_uuid),"pdf_pages_extracted": len(image_page_metadata))

    step += 1; progress(step, TOTAL, "Building TRF ref + generating template/description")
    #with open("1614_pta.json", "r", encoding="utf-8") as f:
    #    trf_filled = json.load(f)
        
    trf_filled = input_json_file
    # print("trf_filled:\n\n{trf_filled}")

    ref = build_ref(trf_filled)

    template = references_main(vs, ref)
    product_info = description_main(vs, ref)
    description = build_product_section_items(product_info)

    step += 1; progress(step, TOTAL, "Running Features extraction")
    print('-------running features---------')
    #features = features_main(vs, image_urls)
    features = features_tools_main(vs, image_urls, run_audit=True)
    print('features\n', features)
    with open("sheet_6_agent_output.json", "w", encoding="utf-8") as f:
        json.dump(features['Sheets'][4], f, indent=2, ensure_ascii=False)
    print('features\n', features)

    step += 1; progress(step, TOTAL, "Moving device images")
    moved = move_device_images_in_blob(
        image_urls=image_urls,
        connection_string=configs.AZURE_BLOB_CONNECTION_STRING,
        container_name=configs.BLOB_CONTAINER_NAME,
    )
    progress(step, TOTAL, "Device images moved", {"count": len(moved)})

    step += 1; progress(step, TOTAL, "Running sheet 3 and 4")
    run_sheet_3_and_4_agentic(vs=vs)

    step += 1; progress(step, TOTAL, "Post-processing CDR + saving output")
    with open(configs.CDR_PAYLOAD_PATH, "r", encoding="utf-8") as f:
        cdr = json.load(f)
    with open(configs.OUTPUT_JSON_S3, "r", encoding="utf-8") as f:
        s3j = json.load(f)
    with open(configs.OUTPUT_JSON_S4, "r", encoding="utf-8") as f:
        s4j = json.load(f)

    cdr = post_process_cdr(
        cdr=cdr,
        template=template,
        description=description,
        features=features,
        s3j=s3j,
        s4j=s4j
    )
    # container_sas_url = configs.AZURE_BLOB_CONTAINER_SAS_URL

    cdr, count = add_urls_sheet_1_and_6(cdr, configs.AZURE_BLOB_CONTAINER_SAS_URL)
    with open(configs.OUTPUT_CDR_PATH, "w", encoding="utf-8") as f:
        json.dump(cdr, f, indent=2, ensure_ascii=False)

    progress(TOTAL, TOTAL, "Done ✅ Output generated", {"output_file": "cdr_payload_v5_updated.json"})
 
    compiler.fill_excel_from_json(cdr, output_excel_path) 
 
    print("📄 CDR payload successfully post-processed")
    # return cdr_payload
    return cdr

# with open("1614_pta_v1.json", "r", encoding="utf-8") as f:
#     trf_filled = json.load(f)   # <-- dict

# cdr=main3(trf_filled)
# main3("1614_pta_v1.json")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("❌ Usage: python main.py <PROJECT_ID> <INPUT_JSON_FILE>")
        print("Example: python main.py PRJ001 1614_pta_v1.json")
        sys.exit(1)

    project_id = sys.argv[1]
    input_json_path = sys.argv[2]

    if not os.path.exists(input_json_path):
        print(f"❌ Input JSON file not found: {input_json_path}")
        sys.exit(1)

    with open(input_json_path, "r", encoding="utf-8") as f:
        input_json = json.load(f)

    print(f"🚀 Starting pipeline")
    print(f"   Project ID : {project_id}")
    print(f"   Input JSON : {input_json_path}")

    main2(project_id, input_json)
