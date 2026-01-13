from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
import utility.cdr_report.CDR_Pipelines.configs as configs
from urllib.parse import quote
import pandas as pd
from io import BytesIO

# ===================== CONFIG =====================

AZURE_CONNECTION_STRING = configs.AZURE_BLOB_CONNECTION_STRING
CONTAINER_NAME = configs.BLOB_CONTAINER_NAME
CONTAINER_SAS_URL = configs.AZURE_BLOB_CONTAINER_SAS_URL


MAX_HEADER_SCAN_ROWS = 15

BOM_COLUMNS = {
    "line",
    "qty",
    "u/m",
    "name",
    "description",
    "manufacturer",
    "manufacturer part number"
}

# ===================== HELPERS =====================

# switch.py

def get_bom_filenames() -> set[str]:
    """
    Returns lowercase filenames of detected BOM blobs.
    Intended for retrieval-time filtering.
    """
    bom_items = find_bom_blob_url()
    return {
        item["name"].lower()
        for item in bom_items
        if item.get("name")
    }


def normalize(text: str) -> str:
    return (
        str(text)
        .strip()
        .lower()
        .replace("_", " ")
    )

def is_bom_excel(excel_bytes: bytes) -> bool:
    try:
        xls = pd.ExcelFile(BytesIO(excel_bytes))

        for sheet in xls.sheet_names:
            df = pd.read_excel(
                xls,
                sheet_name=sheet,
                header=None,
                nrows=MAX_HEADER_SCAN_ROWS,
                dtype=str
            )

            found = {
                normalize(cell)
                for row in df.values
                for cell in row
                if cell and str(cell).strip()
            }

            if len(BOM_COLUMNS & found) >= int(0.28 * len(BOM_COLUMNS)):
                return True

    except Exception:
        pass

    return False

import requests
import pdfplumber
from io import BytesIO

def is_bom_pdf(pdf_url: str) -> bool:
    """
    Decide if a PDF is a BOM using ONLY first-page content.
    """
    try:
        response = requests.get(pdf_url, timeout=15)
        response.raise_for_status()

        with pdfplumber.open(BytesIO(response.content)) as pdf:
            if not pdf.pages:
                return False

            text = (pdf.pages[0].extract_text() or "").lower()

            required_keywords = [
                "bill of materials",
                "assembly description",
                "part number",
                "qty",
            ]

            hits = sum(k in text for k in required_keywords)
            return hits >= 2

    except Exception:
        return False

from concurrent.futures import ThreadPoolExecutor, as_completed

def filter_bom_pdfs(pdf_items: list[dict]) -> list[dict]:
    """
    Concurrently validate PDFs using first-page content.
    Uses MAX_WORKERS from configs.py
    """
    results = []

    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as executor:
        future_map = {
            executor.submit(is_bom_pdf, item["url"]): item
            for item in pdf_items
        }

        for future in as_completed(future_map):
            item = future_map[future]
            try:
                if future.result():
                    results.append(item)
            except Exception:
                # defensive; is_bom_pdf already swallows errors
                continue

    return results

# ===================== CORE FUNCTION =====================

from urllib.parse import quote
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

def find_bom_blob_url() -> list[dict]:

    """
    Locate BOM files (Excel + BOM PDFs only).
    Uses multithreading for PDF validation.
    """
    
    configs.require_runtime()
    project_id = configs.runtime.project_id

    blob_service_client = BlobServiceClient.from_connection_string(
        AZURE_CONNECTION_STRING
    )

    container_client = blob_service_client.get_container_client(
        CONTAINER_NAME
    )

    base_url, sas = CONTAINER_SAS_URL.split("?", 1)

    excel_results: list[dict] = []
    pdf_candidates: list[dict] = []

    # ------------------ DISCOVERY (single-threaded) ------------------
    prefix = f"Documents/{project_id}/source_documents/"

    for blob in container_client.list_blobs(name_starts_with=prefix):

        name = blob.name
        lname = name.lower()

        # ---------- EXCEL ----------
        if lname.endswith((".xlsx", ".xls")):
            blob_client = container_client.get_blob_client(blob.name)

            try:
                excel_bytes = blob_client.download_blob().readall()

                if is_bom_excel(excel_bytes):
                    excel_results.append({
                        "url": f"{base_url}/{quote(name)}?{sas}",
                        "name": name.split("/")[-1],
                        "path": name,
                        "type": "xlsx",
                    })

            except ResourceNotFoundError:
                continue

        # ---------- PDF (candidate only) ----------
        elif lname.endswith(".pdf"):
            pdf_candidates.append({
                "url": f"{base_url}/{quote(name)}?{sas}",
                "name": name.split("/")[-1],
                "path": name,
                "type": "pdf",
            })

    # ------------------ PDF VALIDATION (multi-threaded) ------------------
    bom_pdfs: list[dict] = []

    if pdf_candidates:
        bom_pdfs = filter_bom_pdfs(pdf_candidates)

    return excel_results + bom_pdfs

