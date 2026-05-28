# c2_extractor.py
from openpyxl import Workbook

import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import utility.cdr_report.CDR_Pipelines.configs as configs
import os
from urllib.parse import urlparse

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#                    COMPONENTS : UTILITIES
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

CRITICAL_RULES = [
    {"id": 1, "text": "Required by standard or controlling document"},
    {"id": 2, "text": "Located in safety circuitry"},
    {"id": 3, "text": "Located in hazardous circuitry"},
    {"id": 4, "text": "Encloses or prevents access to hazardous circuitry"},
    {"id": 5, "text": "Used to maintain spacings or segregation of circuits"},
    {"id": 6, "text": "Special evaluation performed"},
    {"id": 7, "text": "Relied upon for safe abnormal operation"},
    {"id": 8, "text": "Other hazard may occur if item is changed or deleted"}
]


# utils.py
import re
from urllib.parse import quote, urlparse
from threading import Lock

from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, PartitionKey
from openai import AzureOpenAI
from docx import Document
from pypdf import PdfReader


# ===================== CLIENTS =====================
def get_openai_client():
    return AzureOpenAI(
        api_key=configs.AZURE_OPENAI_KEY,
        azure_endpoint=configs.AZURE_OPENAI_ENDPOINT,
        api_version=configs.AZURE_OPENAI_API_VERSION
    )



# ===================== TOKEN TRACKING =====================
TOTAL_TOKENS = {
    "prompt": 0,
    "completion": 0,
    "total": 0
}
_token_lock = Lock()

def track_usage(resp):
    if hasattr(resp, "usage") and resp.usage:
        with _token_lock:
            TOTAL_TOKENS["prompt"] += resp.usage.prompt_tokens
            TOTAL_TOKENS["completion"] += resp.usage.completion_tokens
            TOTAL_TOKENS["total"] += resp.usage.total_tokens

# ===================== BLOB & FILE UTILS =====================
def get_image_urls_from_container_sas():
    configs.require_runtime()
    project_id = configs._runtime.project_id

    prefix = f"Documents/{project_id}/source_documents/device_images/"

    blob_service = BlobServiceClient.from_connection_string(
        configs.AZURE_BLOB_CONNECTION_STRING
    )
    container_client = blob_service.get_container_client(
        configs.BLOB_CONTAINER_NAME
    )

    blob_names = sorted([
        blob.name
        for blob in container_client.list_blobs(name_starts_with=prefix)
        if blob.name.lower().endswith((".jpg", ".jpeg", ".png"))
    ])

    
    #print("Blobs found in container:", len(blob_names))
    if not blob_names:
        return []

    base, sas = configs.AZURE_BLOB_CONTAINER_SAS_URL.split("?", 1)
    base = base.rstrip("/")
    
    image_urls = [f"{base}/{quote(blob_name)}?{sas}" for blob_name in blob_names]
    #print("Image URLs constructed:", len(image_urls))
    return image_urls


# from azure.storage.blob import BlobServiceClient
from urllib.parse import quote

def find_user_guide_blob():
    configs.require_runtime()
    project_id = configs._runtime.project_id

    prefix = f"Documents/{project_id}/"

    blob_service = BlobServiceClient.from_connection_string(
        configs.AZURE_BLOB_CONNECTION_STRING
    )
    container_client = blob_service.get_container_client(
        configs.BLOB_CONTAINER_NAME
    )

    all_blobs = [
        blob.name
        for blob in container_client.list_blobs(name_starts_with=prefix)
    ]


    if not all_blobs:
        #print("❌ Container is empty.")
        return None, None

    guide_keywords = ["user", "guide", "manual", "operation", "instruction"]
    candidates = []

    for name in all_blobs:
        name_l = name.lower()
        if not name_l.endswith((".pdf", ".docx")):
            continue
        if any(k in name_l for k in guide_keywords):
            candidates.append(name)

    if not candidates:
        #print("❌ No guide/manual detected.")
        return None, None

    candidates.sort(key=len)
    blob_name = candidates[0]

    # ✅ extract account name safely from SDK
    account_name = blob_service.account_name

    # ✅ normalize SAS
    sas = configs.AZURE_BLOB_CONTAINER_SAS_URL
    if sas and not sas.startswith("?"):
        sas = "?" + sas

    blob_url = (
        f"https://{account_name}.blob.core.windows.net/"
        f"{configs.BLOB_CONTAINER_NAME}/"
        f"{quote(blob_name)}"
    )

    #print("✔ Selected user guide:", blob_name)
    return blob_name, blob_url

 

def build_blob_sas_url(blob_name: str) -> str:
    base, sas = configs.AZURE_BLOB_CONTAINER_SAS_URL.split("?", 1)
    base = base.rstrip("/")
    return f"{base}/{quote(blob_name)}?{sas}"

def download_blob(blob_name: str) -> str:
    os.makedirs(configs.DOWNLOAD_DIR, exist_ok=True)
    local_path = os.path.join(configs.DOWNLOAD_DIR, os.path.basename(blob_name))

    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        return local_path

    blob_service = BlobServiceClient.from_connection_string(configs.AZURE_BLOB_CONNECTION_STRING)
    blob_client = blob_service.get_blob_client(container=configs.BLOB_CONTAINER_NAME, blob=blob_name)
    data = blob_client.download_blob().readall()

    if not data:
        #print(f"Downloaded blob is empty: {blob_name}")
        return

    with open(local_path, "wb") as f:
        f.write(data)
    return local_path

def extract_text_from_file(path: str) -> str:
    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if path.lower().endswith(".docx"):
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    #print("Unsupported guide format")
    return

# ===================== NORMALIZATION =====================
def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r"\b(x\d+|\(\d+\)|\d+)\b", "", name)
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def normalize_image_url(url):
    if not isinstance(url, str) or not url.strip():
        return None
    parsed = urlparse(url.strip())
    return parsed.path.lower().strip()

def clean_value(v):
    import pandas as pd
    if pd.isna(v) or v == "":
        return None
    return v




# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#                    COMPONENTS : EXTRACTION
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
openai_client = get_openai_client()

COLUMNS = [
        "Component Name",
        "Category",
        "Confidence",
        "Source Type",
        "URL",
        "Filename",
        "Page Number",
        "Guide Reference",
        "Evidence"
    ]

# ------------------------------------------------------------
# IMAGE COMPONENT EXTRACTION
# ------------------------------------------------------------
def _process_single_image(img_url):
    comps = []
    image_meta = None

    try:
        response = openai_client.chat.completions.create(
            model=configs.VISION_MODEL,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an electrical engineer.\n"
                        "Identify the image view and type.\n"
                        "Then list ALL clearly visible components.\n"
                        "Do NOT guess hidden internals.\n"
                        "Use generic component names only."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Respond ONLY in JSON:\n"
                                "{"
                                "\"view_description\":\"\","
                                "\"image_type\":\"photo|schematic|diagram|label\","
                                "\"components\":["
                                "{\"name\":\"\",\"category\":\"\",\"description\":\"\"}"
                                "]}"
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": img_url}
                        }
                    ]
                }
            ]
        )

        track_usage(response)

        raw = response.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removesuffix("```").strip()
        result = json.loads(raw)

        image_meta = {
            "image_url": img_url,
            "view_description": result.get("view_description"),
            "image_type": result.get("image_type")
        }

        for it in result.get("components", []):
            
            filename = os.path.basename(urlparse(img_url).path)

            comps.append({
                "component_name": it.get("name"),
                "component_category": it.get("category", "unknown"),
                "sources": [{
                    "source_type": "image",
                    "source_ref": img_url,
                    "filename": filename,
                    "page_number": None,
                    "chunk": None,
                    "evidence": it.get("description", ""),
                    "view": image_meta["view_description"]
                }],
                "confidence": 80
            })


    except Exception as e:
        print("⚠ Image failed:", img_url, e)
        print("--------------------------------------------------------------------------")
    return image_meta, comps


def extract_components_from_images(image_urls):
    if not image_urls:
        return [], []

    all_components = []
    image_captions = []

    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as exe:
        futures = [exe.submit(_process_single_image, u) for u in image_urls]

        for f in as_completed(futures):
            meta, comps = f.result()
            if meta:
                image_captions.append(meta)
            all_components.extend(comps)

    return image_captions, all_components


# ------------------------------------------------------------
# GUIDE COMPONENT EXTRACTION
# ------------------------------------------------------------
from urllib.parse import urlparse
import os


def _process_guide_chunk(chunk, guide_filename, guide_url, page_no):
    comps = []
    try:
        response = openai_client.chat.completions.create(
            model=configs.VISION_MODEL,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert certification engineer.\n"
                        "Follow the user manual to get context of product/device."
                        "Extract ATLEAST 15 OR MORE physical/electrical components supported by the text.\n"
                        "Each component MUST be supported by the text."
                        "the product/device itself (which is being refered to in the guide/manual) is NOT a component."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "Respond ONLY in JSON array:\n"
                        "[{\"name\":\"\",\"category\":\"\",\"reason\":\"\"}]\n\n"
                        f"{chunk}"
                    )
                }
            ]
        )

        track_usage(response)
        items = json.loads(response.choices[0].message.content)

        for it in items:
            comps.append({
                "component_name": it.get("name"),
                "component_category": it.get("category", "unknown"),
                "sources": [{
                    "source_type": "guide",
                    "source_ref": guide_url,
                    "filename": guide_filename,
                    "page_number": page_no,
                    "chunk": chunk.strip(),
                    "evidence": it.get("reason", "")
                }],
                "confidence": 60

            })

    except Exception:
        pass

    return comps



def extract_components_from_guide(guide_text, guide_filename, guide_url):
    if not guide_text or not guide_text.strip():
        return []

    # Split pages first
    pages = guide_text.split("\f")

    components = []

    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as exe:
        futures = []

        for page_no, page_text in enumerate(pages, start=1):
            # chunk per page (keep page number accurate)
            chunks = [page_text[i:i+2000] for i in range(0, len(page_text), 2000)]
            chunks = chunks[:3]  # safety cap

            for ch in chunks:
                futures.append(
                    exe.submit(
                        _process_guide_chunk,
                        ch,
                        guide_filename,
                        guide_url,
                        page_no
                    )
                )

        for f in as_completed(futures):
            components.extend(f.result())

    return components


# ------------------------------------------------------------
# MERGE LOGIC
# ------------------------------------------------------------
def merge_components(image_components, guide_components):
    merged = {}

    def key(name):
        return (name or "").lower().replace(" ", "").replace("-", "")

    for comp in image_components + guide_components:
        k = key(comp["component_name"])
        if not k:
            continue

        if k not in merged:
            merged[k] = comp
        else:
            # merge sources
            merged[k]["sources"].extend(comp["sources"])

            # upgrade confidence if multiple sources
            merged[k]["confidence"] = max(
                merged[k]["confidence"],
                comp["confidence"],
                95  # image + guide → very high
            )

    return list(merged.values())




import re

ILLEGAL_XML_CHARS = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F]"
)

def sanitize_excel_text(value):
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    return ILLEGAL_XML_CHARS.sub("", value)
 

def run_extractor():
    configs.require_runtime()

    # print("--- Starting Pipeline ---")

    # 1. DISCOVERY
    image_urls = get_image_urls_from_container_sas()

    guide_blob_name, guide_url = find_user_guide_blob()
    guide_text=""
    guide_components = []

    if guide_blob_name:
        guide_filename = guide_blob_name.split("/")[-1]
        guide_local_path = download_blob(guide_blob_name)
        guide_text = extract_text_from_file(guide_local_path)

        print(f"Guide text length: {len(guide_text)}")

        guide_components = extract_components_from_guide(
            guide_text,
            guide_filename,
            guide_url
        )
    else:
        print("⚠ No guide found, continuing without guide components")

    print(f"Guide text length: {len(guide_text)}")

    # 2. EXTRACTION
    print("\n--- Extracting Components ---")

    image_captions, image_components = extract_components_from_images(image_urls)

    combined_components = merge_components(image_components, guide_components)

    print(f"Image comps: {len(image_components)}, Guide comps: {len(guide_components)}")
    print(f"Combined unique: {len(combined_components)}")

    # 3. BUILD IMAGE CAPTION LOOKUP
    image_caption_map = {
        c["image_url"]: f'{c["view_description"]} ({c["image_type"]})'
        for c in image_captions
        if c.get("view_description")
    }

    # 4. SAVE COMBINED OUTPUT
    rows = []

    for c in combined_components:
        for s in c["sources"]:
            
            rows.append({
                "Component Name": sanitize_excel_text(c["component_name"]),
                "Category": sanitize_excel_text(c["component_category"]),
                "Confidence": c["confidence"],

                "Source Type": s["source_type"],
                "URL": sanitize_excel_text(s["source_ref"]),
                "Filename": sanitize_excel_text(s.get("filename")),
                "Page Number": s.get("page_number"),

                "Guide Reference": sanitize_excel_text(
                    s.get("chunk") if s["source_type"] == "guide" else None
                ),

                "Evidence": sanitize_excel_text(s.get("evidence")),
            })
 

    df_raw = pd.DataFrame(rows, columns=COLUMNS)
    # df_raw.to_excel(configs.OUTPUT_EXCEL_RAW, index=False)
    # print(f"✔ Combined output written: {configs.OUTPUT_EXCEL_RAW}")

    try:
        df_raw.to_excel(configs.OUTPUT_EXCEL_RAW, index=False)
        print(f"✔ Excel written: {configs.OUTPUT_EXCEL_RAW}")

    except Exception as e:
        print("❌ Excel write failed, creating blank Excel")
        print(str(e))

        wb = Workbook()
        ws = wb.active
        ws.append(COLUMNS)   # headers only
        wb.save(configs.OUTPUT_EXCEL_RAW)

        print(f"⚠ Blank Excel created: {configs.OUTPUT_EXCEL_RAW}")

    
    
    print("✔ Extraction completed successfully")
    






# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#                  COMPONENTS : CLASSIFICATION
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# processor.py


openai_client = get_openai_client()

# ------------------------------------------------------------
# BATCH CLASSIFICATION
# ------------------------------------------------------------
def classify_batch_llm(batch_rows, batch_indices):
    payload = [
        {"index": idx, "component_data": row}
        for idx, row in zip(batch_indices, batch_rows)
    ]
    prompt = f"""
You are an IEC 61010-01 electrical safety certification engineer.
Evaluate EACH component below independently.

CRITICALITY RULES:
{json.dumps(CRITICAL_RULES, indent=2)}

DECISION LOGIC:
- If ANY rule is satisfied → component is CRITICAL
- Rule score = rules_passed / total_rules
- Confidence = 0–100 (engineering certainty)
- Be conservative. Do NOT guess.

Respond ONLY in JSON array.
Each object MUST include the same index provided.

RESPONSE FORMAT:
[
  {{
    "index": 0,
    "critical": true/false,
    "confidence": 0-100,
    "rules_passed": [1,4],
    "rule_score": 0.25,
    "reasoning": "concise technical justification"
  }}
]

COMPONENTS:
{json.dumps(payload, indent=2)}
"""
    response = openai_client.chat.completions.create(
        model=configs.CLASSIFICATION_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a strict IEC 61010 compliance engineer."},
            {"role": "user", "content": prompt}
        ]
    )
    # Track usage logic handled in c2_utils, but here we track explicitly if needed
    # for simplicity using the same object
    usage = response.usage
    if usage:
        TOTAL_TOKENS["prompt"] += usage.prompt_tokens or 0
        TOTAL_TOKENS["completion"] += usage.completion_tokens or 0
        TOTAL_TOKENS["total"] += usage.total_tokens or 0

    results = json.loads(response.choices[0].message.content)
    output = {}
    for r in results:
        output[r["index"]] = {
            "critical": bool(r.get("critical", False)),
            "confidence": int(r.get("confidence", 0)),
            "rules_passed": r.get("rules_passed", []),
            "rules_passed_count": len(r.get("rules_passed", [])),
            "rule_score": float(r.get("rule_score", 0.0)),
            "reasoning": r.get("reasoning", ""),
        }
    return output

def run_classification(df):
    records = df.to_dict(orient="records")
    batches = []
    for i in range(0, len(records), configs.CLASSIFICATION_BATCH_SIZE):
        batch_rows = records[i:i + configs.CLASSIFICATION_BATCH_SIZE]
        batch_indices = list(range(i, min(i + configs.CLASSIFICATION_BATCH_SIZE, len(records))))
        batches.append((batch_rows, batch_indices))

    results_map = {}
    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as executor:
        futures = [
            executor.submit(classify_batch_llm, rows, idxs)
            for rows, idxs in batches
        ]
        for future in as_completed(futures):
            try:
                batch_result = future.result()
                results_map.update(batch_result)
            except Exception as e:
                print("⚠ Batch classification failed:", e)
                print("----------------------------------------------------------------")
    result_rows = []
    for i in range(len(records)):
        result_rows.append(results_map.get(i, {
            "critical": False,
            "confidence": 0,
            "reasoning": "Classification failed"
        }))
    
    results_df = pd.DataFrame(result_rows)
    final_df = pd.concat([df.reset_index(drop=True), results_df], axis=1)
    return final_df

# ------------------------------------------------------------
# DEDUPLICATION
# ------------------------------------------------------------
def deduplicate_components(df):
    df["__dedupe_key"] = (
        df["Component Name"].apply(normalize_name)
        + "||"
        + df["Category"].fillna("").str.lower().str.strip()
    )
    
    df["critical_sort"] = df["critical"].astype(str).str.lower().isin(["true", "1", "yes", "y"])
    df["confidence_sort"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0)
    df["rule_score_sort"] = pd.to_numeric(df["rule_score"], errors="coerce").fillna(0)

    df = df.sort_values(
        by=["critical_sort", "confidence_sort", "rule_score_sort"],
        ascending=[False, False, False]
    )

    deduped_df = df.drop_duplicates(subset="__dedupe_key", keep="first")
    
    # Filter Critical & Rule > 1
    deduped_df = deduped_df[
        deduped_df["critical"].astype(str).str.lower().isin(["true", "1", "yes", "y"])
    ]
    deduped_df = deduped_df[
        pd.to_numeric(deduped_df["rules_passed_count"], errors="coerce").fillna(0) > 1
    ]

    deduped_df["_image_id"] = deduped_df["URL"].apply(normalize_image_url)
    deduped_df["_image_sort_key"] = deduped_df["_image_id"].where(deduped_df["_image_id"].notna(), "zzzz_guide")
    deduped_df = deduped_df.sort_values("_image_sort_key").reset_index(drop=True)

    # Assign Photo No
    photo_map = {}
    photo_counter = 1

    def assign_photo_no(image_id):
        nonlocal photo_counter

        if not image_id:
            return "guide"

        img = str(image_id).strip().lower()

        # ----- VALID IMAGE CHECK -----
        is_http_image = img.startswith(("http://", "https://"))
        is_base64_image = img.startswith("data:image/")

        if not (is_http_image or is_base64_image):
            return "guide"

        # ----- ASSIGN CONTINUOUS PHOTO NO -----
        if image_id not in photo_map:
            photo_map[image_id] = photo_counter
            photo_counter += 1

        return photo_map[image_id]
 

    deduped_df["photo_no"] = deduped_df["_image_id"].apply(assign_photo_no)
    
    deduped_df = deduped_df.drop(columns=[
        "__dedupe_key", "critical_sort", "confidence_sort", 
        "rule_score_sort", "_image_id", "_image_sort_key"
    ])
    
    return deduped_df




def run_processor():
    configs.require_runtime()
    print("\n--- Classifying Components ---")
    df_raw = pd.read_excel(configs.OUTPUT_EXCEL_RAW, dtype=str)

    if df_raw.empty:
        print("ℹ No components found. Writing empty outputs.")

        classified_cols = list(dict.fromkeys(
            list(df_raw.columns) + [
                "critical", "confidence", "rules_passed",
                "rules_passed_count", "rule_score", "reasoning"
            ]
        ))

        pd.DataFrame(columns=classified_cols).to_excel(
            configs.OUTPUT_EXCEL_CLASSIFIED, index=False
        )

        dedup_cols = [
            "Component Name", "Category", "Confidence", "Source Type",
            "URL", "Filename", "Page Number", "Guide Reference", "Evidence",
            "critical", "confidence", "rules_passed",
            "rules_passed_count", "rule_score", "reasoning", "photo_no"
        ]

        pd.DataFrame(columns=dedup_cols).to_excel(
            configs.OUTPUT_EXCEL_DEDUPED, index=False
        )

        return

    df_classified = run_classification(df_raw)
    df_classified.to_excel(configs.OUTPUT_EXCEL_CLASSIFIED, index=False)
    print(f"✔ Classified excel written: {configs.OUTPUT_EXCEL_CLASSIFIED}")

    print("\n--- Deduplicating ---")
    df_deduped = deduplicate_components(df_classified)
    df_deduped.to_excel(configs.OUTPUT_EXCEL_DEDUPED, index=False)
    print(f"✔ Deduplicated excel written: {configs.OUTPUT_EXCEL_DEDUPED}")



# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#                    COMPONENTS : FORMATTING
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



def create_s4_json(input_excel, output_json):
    df = pd.read_excel(input_excel, dtype=str)
    
    # --------------------------------
    # CASE: EMPTY SHEET → CREATE NULL ITEM
    # --------------------------------
    if df.empty:
        null_item = {
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

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump({"Items": [null_item]}, f, indent=4)

        print("✔ Sheet 4 JSON created with NULL placeholder item:", output_json)
        return

        # --------------------------------
        # CASE: NON-EMPTY SHEET → CREATE ITEMs
        # --------------------------------
        
    if "photo_no" not in df.columns:
        print("photo_no column missing.")
        return

    def photo_sort_key(v):
        if v == "guide" or v is None: return 10_000
        try: return int(v)
        except: return 10_000

    df["_photo_sort"] = df["photo_no"].apply(photo_sort_key)
    df = df.sort_values(by=["_photo_sort", "Component Name"]).reset_index(drop=True)
    df.drop(columns=["_photo_sort"], inplace=True)

    items = []
    current_row = 3
    start_column = "A"

    for idx, row in df.iterrows():
        item_no = idx + 1
        start_cell = f"{start_column}{current_row}"
        item = {
            "start_cell": start_cell,
            "row_type": "table_data",
            "photo_no": clean_value(row.get("photo_no")),
            "item_no": str(item_no),
            "name": clean_value(row.get("Component Name")),
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
            "image_support": clean_value(row.get("Image URLs")),
            "text_support": [
                                {
                                    "filename": clean_value(row.get("Filename")),
                                    "page": (int(row.get("Page Number"))
                                                if pd.notna(row.get("Page Number"))
                                                else None
                                            ),
                                    "similarity_score": None,
                                    "preview_text": clean_value(row.get("Guide Reference")),
                                    "url": clean_value(row.get("URL")),
                                }
                            ],
            "confidence": int(clean_value(row.get("confidence")))
        }
        items.append(item)
        current_row += 1

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({"Items": items}, f, indent=4)
    print("✔ JSON created successfully:", output_json)

def create_s3_json(input_excel, output_json):
    df = pd.read_excel(input_excel, dtype=str)

    REQUIRED_COLS = {"photo_no", "URL", "Source Type"}
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        #print(f"⚠ Missing required columns for Sheet 3: {missing}")
        return

    # --------------------------------
    # Strict image validation
    # --------------------------------
    def has_real_image(row):
        img = str(row.get("URL", "")).strip().lower()
        src = str(row.get("Source Type", "")).strip().lower()
        photo = str(row.get("photo_no", "")).strip().lower()

        if not photo or photo in ("guide", "nan", "none"):
            return False
        if "image" not in src:
            return False
        if not img or img in ("nan", "none", "[]"):
            return False
        if not img.startswith(("http://", "https://")):
            return False
        return True

    df["has_image"] = df.apply(has_real_image, axis=1)
    matched_df = df[df["has_image"]].copy()

    # --------------------------------
    # CASE 1: NO IMAGE → CREATE NULL ITEM
    # --------------------------------
    if matched_df.empty:
        null_item = {
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

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump({"Items": [null_item]}, f, indent=4)

        #print("✔ Sheet 3 JSON created with NULL placeholder item:", output_json)
        return

    # --------------------------------
    # CASE 2: VALID IMAGES EXIST
    # --------------------------------
    def photo_sort_key(v):
        try:
            return int(v)
        except Exception:
            return 10_000

    photo_df = (
        matched_df
        .assign(_photo_sort=lambda d: d["photo_no"].map(photo_sort_key))
        .sort_values("_photo_sort")
        .drop_duplicates(subset=["photo_no"])
        .reset_index(drop=True)
        .drop(columns="_photo_sort")
    )

    items = []
    current_row = 3
    row_gap = 8
    column = "A"

    def build_field_text(photo_no, caption):
        if caption:
            return f"Photo {photo_no} - {caption}"
        return f"Photo {photo_no}"

    for _, row in photo_df.iterrows():
        items.append({
            "question_cell": f"{column}{current_row}",
            "prefix": "Product",
            "field": build_field_text(
                clean_value(row.get("photo_no")),
                clean_value(row.get("Image Captions"))
            ),
            "answer_cell": f"{column}{current_row + 1}",
            "photo_path": clean_value(row.get("Image URLs")),
            "field_merged": False,
            "fm_range": None,
            "value_merged": False,
            "vm_range": None,
            "task_type": "photo",
            "user_editable": True,
            "ai_fillable": True,
            "accuracy_level": False
        })
        current_row += row_gap

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({"Items": items}, f, indent=4)

    #print("✔ Sheet 3 JSON created with image items:", output_json)

    
    
def run_formatter():
    configs.require_runtime()

        # 5. FORMATTING (JSON)
    #print("\n--- Formatting JSONs ---")
    create_s4_json(configs.OUTPUT_EXCEL_DEDUPED, configs.OUTPUT_JSON_S4)
    create_s3_json(configs.OUTPUT_EXCEL_DEDUPED, configs.OUTPUT_JSON_S3)




# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#               COMPONENTS : ORCHESTRATION - CASE 2
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def run_case2_pipeline():
    configs.require_runtime()
    
    #print("Step 1 : Extracting . . .")
    run_extractor()
    
    #print("Step 2 : Processing . . .")
    run_processor()
    
    #print("Step 3 : Formatting JSON . . .")
    run_formatter()



