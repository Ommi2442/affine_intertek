# c2_formatter.py
import json
import pandas as pd
import utility.cdr_report.CDR_Pipelines.c2_utils as c2_utils
import utility.cdr_report.CDR_Pipelines.configs as configs

def create_s4_json(input_excel, output_json):
    df = pd.read_excel(input_excel, dtype=str)
    
    if "photo_no" not in df.columns:
        #print("photo_no column missing.")
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
            "photo_no": c2_utils.clean_value(row.get("photo_no")),
            "item_no": str(item_no),
            "name": c2_utils.clean_value(row.get("Component Name")),
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
            "image_support": c2_utils.clean_value(row.get("Image URLs")),
            "text_support": [
                                {
                                    "filename": c2_utils.clean_value(row.get("Filename")),
                                    "page": (int(row.get("Page Number"))
                                                if pd.notna(row.get("Page Number"))
                                                else None
                                            ),
                                    "similarity_score": None,
                                    "preview_text": c2_utils.clean_value(row.get("Guide Reference")),
                                    "url": c2_utils.clean_value(row.get("URL")),
                                }
                            ],
            "confidence": int(c2_utils.clean_value(row.get("confidence")))
        }
        items.append(item)
        current_row += 1

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({"Items": items}, f, indent=4)
    #print("✔ JSON created successfully:", output_json)



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
                c2_utils.clean_value(row.get("photo_no")),
                c2_utils.clean_value(row.get("Image Captions"))
            ),
            "answer_cell": f"{column}{current_row + 1}",
            "photo_path": c2_utils.clean_value(row.get("Image URLs")),
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
