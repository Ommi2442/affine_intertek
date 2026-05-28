import os
import re
import requests
import pandas as pd
from io import BytesIO
from urllib.parse import urlparse

import camelot

# 🔹 IMPORT YOUR EXISTING FIND LOGIC
from switch import find_bom_blob_url

# ============================================================
# CONFIG
# ============================================================

HEADER_SCAN_ROWS = 15

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

MASTER_BOM_COLUMNS = BOM_COLUMNS + [
    "sheet_name",
    "source_doc",
]

def looks_like_part_number(v: str) -> bool:
    v = v.strip()
    return len(v) >= 4 and any(c.isdigit() for c in v)


PART_NO_RE = re.compile(r"^\d{3}-\d{6}")

# ============================================================
# HELPERS (XLSX)
# ============================================================

def normalize(col: str) -> str:
    return str(col).strip().lower().replace("_", " ")

NORMALIZED_BOM_COLS = {normalize(c): c for c in BOM_COLUMNS}


def detect_header_row(df_preview: pd.DataFrame) -> int | None:
    for i in range(len(df_preview)):
        row = df_preview.iloc[i].dropna().tolist()
        normalized = {normalize(c) for c in row}

        if len(set(NORMALIZED_BOM_COLS) & normalized) >= int(
            0.7 * len(NORMALIZED_BOM_COLS)
        ):
            return i
    return None

import configs as configs

def _process_single_bom_file(f: dict) -> pd.DataFrame | None:
    try:
        print(f"Processing BOM: {f['name']}")

        if f["type"] == "xlsx":
            df = merge_bom_sheets_from_sas_url(f["url"])
            return df.reindex(columns=MASTER_BOM_COLUMNS)

        elif f["type"] == "pdf":
            # ❌ DO NOT thread Camelot on Windows
            return parse_pdf_bom(
                pdf_url=f["url"],
                pdf_name=f["name"]
            )

    except Exception as e:
        print(f"⚠ Failed BOM file: {f['name']} | {e}")
        return None


# ============================================================
# XLSX PARSER (MULTI-SHEET)
# ============================================================

def merge_bom_sheets_from_sas_url(bom_sas_url: str) -> pd.DataFrame:
    response = requests.get(bom_sas_url)
    response.raise_for_status()

    xls = pd.ExcelFile(BytesIO(response.content))
    merged_rows = []

    parsed = urlparse(bom_sas_url)
    file_name = os.path.basename(parsed.path)

    for sheet in xls.sheet_names:
        preview = pd.read_excel(
            xls,
            sheet_name=sheet,
            header=None,
            nrows=HEADER_SCAN_ROWS,
            dtype=str
        )

        header_row = detect_header_row(preview)
        if header_row is None:
            continue

        df = pd.read_excel(
            xls,
            sheet_name=sheet,
            header=header_row,
            dtype=str
        )

        df.columns = [
            NORMALIZED_BOM_COLS.get(normalize(c), c)
            for c in df.columns
        ]

        df = df[[c for c in BOM_COLUMNS if c in df.columns]]
        df = df.dropna(how="all")

        df["sheet_name"] = sheet
        df["source_doc"] = bom_sas_url

        merged_rows.append(df)

    if not merged_rows:
        raise RuntimeError("No valid BOM sheets found")

    return pd.concat(merged_rows, ignore_index=True)

# ============================================================
# PDF PARSER (SHEET-EQUIVALENT)
# ============================================================

def parse_pdf_bom(pdf_url: str, pdf_name: str) -> pd.DataFrame:
    tables = camelot.read_pdf(
        pdf_url,
        pages="all",
        flavor="lattice"
    )

    rows = []

    for table in tables:
        df = table.df
        df.columns = df.iloc[0]
        df = df.iloc[1:]

        for _, r in df.iterrows():
            part_no = str(r.iloc[0]).strip()

            if not looks_like_part_number(part_no):
                continue


            rows.append({
                "Line": None,
                "Parent Part Number": None,
                "QTY": r.get("Qty"),
                "U/M": r.get("UoM"),
                "Description": r.get("Description"),

                "Manufacturer": None,
                "Manufacturer Part Number": r.get("Part Number"),  # ✅ key rule
                "Vendor": None,
                "Vendor Part Number": None,

                "Existing Netsuite Item Number": None,
                "Modified PP Item Number": None,
                "CAT": None,
                "SP": None,
                "Rev": r.get("Rev"),
                "Customer Reference Number": None,

                "sheet_name": pdf_name,
                "source_doc": pdf_url,
            })

    return pd.DataFrame(rows, columns=MASTER_BOM_COLUMNS)

# ============================================================
# MASTER BOM ORCHESTRATOR
# ============================================================

from concurrent.futures import ThreadPoolExecutor, as_completed


def run_master_bom():
    bom_files = find_bom_blob_url()

    if not bom_files:
        raise RuntimeError("No BOM files found")

    # Split by type (CRITICAL for Windows + Camelot)
    xlsx_files = [f for f in bom_files if f["type"] == "xlsx"]
    pdf_files  = [f for f in bom_files if f["type"] == "pdf"]

    all_dfs: list[pd.DataFrame] = []

    # --------------------------------------------------
    # XLSX BOMs → SAFE to multithread
    # --------------------------------------------------
    if xlsx_files:
        with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as executor:
            futures = [
                executor.submit(_process_single_bom_file, f)
                for f in xlsx_files
            ]

            for future in as_completed(futures):
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        all_dfs.append(df)
                except Exception as e:
                    print(f"⚠ XLSX BOM failed: {e}")

    # --------------------------------------------------
    # PDF BOMs → MUST be SERIAL (Camelot + Windows)
    # --------------------------------------------------
    for f in pdf_files:
        try:
            df = _process_single_bom_file(f)
            if df is not None and not df.empty:
                all_dfs.append(df)
        except Exception as e:
            print(f"⚠ PDF BOM failed: {f['name']} | {e}")

    # --------------------------------------------------
    # Finalize
    # --------------------------------------------------
    if not all_dfs:
        print("⚠ BOM files detected but no rows extracted")
        return   # <-- do NOT crash pipeline

    master_df = pd.concat(all_dfs, ignore_index=True)
    master_df = master_df.reindex(columns=MASTER_BOM_COLUMNS)

    master_df.to_excel("master_bom.xlsx", index=False)
    print("✅ master_bom.xlsx generated successfully")
