# formatter.py
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

def run_formatter():
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

    matched_df = df[df["found_norm"].isin(["true", "1", "yes", "y"])].copy()

    print("Total rows in sheet           :", len(df))
    print("Rows with image match (true) :", len(matched_df))

    if matched_df.empty:
        print("No components with image matches found.")
        return

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

    # Sort
    matched_df = matched_df.sort_values(
        by=["photo_no", "Description"],
        ascending=[True, True]
    ).reset_index(drop=True)
    
    print("Rows sorted by photo number")

    # Persist photo_no back to Excel
    matched_df.to_excel(configs.FINAL_OUTPUT_WITH_EVIDENCE, index=False)
    print("✔ photo_no persisted to Excel")

    # Build Items
    items = []
    current_row = START_ROW

    for idx, row in matched_df.iterrows():
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
            "image_support": row.get("image_url"),
            "text_support": [{"filename": c1_utils.clean_value(row.get("source_doc")),
                             "page": c1_utils.clean_value(row.get("sheet_name")),
                             "similarity_score": None,
                             "text": None,
                             "page": c1_utils.clean_value(row.get("url"))}],
            "confidence": c1_utils.clean_value(row.get("confidence_score"))
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

    with open(configs.OUTPUT_JSON_METADATA, "w", encoding="utf-8") as f:
        json.dump({"Items": items_meta}, f, indent=4)

    print("✔ Photo metadata JSON created")
    print("✔ Output file:", configs.OUTPUT_JSON_METADATA)