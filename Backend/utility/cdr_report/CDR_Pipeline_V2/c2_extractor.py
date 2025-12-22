# extractor.py
import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import configs
import c2_utils

openai_client = c2_utils.get_openai_client()

# ------------------------------------------------------------
# IMAGE COMPONENT EXTRACTION
# ------------------------------------------------------------
def _process_single_image(img_url):
    comps = []
    try:
        response = openai_client.chat.completions.create(
            model=configs.VISION_MODEL,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an electrical safety engineer.\n"
                        "List ALL identifiable components visible in the image.\n"
                        "Do NOT guess hidden internals."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Respond ONLY in JSON array:\n"
                                "[{\"name\":\"\",\"category\":\"\",\"description\":\"\"}]"
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
        items = json.loads(response.choices[0].message.content)

        for it in items:
            comps.append({
                "component_name": it.get("name"),
                "component_category": it.get("category", "unknown"),
                "sources": [{
                    "source_type": "image",
                    "source_ref": img_url,
                    "evidence": it.get("description", "")
                }],
                "confidence": "high"
            })
    except Exception as e:
        print("⚠ Image failed:", img_url, e)
    return comps

def extract_components_from_images(image_urls):
    if not image_urls:
        return []
    components = []
    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as exe:
        futures = [exe.submit(_process_single_image, u) for u in image_urls]
        for f in as_completed(futures):
            components.extend(f.result())
    return components

# ------------------------------------------------------------
# GUIDE COMPONENT EXTRACTION
# ------------------------------------------------------------
def _process_guide_chunk(chunk, guide_filename):
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
                        "From the user guide text, extract ALL physical components,\n"
                        "assemblies, and subsystems that a safety reviewer would expect\n"
                        "to exist in the product.\n\n"
                        "Rules:\n"
                        "- Components MAY be inferred if they are standard for the described function\n"
                        "- Do NOT invent exotic or optional features\n"
                        "- Each component MUST be supported by a sentence from the text\n"
                        "- Prefer generic component names (e.g. Power Supply, PCB, Enclosure)\n"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "First identify the PRODUCT FUNCTION described.\n"
                        "Then list components required to support that function.\n\n"
                        "Respond ONLY in JSON array:\n"
                        "[{\"name\":\"\",\"category\":\"\",\"reason\":\"Quoted sentence or inference\"}]\n\n"
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
                    "source_ref": guide_filename,
                    "evidence": it.get("reason", "")
                }],
                "confidence": "medium"
            })
    except Exception:
        pass
    return comps

def extract_components_from_guide(guide_text, guide_filename):
    if not guide_text or not guide_text.strip():
        return []
    chunks = [guide_text[i:i+2000] for i in range(0, len(guide_text), 2000)]
    chunks = chunks[:6]
    components = []
    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as exe:
        futures = [
            exe.submit(_process_guide_chunk, ch, guide_filename)
            for ch in chunks
        ]
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
            merged[k]["sources"].extend(comp["sources"])
            merged[k]["confidence"] = "high"
    return list(merged.values())


def run_extractor():
    # 1. SETUP & DISCOVERY
    print("--- Starting Pipeline ---")
    image_urls = c2_utils.get_image_urls_from_container_sas()
    
    guide_blob = c2_utils.find_user_guide_blob()
    guide_filename = guide_blob 
    guide_local_path = c2_utils.download_blob(guide_blob)
    guide_text = c2_utils.extract_text_from_file(guide_local_path)
    print(f"Guide text length: {len(guide_text)}")

    # 2. EXTRACTION (Images + Guide)
    print("\n--- Extracting Components ---")
    image_components = extract_components_from_images(image_urls)
    guide_components = extract_components_from_guide(guide_text, guide_filename)
    combined_components = merge_components(image_components, guide_components)
    
    print(f"Image comps: {len(image_components)}, Guide comps: {len(guide_components)}")
    print(f"Combined unique: {len(combined_components)}")

    # Save RAW
    rows = []
    for c in combined_components:
        rows.append({
            "Component Name": c["component_name"],
            "Category": c["component_category"],
            "Confidence": c["confidence"],
            "Source Types": ", ".join({s["source_type"] for s in c["sources"]}),
            "Evidence Count": len(c["sources"]),
            "Image URLs": "; ".join(s["source_ref"] for s in c["sources"] if s["source_type"] == "image"),
            "Guide Reference": "; ".join(s["source_ref"] for s in c["sources"] if s["source_type"] == "guide")
        })
    df_raw = pd.DataFrame(rows)
    df_raw.to_excel(configs.OUTPUT_EXCEL_RAW, index=False)
    print(f"✔ Raw excel written: {configs.OUTPUT_EXCEL_RAW}")
    
    