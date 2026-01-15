# c1_formatter.py
import pandas as pd
import json
import utility.cdr_report.CDR_Pipelines.configs as configs
import utility.cdr_report.CDR_Pipelines.c1_utils as c1_utils

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
    Handles pipe-separated filenames / URLs correctly.
    """

    def split(v):
        if not v:
            return []
        return [x.strip() for x in str(v).split("|")]

    filenames = split(sheet_name)
    urls = split(source_doc)

    max_len = max(len(filenames), len(urls))

    supports = []

    for i in range(max_len):
        filename = filenames[i] if i < len(filenames) else None
        url = urls[i] if i < len(urls) else None

        supports.append({
            "filename": filename,
            "page": filename,   # ← your expected behavior
            "similarity_score": None,
            "text": None,
            "url": url
        })

    return supports


def run_formatter():
    configs.require_runtime()

    print("Starting Formatting...")

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


    print("Total rows in sheet           :", len(df))
    print("Rows with image match (true) :", len(matched_df))

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
    print("Unique photos detected:", len(photo_map))
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

    print("Rows sorted by photo number")

    # Persist photo_no back to Excel
    final_df.to_excel(configs.FINAL_OUTPUT_WITH_EVIDENCE, index=False)
    print("✔ photo_no persisted to Excel for all rows")


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
            "name": c1_utils.clean_value(row.get("Description")),
            "manufacturer": c1_utils.clean_value(row.get("Manufacturer")),
            "type_model": c1_utils.clean_value(row.get("Manufacturer Part Number")),
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
                                c1_utils.clean_value(row.get("image_url"))
                                if row["photo_no"] != "Not Shown"
                                else None
                            ),

            "text_support": build_text_support_list(
                                                        c1_utils.clean_value(row.get("sheet_name")),
                                                        c1_utils.clean_value(row.get("source_doc"))
                                                    ),

            "confidence": int(float(c1_utils.clean_value(row.get("confidence_score")) or 0) * 100)
        }

        items.append(item)
        current_row += 1

    output = {"Items": items}

    with open(configs.OUTPUT_JSON_COMPONENTS, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)

    print("✔ Component JSON created successfully")
    print("✔ Output file:", configs.OUTPUT_JSON_COMPONENTS)

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
                c1_utils.clean_value(row["photo_no"]),
                c1_utils.clean_value(row.get("image_caption"))
            ),
            "answer_cell": answer_cell,
            "photo_path": c1_utils.clean_value(row.get("image_url")),
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

    # ---------------- ADD UNMATCHED IMAGES ----------------

    for img_url in sorted(remaining_images):
        question_cell = f"{START_COLUMN}{current_row_meta}"
        answer_cell = f"{START_COLUMN}{current_row_meta + 1}"

        items_meta.append({
            "question_cell": question_cell,
            "prefix": "Product",
            "field": image_name_no_ext(img_url),   # filename without extension
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

        current_row_meta += ROW_GAP



    with open(configs.OUTPUT_JSON_METADATA, "w", encoding="utf-8") as f:
        json.dump({"Items": items_meta}, f, indent=4)

    print("✔ Photo metadata JSON created")
    print("✔ Output file:", configs.OUTPUT_JSON_METADATA) 