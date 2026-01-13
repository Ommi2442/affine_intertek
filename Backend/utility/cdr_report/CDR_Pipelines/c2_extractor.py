# c2_extractor.py
import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import utility.cdr_report.CDR_Pipelines.configs as configs
import utility.cdr_report.CDR_Pipelines.c2_utils as c2_utils
import os
from urllib.parse import urlparse


openai_client = c2_utils.get_openai_client()

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

        c2_utils.track_usage(response)

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
                        "You are a certification engineer.\n"
                        "Extract physical components supported by the text.\n"
                        "Each component MUST be supported by the text."
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

        c2_utils.track_usage(response)
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



def run_extractor():
    configs.require_runtime()

    print("--- Starting Pipeline ---")

    # 1. DISCOVERY
    image_urls = c2_utils.get_image_urls_from_container_sas()

    guide_blob_name, guide_url = c2_utils.find_user_guide_blob()

    if not guide_blob_name:
        return
    guide_filename = guide_blob_name.split("/")[-1]
    guide_local_path = c2_utils.download_blob(guide_blob_name)
    guide_text = c2_utils.extract_text_from_file(guide_local_path)
    

    guide_components = extract_components_from_guide(
        guide_text,
        guide_filename,
        guide_url
    )


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
                "Component Name": c["component_name"],
                "Category": c["component_category"],
                "Confidence": c["confidence"],
                "Source Type": s["source_type"],

                # (1) URL logic
                "URL": s["source_ref"],

                # (3) filename
                "Filename": s.get("filename"),

                # (4) page number (guide only)
                "Page Number": s.get("page_number"),

                # (2) exact chunk
                "Guide Reference": s.get("chunk") if s["source_type"] == "guide" else None,

                "Evidence": s.get("evidence")
            })

    df_raw = pd.DataFrame(rows)
    df_raw.to_excel(configs.OUTPUT_EXCEL_RAW, index=False)

    print(f"✔ Combined output written: {configs.OUTPUT_EXCEL_RAW}")
    print("✔ Extraction completed successfully")

    
