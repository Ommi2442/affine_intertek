# ===================== IMPORTS =====================

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
import utility.cdr_report.CDR_Pipelines.configs as configs
from urllib.parse import quote

import pandas as pd
from io import BytesIO
from collections import defaultdict


# ===================== CONFIG =====================

AZURE_CONNECTION_STRING = configs.AZURE_BLOB_CONNECTION_STRING
CONTAINER_NAME = configs.BLOB_CONTAINER_NAME
CONTAINER_SAS_URL = configs.AZURE_BLOB_CONTAINER_SAS_URL

MAX_HEADER_SCAN_ROWS = 15


# ===================== EXCEL BOM DETECTION =====================

BOM_COLUMNS = {
    "line",
    "qty",
    "u/m",
    "name",
    "description",
    "manufacturer",
    "manufacturer part number",
    "mfg",
    "mfr",
    "mpn",
    "mfr-pn",
    "part",
    "manuf",
    "manuf #",
    "quantity",
    "item"

}


def normalize(text: str) -> str:
    return str(text).strip().lower().replace("_", " ")


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

            if len(BOM_COLUMNS & found) >= int(0.16 * len(BOM_COLUMNS)):
                return True

    except Exception:
        pass

    return False


# ===================== PDF HYBRID DETECTION (NEW) =====================

PDF_KEYWORDS = [
    "line",
    "qty",
    "quantity",
    "description",
    "manufacturer",
    "part number",
    "mpn",
    "mfr",
    "u/m",
    "bill of materials",
    "parts list"
]


def is_bom_pdf_by_similarity(
    vs,
    filename: str,
    k: int = 25,
    score_threshold: float = 0.5,
    min_hits: int = 4
) -> bool:
    """
    Lightweight file-level detection.

    If ANY page in the PDF matches:
      similarity + keyword hits
    → treat file as BOM
    """

    query = """
    bill of materials table with columns
    qty quantity description manufacturer
    part number mpn mfr u/m line item
    """

    where = f"c.metadata.source_file = '{filename}'"

    docs_scores = vs.similarity_search_with_score(
        query=query,
        k=k,
        where=where
    )

    for doc, score in docs_scores:

        if score < score_threshold:
            continue

        text = doc.page_content.lower()
        hits = sum(kw in text for kw in PDF_KEYWORDS)

        if hits >= min_hits:
            return True

    return False


# ===================== CORE DISCOVERY =====================

def find_bom_blob_url(*, vs) -> list[dict]:
    """
    Detect ONLY real BOM files.

    Excel → header scan
    PDF   → vector similarity check

    Returns same format as before.
    """

    configs.require_runtime()
    project_id = configs._runtime.project_id

    blob_service_client = BlobServiceClient.from_connection_string(
        AZURE_CONNECTION_STRING
    )

    container_client = blob_service_client.get_container_client(
        CONTAINER_NAME
    )

    base_url, sas = CONTAINER_SAS_URL.split("?", 1)

    results: list[dict] = []

    prefix = f"Documents/{project_id}/source_documents/"

    for blob in container_client.list_blobs(name_starts_with=prefix):

        name = blob.name
        filename = name.split("/")[-1]
        lname = filename.lower()

        # ---------------- EXCEL ----------------
        if lname.endswith((".xlsx", ".xls")):

            blob_client = container_client.get_blob_client(name)

            try:
                excel_bytes = blob_client.download_blob().readall()

                if is_bom_excel(excel_bytes):
                    results.append({
                        "url": f"{base_url}/{quote(name)}?{sas}",
                        "name": filename,
                        "path": name,
                        "type": "xlsx",
                    })

            except ResourceNotFoundError:
                continue

        # ---------------- PDF (NEW similarity detection) ----------------
        elif lname.endswith(".pdf"):

            if is_bom_pdf_by_similarity(vs, filename):
                results.append({
                    "url": f"{base_url}/{quote(name)}?{sas}",
                    "name": filename,
                    "path": name,
                    "type": "pdf",
                })

    return results


# ===================== PIPELINE HELPER =====================

def get_bom_filenames(*, vs) -> set[str]:
    return {
        item["name"].lower()
        for item in find_bom_blob_url(vs=vs)
    }
