import os
import requests
import pandas as pd
from io import BytesIO
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import fitz
import base64
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import AzureOpenAI

import utility.cdr_report.CDR_Pipelines.configs as configs
from utility.cdr_report.CDR_Pipelines.switch import find_bom_blob_url






# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#                    COMPONENTS : UTILITIES
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


import re
import numpy as np
from azure.cosmos import CosmosClient, PartitionKey

# ==================== CLIENT INITIALIZATION ====================
openai_client = AzureOpenAI(
    api_key=configs.AZURE_OPENAI_KEY,
    azure_endpoint=configs.AZURE_OPENAI_ENDPOINT,
    api_version=configs.AZURE_OPENAI_API_VERSION
)

cosmos_client = CosmosClient(configs.COSMOS_ENDPOINT, configs.COSMOS_KEY)
cosmos_db = cosmos_client.get_database_client(configs.COSMOS_DB_NAME)
# cosmos_container = cosmos_db.create_container_if_not_exists(
#     id=configs.COSMOS_CONTAINER_NAME,
#     partition_key=PartitionKey(path=configs.PARTITION_KEY)
# )

# Alias for compatibility with original code
client = openai_client


# ==================== PROMPTS ====================
SYSTEM_PROMPT = """
You are a senior electrical safety engineer.
Classify components conservatively.
If uncertain, mark as CRITICAL with lower confidence.
"""

USER_PROMPT = """
Below is a list of components. For EACH item, determine whether it is CRITICAL.

Rules:
1. Required by standard or controlling document
2. Located in safety circuitry
3. Located in hazardous circuitry
4. Encloses or prevents access to hazardous circuitry
5. Used to maintain spacings or segregation
6. Special evaluation performed
7. Relied upon for safe abnormal operation
8. Other hazard may occur if item is changed or deleted


Exlusions from critical : The below listed and related parts are not critical
- fasteners
- adhesives
- accessories


Return STRICT JSON ARRAY in SAME ORDER:

[
  {{
    "row_id": "<row_id>",
    "is_critical": true | false,
    "triggered_rules": [1,4,7],
    "confidence_score": 0.0-1.0,
    "reasoning": "short technical justification"
  }}
]

Components:
{components_json}
"""

# ==================== LOGIC FUNCTIONS ====================
def confidence_level(score):
    score = float(score)
    if score >= 0.8:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"

def visual_confidence_from_distance(d, applicability):
    if applicability == "Direct" and d < 0.30:
        return "Visual support present"
    if applicability == "Indirect" and d < 0.22:
        return "Visual context only"
    return "No visual evidence"

def visual_applicability(component_name, description):
    text = f"{component_name} {description}".lower()

    if any(k in text for k in [
        "enclosure", "housing", "cabinet", "cover", "case",
        "fan", "vent", "ventilation",
        "label", "marking", "nameplate",
        "power inlet", "ac inlet", "connector",
        "earth", "ground", "protective earth"
    ]):
        return "Direct"

    if any(k in text for k in [
        "fuse", "transformer", "power supply",
        "relay", "switch", "terminal"
    ]):
        return "Indirect"

    return "Not applicable"


def safe_json_load(text):
    """
    Extracts first JSON array or object from text safely.
    Returns None if extraction fails.
    """
    if not text or not text.strip():
        return None

    # Remove markdown fences
    text = text.strip()
    text = re.sub(r"^```.*?\n", "", text)
    text = re.sub(r"\n```$", "", text)

    # Try array first
    match = re.search(r"\[\s*{.*}\s*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Try object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None

def cosine_distance(a, b):
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def clean_value(v):
    if pd.isna(v):
        return None
    return v








# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#                    COMPONENTS : MASTER BOM
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



# ============================================================
# CONFIG
# ============================================================

vision_client = AzureOpenAI(
    api_key=configs.AOAI_KEY,
    azure_endpoint=configs.AOAI_ENDPOINT,
    api_version=configs.API_VERSION
)


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

# TEMP_DIR = "temp_images"
# os.makedirs(TEMP_DIR, exist_ok=True)


def render_pages_to_temp_images(pdf_bytes, filename, pages, dpi=200):
    os.makedirs(configs.TEMP_DIR, exist_ok=True)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    saved = []
    total_pages = len(doc)

    for p in sorted(pages):

        idx = p

        if idx < 0 or idx >= total_pages:
            continue

        pix = doc[idx].get_pixmap(dpi=dpi)

        img_path = os.path.join(
            configs.TEMP_DIR,
            f"{filename}_page_{p}.png"
        )

        pix.save(img_path)
        saved.append((p, img_path))

    return saved

def extract_bom_from_image(img_bytes):

    b64 = base64.b64encode(img_bytes).decode()

    prompt = """
Extract BOM table rows from this image.

Return ONLY valid JSON list.
Schema:
[
  {
    "Line": string | null,
    "Description": string | null,
    "Manufacturer": string | null,
    "Manufacturer Part Number": string | null,
    "QTY": string | null,
    "U/M": string | null
  }
]
"""

    response = vision_client.chat.completions.create(
        model=configs.VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }}
            ]
        }],
        temperature=0,
        max_tokens=8000
    )

    raw = response.choices[0].message.content or ""
    s = raw.strip()

    l = s.find("[")
    r = s.rfind("]")

    if l == -1 or r == -1:
        return []

    return json.loads(s[l:r+1])


MAX_RETRIES = 6


def safe_extract_with_retry(img_path):
    
    for attempt in range(MAX_RETRIES):
        try:
            with open(img_path, "rb") as f:
                return extract_bom_from_image(f.read())

        except Exception:
            time.sleep(min(2 ** attempt, 15))

    return []

# ============================================================
# PDF BOM — RAG USING EXISTING VECTOR STORE
# ============================================================

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

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

from urllib.parse import unquote
from os.path import basename

def normalize(name: str) -> str:
    """
    Normalize filenames for reliable matching across:
    - URLs (%20 etc.)
    - Different casing
    - Extra spaces
    """
    if not name:
        return ""
    return unquote(str(name)).strip().lower()

def _retrieve_bom_chunks(source_name: str, vs):
    print(f"Inside Excel_chunk before normalize {source_name}")
    bom_name = unquote(str(basename(source_name))).strip()
    print(f"Inside Excel_chunk after normalize {bom_name}")
    where = f"c.metadata.source_file = '{bom_name}'"
    query = """
    bill of materials table with columns
    qty quantity description manufacturer
    part number mpn mfr u/m line item
    """
    docs = vs.similarity_search(query=query, k=20, where=where)
    for d in docs:
        print(f"{source_name} -> File:{bom_name} -> Metadata:{d.metadata.get('source_file')}")

    return docs




import json

def _parse_bom_with_vs(
    *,
    source_url: str,
    source_name: str,
    vs,
) -> pd.DataFrame:
    rows = []

    chunks = _retrieve_bom_chunks(source_name, vs=vs)
    print(f"{source_name}: retrieved {len(chunks)} chunks")

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

def _parse_pdf_with_vision(
    *,
    source_url: str,
    source_name: str,
    vs,
) -> pd.DataFrame:
    """
    New PDF extraction using:
      similarity → pages → images → vision → rows
    """

    # 1️⃣ detect pages via vector search
    where = f"c.metadata.source_file = '{source_name}'"
    query = """
    bill of materials table with columns
    qty quantity description manufacturer
    part number mpn mfr u/m line item
    """
    docs = vs.similarity_search(
        query=query,
        k=25,
        where=where
    )
    for d in docs:
        print(f"{source_name} → page {d.metadata['page']}")
    pages = {d.metadata["page"] for d in docs}
    # print(f"✔ BOM detected in {source_name} page {docs.metadata['page']} ")
    if not pages:
        return pd.DataFrame(columns=MASTER_BOM_COLUMNS)

    # 2️⃣ download PDF once
    response = requests.get(source_url)
    pdf_bytes = response.content

    # 3️⃣ render pages
    images = render_pages_to_temp_images(pdf_bytes, source_name, pages)

    rows = []

    # 4️⃣ parallel vision extraction
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(safe_extract_with_retry, img): page
            for page, img in images
        }

        for future in as_completed(futures):
            page = futures[future]
            items = future.result()

            for it in items:
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
                    "Rev": None,
                    "Customer Reference Number": None,
                    "sheet_name": page + 1,
                    "source_doc": source_name,
                })
            print(f"✅ {source_name} page {page} → {len(rows)} rows")
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
    print(f"Processing BOM: {f['name']}")

    if f["type"] in ["xlsx", "xls"]:
        df = merge_bom_sheets_from_sas_url(f["url"])

        confidence = structured_bom_confidence(df)

        if confidence >= CONF_THRESHOLD:
            print(f"✔ Structured BOM detected ({confidence:.2f}) — using Excel parser")
            return df.reindex(columns=MASTER_BOM_COLUMNS)

        print("⚠ Low structure confidence — falling back to RAG for XLSX")
        return _parse_bom_with_vs(
            source_url=f["url"],
            source_name=f["name"],
            vs=vs,
        )


    if f["type"] == "pdf":
        return _parse_pdf_with_vision(
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
        bom_files = find_bom_blob_url(vs=vs)

    if not bom_files:
        print("⚠ No BOM files found. Skipping Master BOM.")
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
        print("⚠ BOM files detected but no rows extracted.")
        return

    master_df = pd.concat(all_dfs, ignore_index=True)
    master_df = master_df.reindex(columns=MASTER_BOM_COLUMNS)

    print(f"Before dedupe: {len(master_df)} rows")
    master_df = deduplicate_master_bom(master_df)
    print(f"After dedupe: {len(master_df)} rows")

    master_df.to_excel(configs.MASTER_SHEET_PATH, index=False)

    print("✅ master_bom.xlsx generated successfully")








# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#             COMPONENTS : EXTRACTION - CLASSIFICATION
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



def classify_in_batches(df, batch_size):
    configs.require_runtime()

    results = []

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size].copy()
        batch["row_id"] = batch.index.astype(str)

        payload = batch.to_dict(orient="records")

        response = client.chat.completions.create(
            model=configs.VISION_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_PROMPT.format(
                        components_json=json.dumps(payload, indent=2)
                    )
                }
            ]
        )

        raw_text = response.choices[0].message.content
        batch_result = safe_json_load(raw_text)

        if batch_result is None:
            #print("⚠️ JSON parse failed, marking batch as LOW confidence")
            for row_id in batch["row_id"]:
                results.append({
                    "row_id": row_id,
                    "is_critical": True,
                    "triggered_rules": [],
                    "confidence_score": 0.3,
                    "reasoning": "LLM response parsing failed"
                })
        else:
            results.extend(batch_result)

    return pd.DataFrame(results)



def run_extraction():
        configs.require_runtime()

        print("Starting Extraction...")
        # Load master sheet

        master_path = configs.MASTER_SHEET_PATH

        # --------------------------------
        # CASE: MASTER BOM DOES NOT EXIST
        # --------------------------------
        if not master_path.exists():
            print("ℹ Master BOM not found. Writing empty extraction output.")
            return
        
        
        master_df = pd.read_excel(configs.MASTER_SHEET_PATH, dtype=str)

        
        # Classify
        results_df = classify_in_batches(master_df, configs.BATCH_SIZE)

        # Rule-count scoring
        results_df["rules_triggered_count"] = results_df["triggered_rules"].apply(
            lambda x: len(x) if isinstance(x, list) else 0
        )
        results_df["rules_triggered_total"] = 8
        results_df["rules_score"] = (
            results_df["rules_triggered_count"] /
            results_df["rules_triggered_total"]
        )

        # Confidence level
        results_df["confidence_level"] = results_df["confidence_score"].apply(confidence_level)

        # Merge back to master
        final_df = master_df.copy()
        results_df["row_id"] = results_df["row_id"].astype(int)
        final_df = final_df.join(results_df.set_index("row_id"), how="left")

        # Export
        final_df.to_excel(configs.OUTPUT_PATH_FINAL, index=False)

        print("✔ Critical component classification complete")
        print(f"✔ Output saved to: {configs.OUTPUT_PATH_FINAL}")





# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#               COMPONENTS : DEVICE PHOTOS TAGGING
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


from concurrent.futures import ThreadPoolExecutor
from azure.storage.blob import BlobServiceClient

from urllib.parse import quote

# ===================== INTERNAL UTILS =====================

def embed_text(text):
    """
    Generates embedding for a single text string.
    Returns None if text is empty or error occurs.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return None

    try:
        return openai_client.embeddings.create(
            model=configs.EMBED_MODEL,
            input=text
        ).data[0].embedding
    except Exception as e:
        #print(f"⚠ Embedding failed: {e}")
        return None




def get_image_urls_from_container_sas():
    configs.require_runtime()
    project_id = configs._runtime.project_id

    device_prefix = f"Documents/{project_id}/source_documents/device_images/"

    blob_service = BlobServiceClient.from_connection_string(
        configs.AZURE_BLOB_CONNECTION_STRING
    )
    container_client = blob_service.get_container_client(
        configs.BLOB_CONTAINER_NAME
    )

    blob_urls = []

    for blob in container_client.list_blobs(name_starts_with=device_prefix):
        blob_client = container_client.get_blob_client(blob.name)
        blob_urls.append(blob_client.url)   # ✅ SAFE, SDK-built URL

    #print("Blobs found in device_images:", len(blob_urls))
    return blob_urls

def describe_image(image_url):
    try:
        response = openai_client.chat.completions.create(
            model=configs.VISION_MODEL,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an electrical safety engineer. "
                        "Describe the image factually. Do not guess."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                    "Respond ONLY in JSON.\n\n"
                                    "Rules for view_description:\n"
                                    "- MAX 10 words\n"
                                    "- One short sentence fragment\n"
                                    "- Describe ONLY view/angle/type\n"
                                    "- NO explanations\n\n"
                                    "{"
                                    "\"view_description\":\"\",\n"
                                    "\"image_type\":\"exterior|interior|partial|schematic\",\n"
                                    "\"visible_elements\":\"\""
                                    "}"
                                )

                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        }
                    ]
                }
            ]
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removesuffix("```").strip()
        return json.loads(raw)

    except Exception as e:
        #print(f"⚠ Image not readable by Vision ({image_url}): {e}")
        return None

def extract_visible_elements(description):
    if not description or "VISIBLE ELEMENTS:" not in description:
        return ""
    visible = description.split("VISIBLE ELEMENTS:")[1]
    if "NOT VISIBLE" in visible:
        visible = visible.split("NOT VISIBLE")[0]
    return visible.strip()

# ===================== OPTIMIZED MATCHING LOGIC =====================

def calculate_cosine_distances_matrix(comp_embeddings, img_embeddings):
    """
    Computes cosine distance matrix between components (C) and images (I).
    Output shape: (C, I)
    Formula: 1 - (A . B) / (|A|*|B|)
    """
    # Convert to numpy arrays
    A = np.array(comp_embeddings) # Shape: (C, D)
    B = np.array(img_embeddings)  # Shape: (I, D)

    # Normalize vectors
    norm_A = np.linalg.norm(A, axis=1, keepdims=True)
    norm_B = np.linalg.norm(B, axis=1, keepdims=True)

    # Avoid division by zero
    norm_A[norm_A == 0] = 1e-9
    norm_B[norm_B == 0] = 1e-9

    # Cosine Similarity
    similarity = np.dot(A, B.T) / (norm_A @ norm_B.T)

    # Cosine Distance
    return 1 - similarity



# ===================== PHOTO-TAGGING =====================

def run_phototagging():
    
    configs.require_runtime()

    print("Starting Phototagging (Optimized)...")

    final_input_path = configs.OUTPUT_PATH_FINAL

    # --------------------------------
    # CASE 1: INPUT FILE DOES NOT EXIST
    # --------------------------------
    if not final_input_path.exists():
        print("ℹ No extraction output found. Skipping phototagging.")
        return

    df_all = pd.read_excel(final_input_path, dtype=str)

    # --------------------------------
    # CASE 2: FILE EXISTS BUT EMPTY
    # --------------------------------
    if df_all.empty:
        print("ℹ Extraction output is empty. Skipping phototagging.")
        return

    # --------------------------------
    # CASE 3: REQUIRED COLUMN MISSING
    # --------------------------------
    if "is_critical" not in df_all.columns:
        print("⚠ 'is_critical' column missing. Skipping phototagging.")
        return
    

    # STEP 0: LOAD ORIGINAL & FILTER CRITICAL

    df_all["is_critical_norm"] = (
        df_all["is_critical"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    critical_df = df_all.loc[
        df_all["is_critical_norm"].isin(["true", "1", "yes", "y"])
    ].copy()

    print("===== FILTER CHECK =====")
    print("Total rows in original file :", len(df_all))
    print("Critical rows selected      :", len(critical_df))

    if critical_df.empty:
        print("No critical components found.")
        return

    critical_df.to_excel(configs.CRITICAL_ONLY_EXCEL, index=False)

    # STEP 1: RELOAD CRITICAL-ONLY FILE
    df = pd.read_excel(configs.CRITICAL_ONLY_EXCEL, dtype=str)
    print("Working rows (critical only):", len(df))

    # STEP 2: IMAGE DISCOVERY + DESCRIPTION (PARALLEL)
    image_urls = get_image_urls_from_container_sas()
    print(f"Image URLs supplied: {len(image_urls)}")
    # SAVE ALL IMAGE URLS FOR FORMATTER
    pd.Series(image_urls, name="image_url").to_csv(
        configs.ALL_IMAGE_URLS_CSV,
        index=False
    )

    has_images = len(image_urls) > 0


    print("...Generating Image Descriptions (Parallel)...")
    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as exe:
        image_meta = list(exe.map(describe_image, image_urls))

    valid_items = []
    for url, meta in zip(image_urls, image_meta):
        if meta:
            valid_items.append({
                "url": url,
                "view": meta.get("view_description"),
                "type": meta.get("image_type"),
                "visible": meta.get("visible_elements")
            })

    print(f"Images successfully described: {len(valid_items)}")


    # STEP 3: IMAGE EMBEDDINGS (PARALLEL)
    print("...Generating Image Embeddings (Parallel)...")
    visible_texts = [item["visible"] for item in valid_items]

    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as exe:
        valid_img_embeddings = list(exe.map(embed_text, visible_texts))

    image_items = []
    for item, emb in zip(valid_items, valid_img_embeddings):
        if emb is not None:
            image_items.append({
                "url": item["url"],
                "embedding": emb,
                "caption": f'{item["view"]} ({item["type"]})'
            })

    print(f"Images with usable embeddings: {len(image_items)}")


    # STEP 4: COMPONENT EMBEDDINGS (ONLY IF IMAGES EXIST)
    if has_images:
        print("...Generating Component Embeddings (Parallel)...")

        df["component_text"] = df.apply(
            lambda r: f"{r.get('Component Name','')} {r.get('Description','')}",
            axis=1
        )

        with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as exe:
            comp_embeddings = list(exe.map(embed_text, df["component_text"].tolist()))

        df["embedding"] = comp_embeddings
        print(f"Component embeddings created: {len(df)}")

    else:
        print("⚠ No images found — skipping component embeddings")
        df["embedding"] = None


# STEP 5: MATCHING + JUSTIFICATION (VECTORIZED)
    print("...Calculating Matches...")

    results = []

    # ===============================
    # FAST PATH: NO IMAGES AVAILABLE
    # ===============================
    if not image_items:
        print("⚠ No images available — pushing all components forward")

        for _, row in df.iterrows():
            name = row.get("Component Name", "")
            desc = row.get("Description", "")
            applicability = visual_applicability(name, desc)

            results.append({
                "visual_applicability": applicability,
                "found_in_images": False,
                "image_url": None,
                "image_caption": None,
                "visual_confidence": "No visual evidence",
                "visual_basis": "No product images available in device_images container"
            })

    else:
        # =================================
        # NORMAL PATH: IMAGES ARE AVAILABLE
        # =================================

        # Pre-calculate matrix if we have images
        img_vecs = [item["embedding"] for item in image_items]

        # Filter rows that have valid embeddings
        valid_rows_mask = df["embedding"].notna()
        valid_comp_vecs = df.loc[valid_rows_mask, "embedding"].tolist()

        dist_matrix = None
        if valid_comp_vecs:
            dist_matrix = calculate_cosine_distances_matrix(valid_comp_vecs, img_vecs)

        # Counter for matrix indexing
        valid_row_idx = 0

        for _, row in df.iterrows():
            name = row.get("Component Name", "")
            desc = row.get("Description", "")
            applicability = visual_applicability(name, desc)
            comp_emb = row["embedding"]

            res = {
                "visual_applicability": applicability,
                "found_in_images": False,
                "image_url": None,
                "image_caption": None,
                "visual_confidence": "No visual evidence",
                "visual_basis": ""
            }

            # Case A: Not Applicable
            if applicability == "Not applicable":
                res["visual_basis"] = (
                    "Component is internal/electronic and not visually verifiable from product images"
                )
                results.append(res)
                if comp_emb is not None:
                    valid_row_idx += 1
                continue

            # Case B: Missing Component Embedding
            if comp_emb is None or dist_matrix is None:
                res["visual_basis"] = "Component text could not be embedded"
                results.append(res)
                continue

            # Case C: Perform Match
            distances = dist_matrix[valid_row_idx]
            valid_row_idx += 1

            best_idx = np.argmin(distances)
            best_dist = distances[best_idx]
            best_image = image_items[best_idx]

            confidence = visual_confidence_from_distance(best_dist, applicability)

            if confidence == "No visual evidence":
                res["visual_basis"] = (
                    "Visible elements in product images do not clearly correspond to this component"
                )
            else:
                res["found_in_images"] = True
                res["image_url"] = best_image["url"]
                res["image_caption"] = best_image["caption"]
                res["visual_confidence"] = confidence
                res["visual_basis"] = (
                    "Visible elements in product images provide support relevant to the component’s safety role"
                )

            results.append(res)

    # Attach results
    df = pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)


    # STEP 6: EXPORT FINAL OUTPUT
    df.to_excel(configs.FINAL_OUTPUT_WITH_EVIDENCE, index=False)
    print(f"✔ Completed. Output: {configs.FINAL_OUTPUT_WITH_EVIDENCE}")





# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#                    COMPONENTS : FORMATTING
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



# ===================== HELPER FOR METADATA =====================
def build_field_text(photo_no, image_reason):
    if image_reason:
        short = image_reason.split(".")[0].strip().lower()
        return f"Photo {photo_no} - {short}"
    return f"Photo {photo_no}"

import os
from urllib.parse import urlparse, unquote

def image_name_no_ext(url):
    filename = os.path.basename(unquote(urlparse(url).path))
    return os.path.splitext(filename)[0]


def build_text_support_list(sheet_name, source_doc):
    """
    Builds a list of text_support dicts.
    - page comes from sheet_name
    - filename is extracted from the URL
    - Handles pipe-separated sheet names and URLs
    """

    def split(v):
        if not v:
            return []
        return [x.strip() for x in str(v).split("|")]

    def filename_from_url(url):
        if not url:
            return None
        path = unquote(urlparse(url).path)
        return os.path.basename(path)

    pages = split(sheet_name)
    urls = split(source_doc)

    max_len = max(len(pages), len(urls))

    supports = []

    for i in range(max_len):
        page = pages[i] if i < len(pages) else None
        url = urls[i] if i < len(urls) else None

        supports.append({
            "filename": filename_from_url(url),
            "page": page,               # sheet name only
            "similarity_score": None,
            "preview_text": None,
            "url": url
        })

    return supports 




NULL_COMPONENT_ITEM = {
    "start_cell": "A3",
    "row_type": "table_data",
    "photo_no": None,
    "item_no": None,
    "name": None,
    "manufacturer": None,
    "type_model": None,
    "technical_data": None,
    "marks_of_conf": None,
    "field_merged": False,
    "fm_range": None,
    "value_merged": False,
    "vm_range": None,
    "task_type": "extraction",
    "user_editable": True,
    "ai_fillable": True,
    "accuracy_level": False,
    "image_support": None,
    "text_support": [
        {
            "filename": None,
            "page": None,
            "similarity_score": None,
            "preview_text": None,
            "url": None
        }
    ],
    "confidence": 0
}


NULL_PHOTO_META_ITEM = {
    "question_cell": "A3",
    "prefix": "Product",
    "field": None,
    "answer_cell": "A4",
    "photo_path": None,
    "field_merged": False,
    "fm_range": None,
    "value_merged": False,
    "vm_range": None,
    "task_type": "photo",
    "user_editable": True,
    "ai_fillable": True,
    "accuracy_level": False
}


def run_formatter():

    configs.require_runtime()

    print("Starting Formatting...")

    final_path = configs.FINAL_OUTPUT_WITH_EVIDENCE

    # --------------------------------
    # CASE: INPUT FILE NOT PRESENT
    # --------------------------------
    if not final_path.exists():
        print("ℹ Final phototagging output not found. Writing NULL JSONs.")

        with open(configs.OUTPUT_JSON_COMPONENTS, "w", encoding="utf-8") as f:
            json.dump({"Items": [NULL_COMPONENT_ITEM]}, f, indent=4)

        with open(configs.OUTPUT_JSON_METADATA, "w", encoding="utf-8") as f:
            json.dump({"Items": [NULL_PHOTO_META_ITEM]}, f, indent=4)

        return
    
    # ===================== PART 1: COMPONENT JSON =====================
    START_ROW = 3
    START_COLUMN = "A"

    df = pd.read_excel(configs.FINAL_OUTPUT_WITH_EVIDENCE, dtype=str)

    df["found_norm"] = (
        df["found_in_images"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    matched_mask = df["found_norm"].isin(["true", "1", "yes", "y"])

    matched_df   = df[matched_mask].copy()
    unmatched_df = df[~matched_mask].copy()


    # print("Total rows in sheet           :", len(df))
    # print("Rows with image match (true) :", len(matched_df))

    if matched_df.empty:
        print("⚠ No image matches found — marking all components as Not Shown")


    # Assign Photo Numbers
    photo_map = {}
    photo_counter = 1

    def assign_photo_no(url):
        nonlocal photo_counter
        if url not in photo_map:
            photo_map[url] = photo_counter
            photo_counter += 1
        return photo_map[url]

    matched_df["photo_no"] = matched_df["image_url"].apply(assign_photo_no)
    # print("Unique photos detected:", len(photo_map))
    unmatched_df["photo_no"] = "Not Shown"


    # Sort
    matched_df = matched_df.sort_values(
        by=["photo_no", "Description"],
        ascending=[True, True]
    ).reset_index(drop=True)

    final_df = pd.concat(
    [matched_df, unmatched_df],
    ignore_index=True
)

    # print("Rows sorted by photo number")

    # Persist photo_no back to Excel
    final_df.to_excel(configs.FINAL_OUTPUT_WITH_EVIDENCE, index=False)
    # print("✔ photo_no persisted to Excel for all rows")


    # Build Items
    items = []
    current_row = START_ROW

    for idx, row in final_df.iterrows():
        item_no = idx + 1
        start_cell = f"{START_COLUMN}{current_row}"

        item = {
            "start_cell": start_cell,
            "row_type": "table_data",
            "photo_no": str(row["photo_no"]),
            "item_no": str(item_no),
            "name": clean_value(row.get("Description")),
            "manufacturer": clean_value(row.get("Manufacturer")),
            "type_model": clean_value(row.get("Manufacturer Part Number")),
            "technical_data": None,
            "marks_of_conf": None,
            "field_merged": False,
            "fm_range": None,
            "value_merged": False,
            "vm_range": None,
            "task_type": "extraction",
            "user_editable": True,
            "ai_fillable": True,
            "accuracy_level": True,
            "image_support": (
                                clean_value(row.get("image_url"))
                                if row["photo_no"] != "Not Shown"
                                else None
                            ),

            "text_support": build_text_support_list(
                                                        clean_value(row.get("sheet_name")),
                                                        clean_value(row.get("source_doc"))
                                                    ),

            "confidence": int(float(clean_value(row.get("confidence_score")) or 0) * 100)
        }

        items.append(item)
        current_row += 1

    output = {"Items": items}

    with open(configs.OUTPUT_JSON_COMPONENTS, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)

    # print("✔ Component JSON created successfully")
    # print("✔ Output file:", configs.OUTPUT_JSON_COMPONENTS)

    # ===================== PART 2: PHOTO METADATA JSON =====================
    ROW_GAP = 8

    # Reload to ensure we have the photo_no column we just saved
    # (Though we can use matched_df, logic in notebook reloads or uses similar logic)
    # We will use matched_df since it's already in memory and sorted/numbered.

    # Unique photos (No regeneration)
    photo_df = (
        matched_df
        .sort_values("photo_no")
        .drop_duplicates(subset=["photo_no"])
        .reset_index(drop=True)
    )
    
    # ---------------- FIND UNMATCHED IMAGES ----------------

    used_images = set(matched_df["image_url"].dropna())

    all_images = set(
        pd.read_csv(configs.ALL_IMAGE_URLS_CSV)["image_url"]
    )

    remaining_images = all_images - used_images

    items_meta = []
    current_row_meta = START_ROW

    for _, row in photo_df.iterrows():
        question_cell = f"{START_COLUMN}{current_row_meta}"
        answer_cell = f"{START_COLUMN}{current_row_meta + 1}"

        item = {
            "question_cell": question_cell,
            "prefix": "Product",
            "field": build_field_text(
                clean_value(row["photo_no"]),
                clean_value(row.get("image_caption"))
            ),
            "answer_cell": answer_cell,
            "photo_path": clean_value(row.get("image_url")),
            "field_merged": False,
            "fm_range": None,
            "value_merged": False,
            "vm_range": None,
            "task_type": "photo",
            "user_editable": True,
            "ai_fillable": True,
            "accuracy_level": False
        }

        items_meta.append(item)
        current_row_meta += ROW_GAP


    # Continue photo numbering after matched photos
    max_photo_no = (matched_df["photo_no"].dropna().astype(float).max())
    max_photo_no = int(max_photo_no) if pd.notna(max_photo_no) else 0
    next_photo_no = max_photo_no + 1


    # ---------------- ADD UNMATCHED IMAGES ----------------

    for img_url in sorted(remaining_images):
        question_cell = f"{START_COLUMN}{current_row_meta}"
        answer_cell = f"{START_COLUMN}{current_row_meta + 1}"

        items_meta.append({
            "question_cell": question_cell,
            "prefix": "Product",
            "field": build_field_text(
                next_photo_no,
                image_name_no_ext(img_url)  # used as caption-like text
            ),
            "answer_cell": answer_cell,
            "photo_path": img_url,
            "field_merged": False,
            "fm_range": None,
            "value_merged": False,
            "vm_range": None,
            "task_type": "photo",
            "user_editable": True,
            "ai_fillable": True,
            "accuracy_level": False
        })

        next_photo_no += 1
        current_row_meta += ROW_GAP




    with open(configs.OUTPUT_JSON_METADATA, "w", encoding="utf-8") as f:
        json.dump({"Items": items_meta}, f, indent=4)

    # print("✔ Photo metadata JSON created")
    # print("✔ Output file:", configs.OUTPUT_JSON_METADATA) 




# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#              COMPONENTS : ORCHESTRACTION - CASE 1
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


def run_case1_pipeline(*, vs):
    configs.require_runtime()


    #print("Step 1 : Creating Master BOM . . .")
    run_master_bom(vs=vs)
    
    #print("Step 2 : Extracting . . .")
    run_extraction()
    
    #print("Step 3 : Tagging Photos . . .")
    run_phototagging()
    
    #print("Step 4 : Formatting JSON . . .")
    run_formatter()
