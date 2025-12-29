import pandas as pd
from io import BytesIO
from urllib.parse import urlparse, parse_qs
import requests
from switch import find_bom_blob_url

# ===================== CONFIG =====================

BOM_COLUMNS = [
    "Line",
    "Parent Part Number",
    "QTY",
    "U/M",
    "Description",
    "Manufacturer",
    "Manufacturer Part Number",
    "Vendor",
    "Vendor Part Number",
    "Existing Netsuite Item Number",
    "Modified PP Item Number",
    "CAT",
    "SP",
    "Rev",
    "Customer Reference Number",
]

HEADER_SCAN_ROWS = 15




# ===================== HELPERS =====================

def normalize(col: str) -> str:
    return (
        str(col)
        .strip()
        .lower()
        .replace("_", " ")
    )

NORMALIZED_BOM_COLS = {normalize(c): c for c in BOM_COLUMNS}


def detect_header_row(df_preview: pd.DataFrame) -> int | None:
    """
    Identify header row index based on BOM column match.
    """
    for i in range(len(df_preview)):
        row = df_preview.iloc[i].dropna().tolist()
        normalized = {normalize(c) for c in row}

        if len(set(NORMALIZED_BOM_COLS) & normalized) >= int(
            0.7 * len(NORMALIZED_BOM_COLS)
        ):
            return i

    return None


# ===================== CORE FUNCTION =====================

def merge_bom_sheets_from_sas_url(bom_sas_url: str) -> pd.DataFrame:
    """
    Read BOM Excel from SAS URL, merge all sheets into one DataFrame.
    Adds source_sheet column.
    """

    # Download BOM
    response = requests.get(bom_sas_url)
    response.raise_for_status()
    excel_bytes = response.content

    xls = pd.ExcelFile(BytesIO(excel_bytes))
    merged_rows = []

    for sheet in xls.sheet_names:
        # Read preview to detect header
        preview = pd.read_excel(
            xls,
            sheet_name=sheet,
            header=None,
            nrows=HEADER_SCAN_ROWS,
            dtype=str
        )

        header_row = detect_header_row(preview)
        if header_row is None:
            continue  # skip non-BOM sheets

        df = pd.read_excel(
            xls,
            sheet_name=sheet,
            header=header_row,
            dtype=str
        )

        # Normalize columns
        df.columns = [
            NORMALIZED_BOM_COLS.get(normalize(c), c)
            for c in df.columns
        ]

        # Keep only known BOM columns (order preserved)
        df = df[[c for c in BOM_COLUMNS if c in df.columns]]

        # Drop empty rows
        df = df.dropna(how="all")

        # Add source sheet reference
        df["source_sheet"] = sheet

        merged_rows.append(df)

    if not merged_rows:
        print("No valid BOM sheets found")
        return

    return pd.concat(merged_rows, ignore_index=True)

# ===================== SAVE MASTER BOM =====================

def save_master_bom(bom_sas_url: str, output_path: str = "master_bom.xlsx"):
    df = merge_bom_sheets_from_sas_url(bom_sas_url)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Master_BOM")

    print(f"Master BOM saved as: {output_path}")


def run_master_bom():
    
    bom_url = find_bom_blob_url()
    save_master_bom(bom_url, "master_bom.xlsx")