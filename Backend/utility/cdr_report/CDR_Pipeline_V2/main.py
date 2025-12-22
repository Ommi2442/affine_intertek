# main.py

import os, sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# import os
# import sys
# from pathlib import Path
# BASE_DIR = Path(__file__).resolve().parent
# if str(BASE_DIR) not in sys.path:
#     sys.path.insert(0, str(BASE_DIR))

# Make relative file paths behave as if executed from this folder
# WORKDIR = Path(os.getenv("CDR_WORKDIR", BASE_DIR)).resolve()
# os.chdir(WORKDIR)
# print("Pipeline working dir:", Path.cwd())


from form_utils import build_ref

import os
import json

from editable_processing import extract_cis
from configs import (
    container,
    AZURE_CONN_STRING,
    DB_NAME,
    CONT_NAME,
    cosmos_client
)
from references import references_main
from utils import (
    get_blob_urls,
    process_blob_urls_2,
    download_images_from_blob_urls,
    create_db_and_container,
    build_embeddings,
    build_vectorstore,
    load_and_split_pdfs_text,
    ingest_chunks,

)

from switch import find_bom_blob_url
import c1_main
import c2_main


def run_sheet_3_and_4():
    bom_url = find_bom_blob_url()
    if bom_url:
        c1_main.run_case1_pipeline()
    else:
        c2_main.run_case2_pipeline()

def main():
    conn_str = AZURE_CONN_STRING

    blob_urls = get_blob_urls(conn_str, container)

    extracted_texts, image_urls, downloaded_pdf_paths, converted_pdf_paths = process_blob_urls_2(
        blob_urls, conn_str, container,
        download_dir="src_files", keep_files=True, verbose=True
    )

    image_paths = download_images_from_blob_urls(
        blob_urls,
        conn_str=conn_str,
        container=container,
        download_dir="src_files",
        overwrite=False,
        verbose=True,
    )
    cis_info=extract_cis() 
    extracted_texts += cis_info

    with open("extracted.txt", "w", encoding="utf-8") as f:
        json.dump(extracted_texts, f, indent=4, default=str)

    pdf_files = [
        f for f in os.listdir("src_files")
        if f.lower().endswith(".pdf")
    ]
    pdf_paths = [os.path.join("src_files", f) for f in pdf_files]

    container_obj = create_db_and_container()
    # ✅ use utils.client (created lazily inside create_db_and_container)
    #db = utils.client.get_database_client(DB_NAME)

    db = cosmos_client.get_database_client(DB_NAME)
    print(f"db_created:{db}")
    print("Containers present:")
    for c in db.list_containers():
        print(" -", c["id"])

    embeddings = build_embeddings()
    vs = build_vectorstore(embeddings)
    print(f"vs built:{vs}")
    print("********",os.listdir())
    print("-----",os.getcwd())
    chunks = load_and_split_pdfs_text(pdf_paths, extracted_texts=extracted_texts)
    # embedd
    ingest_chunks(vs, chunks, max_workers=5, batch_size=10)
    # Reading TRF Output json
    os.chdir(r".\utility\cdr_report\CDR_Pipeline_V2")
    print("------------------",os.getcwd())
    print("+++++++++++++++",os.listdir())
    with open("iec_output.json", "r", encoding="utf-8") as f:
        trf_filled = json.load(f)
    print("trf_filled:\n\n{trf_filled}")
    ref=build_ref(trf_filled)
    print(f'\n\n=========\n{ref}')
    template = references_main(vs, ref)
    run_sheet_3_and_4()
if __name__ == "__main__":
    main()
