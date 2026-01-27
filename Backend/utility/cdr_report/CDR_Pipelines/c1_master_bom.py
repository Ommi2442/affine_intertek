import os
import requests
import pandas as pd
from io import BytesIO
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import utility.cdr_report.CDR_Pipelines.configs as configs
from utility.cdr_report.CDR_Pipelines.switch import find_bom_blob_url

# ============================================================
# CONFIG
# ============================================================

CONF_THRESHOLD = 0.6
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

# ============================================================
# XLSX HELPERS
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

def merge_bom_sheets_from_sas_url(bom_sas_url: str) -> pd.DataFrame:
    response = requests.get(bom_sas_url)
    response.raise_for_status()

    xls = pd.ExcelFile(BytesIO(response.content))
    merged_rows = []

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
        return pd.DataFrame(columns=MASTER_BOM_COLUMNS)

    return pd.concat(merged_rows, ignore_index=True)

def structured_bom_confidence(df: pd.DataFrame) -> float:
    score = 0.0

    if "Description" in df and df["Description"].notna().any():
        score += 0.4

    if (
        "Manufacturer Part Number" in df
        and df["Manufacturer Part Number"].notna().any()
    ):
        score += 0.4

    if "QTY" in df and df["QTY"].notna().any():
        score += 0.2

    return score


# ============================================================
# PDF BOM — RAG USING EXISTING VECTOR STORE
# ============================================================

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# SYSTEM_PROMPT = """
# You extract Bill of Materials (BOM) line items from technical text.

# Rules:
# - Use ONLY the provided text
# - Do NOT invent rows
# - Do NOT infer missing values
# - Missing fields must be null
# - Output MUST be valid JSON
# - Return a JSON arrays
# - description only available in columns (description, name, part description) 
# - if "name" and "value" column present, then Description = "name"+"value"
# - U/M only available in columns (U/M, uom)
# - do not use any other columns than those specified, ignore the rest.
# - manufacturer only available in columns (manufacturer, mfg, mfr, Manufacturer/trademark2)
# - manufacturer part number only available in columns (manufacturer part number, mfg p/n, mfr-pn, mpn, Type/model2)
# """

SYSTEM_PROMPT = """
You extract Bill of Materials (BOM) line items from technical text.

Rules:
- Use ONLY the provided text
- Do NOT invent rows
- Do NOT infer missing values
- Missing fields must be null
- Output MUST be valid JSON
- Return a JSON arrays
- description only available in columns (description, name, part description, part) 
- if "name" and "value" column present, then Description = "name"+"value"
- U/M only available in columns (U/M, uom)
- do not use any other columns than those specified, ignore the rest.
- manufacturer only available in columns (manufacturer, mfg, mfr, Manufacturer/trademark2, manuf)
- manufacturer part number only available in columns (manufacturer part number, mfg p/n, mfr-pn, mpn, Type/model2, manuf #)
"""

USER_PROMPT = """
Extract BOM line items from the following context.

Return EXACTLY this schema:

{{
  "Line": string | null,
  "Description": string | null,
  "Manufacturer' : String | null,
  "Manufacturer Part Number": string | null,
  "QTY": string | null,
  "U/M": string | null,
}}

Context:
{CONTEXT}
"""

llm = configs.llm2

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", USER_PROMPT),
])

parser = JsonOutputParser()
rag_chain = prompt | llm


def _retrieve_bom_chunks(pdf_name: str, *, vs) -> list[str]:
    """
    Retrieve BOM-related chunks from the EXISTING vector store.
    """
    docs = vs.similarity_search(
        query="bill of materials part number quantity",
        k=20
    )
    return [d.page_content for d in docs]


import json

def _parse_bom_with_vs(
    *,
    source_url: str,
    source_name: str,
    vs,
) -> pd.DataFrame:
    rows = []

    chunks = _retrieve_bom_chunks(source_name, vs=vs)
    #print(f"{source_name}: retrieved {len(chunks)} chunks")

    for idx, text in enumerate(chunks, start=1):
        try:
            raw = rag_chain.invoke({"CONTEXT": text})
            raw_text = raw.content if hasattr(raw, "content") else raw
            raw_text = raw_text.strip()
            if not raw_text:
                continue

            items = json.loads(raw_text)
        except Exception:
            continue

        if not isinstance(items, list):
            continue

        for it in items:
            if not any(it.values()):
                continue

            rows.append({
                "Line": it.get("Line"),
                "Parent Part Number": None,
                "QTY": it.get("QTY"),
                "U/M": it.get("U/M"),
                "Description": it.get("Description"),
                "Manufacturer": it.get("Manufacturer"),
                "Manufacturer Part Number": it.get("Manufacturer Part Number"),
                "Vendor": None,
                "Vendor Part Number": None,
                "Existing Netsuite Item Number": None,
                "Modified PP Item Number": None,
                "CAT": None,
                "SP": None,
                "Rev": it.get("Rev"),
                "Customer Reference Number": None,
                "sheet_name": source_name,
                "source_doc": source_url,
            })

    return pd.DataFrame(rows, columns=MASTER_BOM_COLUMNS)

def deduplicate_master_bom(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplicate master BOM rows based on:
      - Description
      - Manufacturer
      - Manufacturer Part Number

    Merge provenance fields:
      - sheet_name
      - source_doc
    """

    # Normalize matching keys (defensive)
    df["_desc_norm"] = (
        df["Description"]
        .astype(str)
        .str.strip()
        .str.lower()
    )
    
    df["_mfr_norm"] = (
        df["Manufacturer"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df["_mpn_norm"] = (
        df["Manufacturer Part Number"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # Rows eligible for deduplication
    has_keys = df["_desc_norm"].ne("nan") & df["_mpn_norm"].ne("nan") & df["_mfr_norm"].ne("nan")

    dedupe_df = df[has_keys].copy()
    passthrough_df = df[~has_keys].copy()

    def merge_unique(series):
        vals = (
            series.dropna()
            .astype(str)
            .str.strip()
            .unique()
        )
        return " | ".join(vals)

    agg_map = {
        # Provenance fields → merge
        "sheet_name": merge_unique,
        "source_doc": merge_unique,
    }

    # All other columns → take first non-null
    for col in df.columns:
        if col not in agg_map and col not in ["_desc_norm", "_mfr_norm", "_mpn_norm"]:
            agg_map[col] = "first"

    deduped = (
        dedupe_df
        .groupby(["_desc_norm", "_mfr_norm", "_mpn_norm"], dropna=False)
        .agg(agg_map)
        .reset_index(drop=True)
    )
    
    # Recombine with rows we intentionally skipped
    final_df = pd.concat([deduped, passthrough_df], ignore_index=True)

    # Cleanup
    final_df = final_df.drop(columns=["_desc_norm", "_mfr_norm", "_mpn_norm"], errors="ignore")

    return final_df


# ============================================================
# ORCHESTRATION
# ============================================================

def _process_single_bom_file(f: dict, *, vs) -> pd.DataFrame | None:
    #print(f"Processing BOM: {f['name']}")

    if f["type"] == "xlsx":
        df = merge_bom_sheets_from_sas_url(f["url"])

        confidence = structured_bom_confidence(df)

        if confidence >= CONF_THRESHOLD:
            #print(f"✔ Structured BOM detected ({confidence:.2f}) — using Excel parser")
            return df.reindex(columns=MASTER_BOM_COLUMNS)

        #print("⚠ Low structure confidence — falling back to RAG for XLSX")
        return _parse_bom_with_vs(
            source_url=f["url"],
            source_name=f["name"],
            vs=vs,
        )


    if f["type"] == "pdf":
        return _parse_bom_with_vs(
            source_url=f["url"],
            source_name=f["name"],
            vs=vs,
        )


    return None


def run_master_bom(
    *,
    bom_files: list[dict] | None = None,
    vs,
):
    configs.require_runtime()

    if vs is None:
        raise RuntimeError("Vector store (vs) must be provided to run_master_bom")

    if bom_files is None:
        bom_files = find_bom_blob_url()

    if not bom_files:
        #print("⚠ No BOM files found. Skipping Master BOM.")
        return

    all_dfs: list[pd.DataFrame] = []

    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as executor:
        futures = [
            executor.submit(_process_single_bom_file, f, vs=vs)
            for f in bom_files
        ]

        for future in as_completed(futures):
            try:
                df = future.result()
                if df is not None and not df.empty:
                    all_dfs.append(df)
            except Exception:
                continue

    if not all_dfs:
        #print("⚠ BOM files detected but no rows extracted.")
        return

    master_df = pd.concat(all_dfs, ignore_index=True)
    master_df = master_df.reindex(columns=MASTER_BOM_COLUMNS)

    #print(f"Before dedupe: {len(master_df)} rows")
    master_df = deduplicate_master_bom(master_df)
    #print(f"After dedupe: {len(master_df)} rows")

    master_df.to_excel(configs.MASTER_SHEET_PATH, index=False)

    #print("✅ master_bom.xlsx generated successfully")
