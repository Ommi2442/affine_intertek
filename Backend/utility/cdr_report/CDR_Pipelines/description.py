from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import utility.cdr_report.CDR_Pipelines.configs as configs


def get_trf_blob_url(conn_str, container, blob_name):
    p = dict(x.split("=",1) for x in conn_str.split(";") if "=" in x)
    return f"{p['BlobEndpoint'].rstrip('/')}/{container}/{quote(blob_name, safe='/')}?{p['SharedAccessSignature'].lstrip('?')}"

def build_product_section_items(product_info: dict, trf_blob_url):
    """
    Convert refined product_info JSON into CDR Section 2.0 item list
    """
    configs.require_runtime()


    field_map = [  
        ("A3", "Product", "Product ", "B3", "J3", "product"),
        ("A4", "Product", "Brand name", "B4", "J4", "brand_name"),
        ("A5", "Product", "Description", "B5", "J6", "description"),
        ("A7", "Product", "Models", "B7", "J7", "models"),
        ("A8", "Product", "Model Similarity", "B8", "J8", "model_similarity"),
        ("A9", "Product", "Ratings", "B9", "J9", "ratings"),
        ("A10", "Product", "Other Ratings", "B10", "J10", "other_ratings"),
    ]

    items = []

    for q_cell, prefix, field, a_cell, vm_range, key in field_map:
        items.append({
            "question_cell": q_cell,
            "prefix": prefix,
            "field": field,
            "answer_cell": a_cell,
            "value": product_info.get(key),
            "field_merged": field == "Description",
            "fm_range": "A6" if field == "Description" else None,
            "value_merged": True,
            "vm_range": vm_range,
            "task_type": "extraction",
            "user_editable": True,
            "ai_fillable": True,
            "accuracy_level": True,
            "text_support": [
                                {
                                    "filename": f"final_output_{configs._runtime.project_id}.docx",
                                    "page": "7" if field == "Description" else "2",
                                    "similarity_score": None,
                                    "preview_text": None,
                                    "url":  trf_blob_url
                                }
                            ],
            "confidence": 0 if product_info.get(key) == None else 100,
        })

    return items





def description_main(vs,ref):
    configs.require_runtime()
    prompt_refine_product = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an assistant that converts raw TRF fields into the final
    Section 2.0 'Product Description' for a CDR form.
    Use ONLY the information in the provided JSON. Do not invent facts.

    The input JSON (called `ref`) can contain keys like:
    - "Test item description"
    - "Trade mark"
    - "General product information and other remarks"
    - "Model/Type reference"
    - "Description of model differences"
    - "Ratings"
    and possibly others.

    You must output ONE JSON object with exactly these keys:
    - "product"
    - "brand_name"
    - "description"
    - "models"
    - "model_similarity"
    - "ratings"
    - "other_ratings"

    Mapping + refinement rules:
    - product: copy from "Test item description" (trimmed) if present, else null.
    - brand_name: from "Trade mark" or "applicant's name"
        If it is missing, empty, or equivalent to 'none', 'na', 'n/a', etc,
        set brand_name to the string "NA".
    - description: mainly from "General product information and other remarks".
        Clean up line-breaks and bullets so it becomes one readable paragraph.
    - models: from "Model/Type reference".
    - model_similarity: from "Description of model differences".
        If that text basically says there is only one model or no
        differences (e.g. "N/A – One model", "N/A", "None", "no differences"),
        then use the string "NA" instead.
    - ratings: take the "Ratings" field and keep ONLY:
        * AC supply voltage ranges (e.g. 100-240VAC, 230VAC)
        * Supply frequency (e.g. 50Hz, 60Hz, 50/60Hz)
        * DC output voltages relevant to the equipment (e.g. 48VDC)
    Format them as one short comma-separated string, with no extra prose.
    - other_ratings:
        Follow this rule exactly:
        * If there is no other type of ratings beyond what you used in "ratings",
            set other_ratings to the exact string "NA" (without quotation marks).
        * Otherwise include any additional rating information such as gas, oil,
            steam, or other application-specific ratings according to the respective
            standards in section 1.0, as one short phrase or sentence.

    All values MUST be strings (or null only where described above).
    Do NOT add any extra keys. Do NOT add explanation text.
    Return ONLY the JSON object."""
            ),
            (
                "human",
                "Here is the raw TRF dictionary `ref` as JSON:\n\n{ref_json}",
            ),
        ]
    )

    refine_product_chain = prompt_refine_product | configs.llm | StrOutputParser()

    ref_dict = ref
    ref_json = json.dumps(ref_dict, indent=2)

    raw_product_json = refine_product_chain.invoke({"ref_json": ref_json})
    product_info = json.loads(raw_product_json)

    return product_info


