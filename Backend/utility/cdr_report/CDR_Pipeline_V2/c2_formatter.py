# formatter.py
import json
import pandas as pd
import c2_utils
import configs

def create_4c2_json(input_excel, output_json):
    df = pd.read_excel(input_excel, dtype=str)
    
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
            "image_url": c2_utils.clean_value(row.get("Image URLs"))
        }
        items.append(item)
        current_row += 1

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({"Items": items}, f, indent=4)
    print("✔ JSON created successfully:", output_json)

def create_3c2_json(input_excel, output_json):
    df = pd.read_excel(input_excel, dtype=str)
    
    df["has_image"] = (
        df["Image URLs"].notna() & 
        df["Image URLs"].astype(str).str.strip().ne("") & 
        df["photo_no"].ne("guide")
    )
    matched_df = df[df["has_image"]].copy()

    if matched_df.empty:
        print("No image-based components found for 3c2.")
        return

    def photo_sort_key(v):
        try: return int(v)
        except: return 10_000

    photo_df = (
        matched_df
        .dropna(subset=["photo_no"])
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

    def build_field_text(photo_no, evidence_count):
        if not photo_no or photo_no == "guide": return None
        if evidence_count: return f"Photo {photo_no} - evidence count {evidence_count}"
        return f"Photo {photo_no}"

    for _, row in photo_df.iterrows():
        item = {
            "question_cell": f"{column}{current_row}",
            "prefix": "Product",
            "field": build_field_text(c2_utils.clean_value(row["photo_no"]), c2_utils.clean_value(row.get("Evidence Count"))),
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
        }
        items.append(item)
        current_row += row_gap

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({"Items": items}, f, indent=4)
    print("✔ Photo metadata JSON created:", output_json)
    
    
def run_formatter():
        # 5. FORMATTING (JSON)
    print("\n--- Formatting JSONs ---")
    create_4c2_json(configs.OUTPUT_EXCEL_DEDUPED, configs.OUTPUT_JSON_4C2)
    create_3c2_json(configs.OUTPUT_EXCEL_DEDUPED, configs.OUTPUT_JSON_3C2)