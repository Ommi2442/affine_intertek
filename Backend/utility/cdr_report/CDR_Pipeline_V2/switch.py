from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from configs import *
from urllib.parse import quote
import pandas as pd
from io import BytesIO

# ===================== CONFIG =====================

AZURE_CONNECTION_STRING = AZURE_CONN_STRING
CONTAINER_NAME = BLOB_CONTAINER_NAME
CONTAINER_SAS_URL = AZURE_BLOB_CONTAINER_SAS_URL

MAX_HEADER_SCAN_ROWS = 10

BOM_COLUMNS = {
    "line",
    "parent part number",
    "qty",
    "u/m",
    "description",
    "manufacturer",
    "manufacturer part number",
    "vendor",
    "vendor part number",
}

# ===================== HELPERS =====================

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

            if len(BOM_COLUMNS & found) >= int(0.8 * len(BOM_COLUMNS)):
                return True

    except Exception:
        pass

    return False

# ===================== CORE FUNCTION =====================

def find_bom_blob_url() -> str | None:
    """
    Locate BOM Excel by content.
    Return full SAS URL if found, else None.
    """

    blob_service_client = BlobServiceClient.from_connection_string(
        AZURE_CONNECTION_STRING
    )

    container_client = blob_service_client.get_container_client(
        CONTAINER_NAME
    )

    # Split container URL and SAS once
    base_url, sas = CONTAINER_SAS_URL.split("?", 1)

    for blob in container_client.list_blobs():
        name = blob.name.lower()

        if not name.endswith((".xlsx", ".xls")):
            continue

        blob_client = container_client.get_blob_client(blob.name)

        try:
            excel_bytes = blob_client.download_blob().readall()

            if is_bom_excel(excel_bytes):
                encoded_name = quote(blob.name)
                return f"{base_url}/{encoded_name}?{sas}"

        except ResourceNotFoundError:
            continue

    return None
