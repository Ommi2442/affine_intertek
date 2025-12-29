# main.py

import os
import json

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
from utility.cdr_report.CDR_Pipelines.features import features_main
from utility.cdr_report.CDR_Pipelines.utils import (
    get_blob_urls,
    process_blob_urls_2,
    download_images_from_blob_urls,
    create_db_and_container,
    build_embeddings,
    build_vectorstore,
    load_and_split_pdfs_text,
    ingest_chunks,
)

from utility.cdr_report.CDR_Pipelines.description import (description_main, build_product_section_items)
import utility.cdr_report.CDR_Pipelines.utils
from utility.cdr_report.CDR_Pipelines.switch import find_bom_blob_url
import utility.cdr_report.CDR_Pipelines.c1_main as c1_main
import utility.cdr_report.CDR_Pipelines.c2_main as c2_main
import utility.cdr_report.CDR_Pipelines.configs as configs
#import utility.cdr_report.CDR_Pipelines.description


from utility.cdr_report.CDR_Pipelines.utils import move_device_images_in_blob
from utility.cdr_report.CDR_Pipelines.c2_utils import get_image_urls_from_container_sas
from utility.cdr_report.CDR_Pipelines.utils import get_image_urls_from_container_sas, move_device_images_in_blob
from utility.cdr_report.CDR_Pipelines.utils import delete_folder_if_exists

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

def run_sheet_3_and_4():
    bom_url = find_bom_blob_url()
    if bom_url:
        c1_main.run_case1_pipeline()
    else:
        c2_main.run_case2_pipeline()
        
        
        

def main2(input_json_file,progress_callback=None):
    TOTAL = 14
    step = 0
    # print(os)
    os.chdir(r'.\utility\cdr_report\CDR_Pipelines')
    conn_str = AZURE_CONN_STRING
    
    step += 1; progress(step, TOTAL, "Starting pipeline")

    step += 1; progress(step, TOTAL, "Deleting device_images folder if exists")
    count = delete_folder_if_exists(conn_str, container, "device_images")
    print("Deleted blobs:", count)

    step += 1; progress(step, TOTAL, "Listing blob URLs")
    blob_urls = get_blob_urls(conn_str, container)
    
    step += 1; progress(step, TOTAL, "Processing blobs (extracting text/images/pdfs)")
    extracted_texts, image_urls, downloaded_pdf_paths, converted_pdf_paths = process_blob_urls_2(
        blob_urls, conn_str, container,
        download_dir="src_files", keep_files="true", verbose="true"
    )
    
    step += 1; progress(step, TOTAL, "Downloading images from blobs")
    image_paths = download_images_from_blob_urls(
        blob_urls,
        conn_str=conn_str,
        container=container,
        download_dir="src_files",
        overwrite="false",
        verbose="true",
    )
    
    step += 1; progress(step, TOTAL, "Extracting CIS info")
    cis_info=extract_cis() 
    extracted_texts += cis_info

    step += 1; progress(step, TOTAL, "Saving extracted text")
    with open("extracted.txt", "w", encoding="utf-8") as f:
        json.dump(extracted_texts, f, indent=4, default=str)

    step += 1; progress(step, TOTAL, "Collecting PDF paths")
    pdf_files = [
        f for f in os.listdir("src_files")
        if f.lower().endswith(".pdf")
    ]
    pdf_paths = [os.path.join("src_files", f) for f in pdf_files]
    
    
    step += 1; progress(step, TOTAL, "Creating DB/container (Cosmos)")
    container_obj = create_db_and_container()
    # ✅ use utils.client (created lazily inside create_db_and_container)
    #db = utils.client.get_database_client(DB_NAME)

    db = cosmos_client.get_database_client(DB_NAME)
    print(f"db_created:{db}")
    print("Containers present:")
    for c in db.list_containers():
        print(" -", c["id"])

    step += 1; progress(step, TOTAL, "Building embeddings + vector store")
    embeddings = build_embeddings()
    vs = build_vectorstore(embeddings)
    #print(f"vs built:{vs}")

    step += 1; progress(step, TOTAL, "Chunking + ingesting documents into vector store")
    chunks = load_and_split_pdfs_text(pdf_paths, extracted_texts=extracted_texts)
    # embedd
    ingest_chunks(vs, chunks, max_workers=5, batch_size=10)
    # Reading TRF Output json
    # with open("trf_final_data.json", "r", encoding="utf-8") as f:
    #     trf_filled = json.load(f)

    step += 1; progress(step, TOTAL, "Building TRF ref + generating template/description")
    trf_filled = input_json_file
    print("trf_filled:\n\n{trf_filled}")
    ref=build_ref(trf_filled)
    print(f'\n\n=========\n{ref}')
    template = references_main(vs, ref)
    product_info = description_main(vs, ref)
    description = build_product_section_items(product_info)

    step += 1; progress(step, TOTAL, "Running Features extraction")
    print('-------running features---------')
    features = features_main(vs, image_urls)
    print('features\n', features)
    
    # print("Preprocessing: moving device images...")
    # image_urls = get_image_urls_from_container_sas()
    # moved = move_device_images_in_blob(image_urls=image_urls,connection_string=configs.AZURE_BLOB_CONNECTION_STRING, container_name=configs.BLOB_CONTAINER_NAME)
    # print(f"Device images moved: {len(moved)}")
    
    step += 1; progress(step, TOTAL, "Moving device images")
    print("Preprocessing: moving device images...")
    image_urls = get_image_urls_from_container_sas()
    moved = move_device_images_in_blob(
        image_urls=image_urls,
        connection_string=configs.AZURE_BLOB_CONNECTION_STRING,
        container_name=configs.BLOB_CONTAINER_NAME,
    )
    print(f"Device images moved: {len(moved)}")
    
    
    step += 1; progress(step, TOTAL, "Running sheet 3 and 4")
    run_sheet_3_and_4()

    step += 1; progress(step, TOTAL, "Post-processing CDR + saving output")
    with open("cdr_payload.json", "r", encoding="utf-8") as f:
        cdr = json.load(f)
    with open(configs.OUTPUT_JSON_S3, "r", encoding="utf-8") as f:
        s3j = json.load(f)
    with open(configs.OUTPUT_JSON_S4, "r", encoding="utf-8") as f:
        s4j = json.load(f)

    # ------------------------------------------------------------
    # Post-process
    # ------------------------------------------------------------
    cdr = post_process_cdr(
        cdr=cdr,
        template=template,
        description=description,
        features=features,
        s3j=s3j,
        s4j=s4j
    )

    # ------------------------------------------------------------
    # Save once
    # ------------------------------------------------------------
    with open("cdr_payload_v5_updated.json", "w", encoding="utf-8") as f:
        json.dump(cdr, f, indent=2, ensure_ascii="false")
    print("📄 CDR payload successfully post-processed")
    
    progress(TOTAL, TOTAL, "Done ✅ Output generated", {"output_file": "cdr_payload_v5_updated.json"})

    # return cdr_payload
    return cdr

