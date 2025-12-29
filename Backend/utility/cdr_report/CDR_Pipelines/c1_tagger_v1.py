# phototag.py
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from azure.storage.blob import BlobServiceClient
import configs
import c1_utils
import c1_rules

# ===================== INTERNAL UTILS =====================

def embed_text(text):
    """
    Generates embedding for a single text string.
    Returns None if text is empty or error occurs.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return None
        
    try:
        return c1_utils.openai_client.embeddings.create(
            model=configs.EMBED_MODEL,
            input=text
        ).data[0].embedding
    except Exception as e:
        print(f"⚠ Embedding failed: {e}")
        return None

def get_image_urls_from_container_sas():
    blob_service = BlobServiceClient.from_connection_string(
        configs.AZURE_BLOB_CONNECTION_STRING
    )
    container_client = blob_service.get_container_client(
        configs.BLOB_CONTAINER_NAME
    )

    blob_names = [
        blob.name
        for blob in container_client.list_blobs()
        if blob.name.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    print("Blobs found in container:", len(blob_names))

    if not blob_names:
        return []

    base, sas = configs.AZURE_BLOB_CONTAINER_SAS_URL.split("?", 1)
    base = base.rstrip("/")

    urls = [f"{base}/{name}?{sas}" for name in blob_names]

    print("Image URLs constructed:", len(urls))
    return urls

def describe_image(image_url):
    try:
        response = c1_utils.openai_client.chat.completions.create(
            model=configs.VISION_MODEL,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an electrical safety engineer. "
                        "Be factual. Do not guess."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Describe this product image.\n\n"
                                "Respond ONLY in this format:\n\n"
                                "IMAGE TYPE:\n"
                                "<exterior / interior / partial / angle>\n\n"
                                "VISIBLE ELEMENTS:\n"
                                "- <element with location>\n"
                                "- <element with location>\n\n"
                                "NOT VISIBLE / NOT DETERMINABLE:\n"
                                "- <item>\n"
                                "- <item>"
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
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠ Image not readable by Vision ({image_url}): {e}")
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

# ===================== MAIN PIPELINE =====================
def run_phototagging():
    print("Starting Phototagging (Optimized)...")
    
    # STEP 0: LOAD ORIGINAL & FILTER CRITICAL
    df_all = pd.read_excel(configs.OUTPUT_PATH_FINAL, dtype=str)

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

    print("...Generating Image Descriptions (Parallel)...")
    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as exe:
        image_descriptions = list(exe.map(describe_image, image_urls))

    # Filter out failed descriptions
    valid = [(u, d) for u, d in zip(image_urls, image_descriptions) if d]
    
    if valid:
        valid_urls, valid_descriptions = zip(*valid)
    else:
        valid_urls, valid_descriptions = [], []
        print("⚠ No valid image descriptions generated.")

    print(f"Images successfully described: {len(valid_descriptions)}")

    # STEP 3: IMAGE EMBEDDINGS (PARALLEL)
    print("...Generating Image Embeddings (Parallel)...")
    visible_texts = [extract_visible_elements(d) for d in valid_descriptions]

    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as exe:
        valid_img_embeddings = list(exe.map(embed_text, visible_texts))

    # Filter out failed embeddings
    image_items = []
    for u, e in zip(valid_urls, valid_img_embeddings):
        if e is not None:
            image_items.append({"url": u, "embedding": e})
            
    print(f"Images with usable embeddings: {len(image_items)}")

    # STEP 4: COMPONENT EMBEDDINGS (PARALLEL)
    print("...Generating Component Embeddings (Parallel)...")
    df["component_text"] = df.apply(
        lambda r: f"{r.get('Component Name','')} {r.get('Description','')}",
        axis=1
    )
    
    # Parallelize this!
    with ThreadPoolExecutor(max_workers=configs.MAX_WORKERS) as exe:
        comp_embeddings = list(exe.map(embed_text, df["component_text"].tolist()))
    
    df["embedding"] = comp_embeddings
    print(f"Component embeddings created: {len(df)}")

    # STEP 5: MATCHING + JUSTIFICATION (VECTORIZED)
    print("...Calculating Matches...")
    
    results = []
    
    # Pre-calculate matrix if we have images
    if image_items:
        img_vecs = [item["embedding"] for item in image_items]
        # Filter rows that have valid embeddings
        valid_rows_mask = df["embedding"].notna()
        valid_comp_vecs = df.loc[valid_rows_mask, "embedding"].tolist()
        
        if valid_comp_vecs:
            # Distance Matrix (Rows x Images)
            dist_matrix = calculate_cosine_distances_matrix(valid_comp_vecs, img_vecs)
    
    # Counter for matrix indexing
    valid_row_idx = 0

    for idx, row in df.iterrows():
        name = row.get("Component Name", "")
        desc = row.get("Description", "")
        applicability = c1_rules.visual_applicability(name, desc)
        comp_emb = row["embedding"]

        # Default result structure
        res = {
            "visual_applicability": applicability,
            "found_in_images": False,
            "image_url": None,
            "visual_confidence": "No visual evidence",
            "visual_basis": ""
        }

        # Case A: Not Applicable
        if applicability == "Not applicable":
            res["visual_basis"] = "Component is internal/electronic and not visually verifiable from product images"
            results.append(res)
            # Increment index if this row had an embedding, even if we skip it logically
            if comp_emb is not None: valid_row_idx += 1
            continue

        # Case B: No Images Available
        if not image_items:
            res["visual_basis"] = "No usable product images available"
            results.append(res)
            if comp_emb is not None: valid_row_idx += 1
            continue
            
        # Case C: Missing Component Embedding
        if comp_emb is None:
            res["visual_basis"] = "Component text could not be embedded"
            results.append(res)
            continue

        # Case D: Perform Match
        # Get distances for this specific component from our pre-calced matrix
        distances = dist_matrix[valid_row_idx]
        valid_row_idx += 1
        
        best_idx = np.argmin(distances)
        best_dist = distances[best_idx]
        best_url = image_items[best_idx]["url"]
        
        confidence = c1_rules.visual_confidence_from_distance(best_dist, applicability)

        if confidence == "No visual evidence":
            res["visual_confidence"] = confidence
            res["visual_basis"] = "Visible elements in product images do not clearly correspond to this component"
        else:
            res["found_in_images"] = True
            res["image_url"] = best_url
            res["visual_confidence"] = confidence
            res["visual_basis"] = "Visible elements in product images provide support relevant to the component’s safety role"
            
        results.append(res)

    # Attach results
    df = pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)

    # STEP 6: EXPORT FINAL OUTPUT
    df.to_excel(configs.FINAL_OUTPUT_WITH_EVIDENCE, index=False)
    print(f"✔ Completed. Output: {configs.FINAL_OUTPUT_WITH_EVIDENCE}")