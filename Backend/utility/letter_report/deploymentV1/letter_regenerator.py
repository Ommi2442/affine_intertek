import os
import json
import requests
import pandas as pd
from utility.letter_report.deploymentV1.letter_generator import *
from utility.letter_report.deploymentV1.core import *

# -------------------------------------------------------
# Utilities
# -------------------------------------------------------


def download_images_from_urls(image_urls, download_dir):
    """
    Downloads images from blob URLs into local folder
    Returns list of local file paths
    """
    os.makedirs(download_dir, exist_ok=True)

    downloaded = []

    for idx, item in enumerate(image_urls):
        url = item.get("url")
        if not url:
            continue

        filename = f"non_conforming_{idx + 1}.jpg"
        local_path = os.path.join(download_dir, filename)

        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(response.content)

            downloaded.append(local_path)
            print(f"⬇️ Downloaded: {local_path}")
        else:
            print(f"⚠️ Failed to download: {url}")

    return downloaded


def extract_table_from_json(data, key_name):
    """
    Extract dataframe table stored in JSON item.value
    Ignores text_support metadata columns.
    """
    for page in data.get("pages", []):
        for item in page.get("items", []):
            if item.get("key") == key_name and isinstance(item.get("value"), list):
                df = pd.DataFrame(item["value"])

                # --------------------------------------------------
                # DROP metadata columns (DO NOT render in DOCX)
                # --------------------------------------------------
                for col in ["text_support", "is_user_edited"]:
                    if col in df.columns:
                        df = df.drop(columns=[col])

                return df

    return None


def extract_non_conforming_image_urls(data):
    """
    Extract nonConforming_urls from photograph section
    """
    for page in data.get("pages", []):
        for item in page.get("items", []):
            if item.get("key") == "photograph":
                return item.get("nonConforming_urls", [])

    return []


# -------------------------------------------------------
# MAIN DOCX UPDATE PIPELINE
# -------------------------------------------------------


def rebuild_letter_docx_from_json(
    letter_json_path,
    letter_header_json_path,
    letter_template_docx,
    output_letter_docx,
    temp_image_dir="non_conforming_images",
):
    """
    Rebuilds letter.docx using only JSON inputs.
    No RAG, no extraction, no blob crawling.
    """

    print("\n==============================")
    print("📄 DOCX REBUILD PIPELINE")
    print("==============================\n")

    # -------------------------------------------------------
    # Load JSON
    # -------------------------------------------------------

    with open(letter_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(letter_header_json_path, "r", encoding="utf-8") as f:
        data_header = json.load(f)

    # -------------------------------------------------------
    # Step 1 — Replace placeholders from JSON
    # -------------------------------------------------------

    print("✏️ Updating placeholders from JSON...")

    replace_keys_with_values_no_format_change_v2(
        input_docx=letter_template_docx, output_docx=output_letter_docx, data=data
    )

    replace_header_keys_with_values_header(
        input_docx=output_letter_docx, output_docx=output_letter_docx, data=data_header
    )

    # -------------------------------------------------------
    # Step 2 — Insert Critical Components Table
    # -------------------------------------------------------

    print("📊 Inserting Critical Components table...")

    df_critical = extract_table_from_json(data, "Critical components table")

    if df_critical is not None and not df_critical.empty:
        insert_dataframe_below_anchor_critical_components(
            input_docx=output_letter_docx,
            output_docx=output_letter_docx,
            df=df_critical,
            anchor_text="Details for the following critical components or materials have not been provided as required:",
        )
        print("✅ Critical components table inserted")
    else:
        insert_dataframe_below_anchor_critical_components(
            input_docx=output_letter_docx,
            output_docx=output_letter_docx,
            df=df_critical,
            anchor_text="Details for the following critical components or materials have not been provided as required:",
        )
        print("⚠️ No critical components table found in JSON")

    # -------------------------------------------------------
    # Step 3 — Insert Non-Conformance Table
    # -------------------------------------------------------

    print("📊 Inserting Non-Conformance table...")

    df_nonpass = extract_table_from_json(data, "Non-conformance Table")

    if df_nonpass is not None and not df_nonpass.empty:
        insert_dataframe_below_anchor_non_conformance(
            input_docx=output_letter_docx,
            output_docx=output_letter_docx,
            df=df_nonpass,
            anchor_text="The shared documents were evaluated during the intrinsic safety analysis and constructional evaluation and following non-conformances were observed:",
        )
        print("✅ Non-conformance table inserted")
    else:
        insert_dataframe_below_anchor_non_conformance(
            input_docx=output_letter_docx,
            output_docx=output_letter_docx,
            df=df_nonpass,
            anchor_text="The shared documents were evaluated during the intrinsic safety analysis and constructional evaluation and following non-conformances were observed:",
        )
        print("⚠️ No non-conformance table found in JSON")

    print("Updating Letter Non ai fillable values")
    replace_keys_with_values_no_format_change_all(
        input_docx=output_letter_docx, output_docx=output_letter_docx, data=data
    )

    # -------------------------------------------------------
    # Step 4 — Insert Non-Conforming Images (Section 6)
    # -------------------------------------------------------

    print("🖼️ Inserting Non-Conforming Images...")

    image_urls = extract_non_conforming_image_urls(data)

    if image_urls:
        downloaded_images = download_images_from_urls(image_urls, temp_image_dir)

        if downloaded_images:
            insert_photos_before_section_6_table(
                docx_path=output_letter_docx,
                output_path=output_letter_docx,
                image_paths=downloaded_images,
            )
            print("✅ Non-conforming images inserted")
        else:
            print("⚠️ No images downloaded")
    else:
        print("⚠️ No non-conforming image URLs found in JSON")

    print("\n==============================")
    print("✅ DOCX REBUILD COMPLETE")
    print("==============================\n")

    return output_letter_docx
