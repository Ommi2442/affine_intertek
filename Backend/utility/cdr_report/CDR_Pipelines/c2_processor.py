# processor.py
import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import utility.cdr_report.CDR_Pipelines.configs as configs
import utility.cdr_report.CDR_Pipelines.c2_rules as c2_rules
import utility.cdr_report.CDR_Pipelines.c2_utils as c2_utils

openai_client = c2_utils.get_openai_client()

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
{json.dumps(c2_rules.CRITICAL_RULES, indent=2)}

DECISION LOGIC:
- If ANY rule is satisfied → component is CRITICAL
- Rule score = rules_passed / total_rules
- Confidence = 0.0–1.0 (engineering certainty)
- Be conservative. Do NOT guess.

Respond ONLY in JSON array.
Each object MUST include the same index provided.

RESPONSE FORMAT:
[
  {{
    "index": 0,
    "critical": true/false,
    "confidence": 0.0,
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
        c2_utils.TOTAL_TOKENS["prompt"] += usage.prompt_tokens or 0
        c2_utils.TOTAL_TOKENS["completion"] += usage.completion_tokens or 0
        c2_utils.TOTAL_TOKENS["total"] += usage.total_tokens or 0

    results = json.loads(response.choices[0].message.content)
    output = {}
    for r in results:
        output[r["index"]] = {
            "critical": bool(r.get("critical", False)),
            "confidence": float(r.get("confidence", 0.0)),
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

    result_rows = []
    for i in range(len(records)):
        result_rows.append(results_map.get(i, {
            "critical": False,
            "confidence": 0.0,
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
        df["Component Name"].apply(c2_utils.normalize_name)
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

    deduped_df["_image_id"] = deduped_df["Image URLs"].apply(c2_utils.normalize_image_url)
    deduped_df["_image_sort_key"] = deduped_df["_image_id"].where(deduped_df["_image_id"].notna(), "zzzz_guide")
    deduped_df = deduped_df.sort_values("_image_sort_key").reset_index(drop=True)

    # Assign Photo No
    photo_map = {}
    photo_counter = 1
    def assign_photo_no(image_id):
        nonlocal photo_counter
        if not image_id:
            return "guide"
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
        # 3. CLASSIFICATION
    print("\n--- Classifying Components ---")
    df_raw = pd.read_excel(configs.OUTPUT_EXCEL_RAW, dtype=str)
    df_classified = run_classification(df_raw)
    df_classified.to_excel(configs.OUTPUT_EXCEL_CLASSIFIED, index=False)
    print(f"✔ Classified excel written: {configs.OUTPUT_EXCEL_CLASSIFIED}")

    # 4. DEDUPLICATION
    print("\n--- Deduplicating ---")
    df_deduped = deduplicate_components(df_classified)
    df_deduped.to_excel(configs.OUTPUT_EXCEL_DEDUPED, index=False)
    print(f"✔ Deduplicated excel written: {configs.OUTPUT_EXCEL_DEDUPED}")