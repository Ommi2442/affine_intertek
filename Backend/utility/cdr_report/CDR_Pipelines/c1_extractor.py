# Extractor.py
import json
import pandas as pd
import utility.cdr_report.CDR_Pipelines.configs as configs
import utility.cdr_report.CDR_Pipelines.c1_rules as c1_rules
import utility.cdr_report.CDR_Pipelines.c1_utils as c1_utils

def classify_in_batches(df, batch_size):
    configs.require_runtime()

    results = []

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size].copy()
        batch["row_id"] = batch.index.astype(str)

        payload = batch.to_dict(orient="records")

        response = c1_utils.client.chat.completions.create(
            model=configs.VISION_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": c1_rules.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": c1_rules.USER_PROMPT.format(
                        components_json=json.dumps(payload, indent=2)
                    )
                }
            ]
        )

        raw_text = response.choices[0].message.content
        batch_result = c1_utils.safe_json_load(raw_text)

        if batch_result is None:
            #print("⚠️ JSON parse failed, marking batch as LOW confidence")
            for row_id in batch["row_id"]:
                results.append({
                    "row_id": row_id,
                    "is_critical": True,
                    "triggered_rules": [],
                    "confidence_score": 0.3,
                    "reasoning": "LLM response parsing failed"
                })
        else:
            results.extend(batch_result)

    return pd.DataFrame(results)

def run_extraction():
    configs.require_runtime()

    #print("Starting Extraction...")
    # Load master sheet
    master_df = pd.read_excel(configs.MASTER_SHEET_PATH, dtype=str)

    # Classify
    results_df = classify_in_batches(master_df, configs.BATCH_SIZE)

    # Rule-count scoring
    results_df["rules_triggered_count"] = results_df["triggered_rules"].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )
    results_df["rules_triggered_total"] = 8
    results_df["rules_score"] = (
        results_df["rules_triggered_count"] /
        results_df["rules_triggered_total"]
    )

    # Confidence level
    results_df["confidence_level"] = results_df["confidence_score"].apply(c1_rules.confidence_level)

    # Merge back to master
    final_df = master_df.copy()
    results_df["row_id"] = results_df["row_id"].astype(int)
    final_df = final_df.join(results_df.set_index("row_id"), how="left")

    # Export
    final_df.to_excel(configs.OUTPUT_PATH_FINAL, index=False)

    #print("✔ Critical component classification complete")
    #print(f"✔ Output saved to: {configs.OUTPUT_PATH_FINAL}")