import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from urllib.parse import unquote
import os

# Config values (created earlier in config.py)
# from config import *

# LLM and langchain imports
from langchain_openai import AzureChatOpenAI

# Import helpers from your essentials file when available
# build_rag_image_pipeline_grey is defined in trf_essentials (per your file)
from utility.trf_report.trf_essential import *


# NOTE: Many functions are repeated between trf_essentials and the notebook.
# Per your instruction, we keep the notebook versions here and expect duplicates
# in trf_essentials to be removed by you or later.

# -----------------------
# build_vision_message_grey
# -----------------------

# import json

# with open("image_urls.json", "r") as f:
#     image_urls = json.load(f)


# from trf_utils import build_vectorstore, build_embeddings
# from azure.cosmos import CosmosClient, ConsistencyLevel

# client = CosmosClient(COSMOS_URL, credential=COSMOS_KEY, consistency_level=ConsistencyLevel.Eventual)

# embeddings = build_embeddings(AOAI_ENDPOINT, AOAI_KEY, API_VERSION, EMBED_DEPLOY)

# vs = build_vectorstore(
#     embeddings,
#     client,
#     DB_NAME,
#     CONT_NAME
# )


# Chunking config
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
EMBED_DIM = 1536
VECTOR_PATH = "/vector"
TOP_K = 5


# Load environment variables
AOAI_ENDPOINT      = os.getenv("AOAI_ENDPOINT")
AOAI_KEY           = os.getenv("AOAI_KEY")
API_VERSION        = os.getenv("API_VERSION")
EMBED_DEPLOY       = os.getenv("EMBED_DEPLOY")
DB_NAME            = os.getenv("DB_NAME")
CONT_NAME          = os.getenv("CONT_NAME")
AZURE_CONN_STRING  = os.getenv("AZURE_CONN_STRING")
COSMOS_URL         = os.getenv("COSMOS_URL")
COSMOS_KEY         = os.getenv("COSMOS_KEY")
CHAT_DEPLOY        = os.getenv("CHAT_DEPLOY")



def build_vision_message_grey(inputs, grey=False):
    """
    Build vision message used by AzureChatOpenAI with image_url blocks.
    Same implementation as in your notebook.
    """
    question = inputs.get("question", "")
    docs = inputs.get("context", [])
    image_urls = inputs.get("image", [])
    custom_prompt = inputs.get("custom_prompt")
    task_type = (inputs.get("task_type") or inputs.get("prompt_type") or "extract").lower()
    accuracy_level = bool(inputs.get("accuracy_level", False))

    context_text = "".join([d.page_content for d in docs])

    guideline_reference = """
    You must obey these grounding rules at all times.
    1. No guessing - If the requirement of a clause is not explicitly available in the TRF Text and the provided images, you must NOT infer it.
    2. However you can use your judgement and expertse as an electrical safety compliance engineer to give the responses.
    3. IEC 61010-1 should guide interpretation only
    Do not copy text from the IEC standard.
    Do not restate entire requirement wording.
    Only verify compliance based on input facts.
    4. Every remark must be evidence-based as applicable
    """

    if custom_prompt and str(custom_prompt).strip():
        active_prompt = custom_prompt.strip()
    else:
        active_prompt = question

    if grey and not accuracy_level:
        system_prompt = f"""
You are assisting with determining whether relevant information exists in the TRF content.

Please provide your answer in this JSON format:
{{
  "response": "TBD - Info available" | "TBD - No info available",
  "confidence": <0-100>
}}

Use ONLY the TRF text and images. NEVER copy or paraphrase IEC text.

TRF TEXT CONTEXT:
{context_text}

QUESTION:
{active_prompt}
""".strip()
    else:
        if task_type == "remark":
            instruction_block = """
Provide ONLY the following JSON keys:
1. "response": A concise evidence-driven remark (Max 10 words) based on the information obtained from input files in accordance to the clause provided in the IEC Standard 61010-1
2. "confidence": Generate a confidence score with Integer values ranging from 1 - 100 by comparing the LLM response with the retrieved evidence from TRF text & input images and the requirement of the clause provided in the IEC Standard 61010-1

Remark Rules:

Follow this decision framework for generating responses for remark:
If TRF Text and Input images provide relevant information with respect to the task, then give a concise evidence-driven remark (Max 10 words) in accordance to the clause provided in the IEC Standard 61010-1
If the component or feature or clause is not present in the equipment or if not applicable to the equipment, then provide a remark confirming the same
If any critical information is missing in the input files, then give a remark highlighting that crtical information is not available in the documentation
If no decision can still be made based on the framework (mentioned above), then keep remark as blank. 
"""
        elif task_type == "verdict":
            instruction_block = """
Provide ONLY the following JSON keys:
1. "response": one of "P", " ", or "N/A"
2. "confidence": Generate a confidence score with Integer values ranging from 1 - 100 by comparing the LLM response with the 
retrieved evidence from TRF text & input images and the requirement of the clause provided in the IEC Standard 61010-1

Verdict Rules:

Follow this decision framework for generating responses for Verdict:
P = Pass only when evidence in the TRF text and Input images is in accordance to the clause mentioned in IEC Standard 61010-1
N/A =  If the equipment does not include the feature or component or the clause is not applicable to the equipment in the TRF text and input images
as referenced in the IEC Standard 61010-1
"""
        else:
            instruction_block = """
Provide ONLY the following JSON keys:
1. "response": concise extracted answer (max 10 words unless specified in the task)
2. "confidence": Generate a confidence score with Integer values ranging from 1 - 100 by comparing the LLM response with the retrieved evidence from TRF text & input images and the requirement of the clause provided in the IEC Standard 61010-1
"""

        system_prompt = f"""
You are an expert electrical safety compliance engineer specializing in IEC 61010-1:2010 & IEC 61010-1:2010/AMD1:2016. 
You can generate the responses using the TRF text and the provided images which includes the images of the equipment and the marking label. 
You shall NOT invent values or assume characteristics not found in the input files, however you can use your judgement and expertse as an electrical safety compliance engineer to give the responses. 
IEC 61010-1 can only be used as a guideline to understand the requirement of the clauses, NOT as a content source.

{guideline_reference}

TASK:
{active_prompt}

OUTPUT FORMAT:
{instruction_block}

TRF TEXT CONTEXT (DO NOT rewrite, only reason over):
{context_text}
""".strip()

    content_blocks = [{"type": "text", "text": system_prompt}]

    for img in image_urls:
        if isinstance(img, dict) and "url" in img:
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": img["url"]}
            })
        elif isinstance(img, str):
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": img}
            })

    return [{"role": "user", "content": content_blocks}]


# -----------------------
# build_tasks_with_custom_prompt_grey
# -----------------------

def build_tasks_with_custom_prompt_grey(data, image_urls):
    tasks = []
    item_refs = []

    for table in data.get("Tables", []):
        for item in table.get("Items", []):
            if not item.get("ai_fillable"):
                continue

            custom = item.get("custom_prompt", "")
            accuracy = bool(item.get("accuracy_level", False))

            if "grey" in item:
                grey_flag = bool(item.get("grey"))
            else:
                grey_flag = not accuracy

            if custom and str(custom).strip() != "":
                modified_question = custom.strip()
            else:
                task_type = str(item.get("task_type", "")).strip().lower()
                field = item.get("field", "")
                if task_type == "verdict":
                    modified_question = (
                        "Give the verdict as Pass, Fail, or N/A only."
                        f"{field}"
                    )
                else:
                    modified_question = field

            tasks.append({
                "question": modified_question,
                "image": image_urls,
                "task_type": item.get("task_type"),
                "custom_prompt": custom,
                "accuracy_level": accuracy,
                "grey": grey_flag
            })

            item_refs.append(item)

    return tasks, item_refs


# -----------------------
# update_json_item_grey
# -----------------------

def normalize_verdict(value):
    if not isinstance(value, str):
        return "N/A"
    v = value.strip().lower()
    if v.startswith("p"):
        return "P"
    if v.startswith("f"):
        return "F"
    return "N/A"


def update_json_item_grey(item, result):
    if not item.get("ai_fillable", False):
        return

    raw_answer = result.get("answer", "")
    try:
        parsed = json.loads(raw_answer)
    except Exception:
        parsed = {}

    response = parsed.get("response")
    confidence = parsed.get("confidence", 0)

    if response is None:
        response = raw_answer

    if isinstance(response, str) and response.strip() == "":
        response = parsed.get("fallback", None) or "Not available"

    response = str(response).strip()

    grey_mode = result.get("grey_mode", False)

    if response.replace(" ", "").startswith("TBD"):
        item["value"] = response
        item["confidence"] = confidence
        item["text_support"] = result.get("text_support", [])
        item["image_support"] = result.get("image_support", [])
        item["similarity_query"] = result.get("similarity_query")
        item["vector_search_based_on"] = result.get("vector_search_based_on")
        return

    task_type = item.get("task_type")

    if task_type in ("remark", "extraction", "extract", "custom", None):
        item["value"] = response
    elif task_type == "verdict":
        item["value"] = normalize_verdict(response)

    item["confidence"] = confidence
    item["text_support"] = result.get("text_support", [])
    item["image_support"] = result.get("image_support", [])
    item["similarity_query"] = result.get("similarity_query")
    item["vector_search_based_on"] = result.get("vector_search_based_on")


# -----------------------
# process_tasks_with_batches_parallel_grey
# -----------------------


def process_tasks_with_batches_parallel_grey(
        tasks,
        item_refs,
        rag_image,
        vs,
        batch_size=150,
        cooldown_sec=15,
        max_workers=6,
        use_llm_inGrey=False,
        stats=False,
        progress_callback=None
    ):

    total = len(tasks)
    processed = 0
    all_results = []

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_total_tokens = 0
    total_llm_calls = 0

    def handle_low_accuracy_item(item, task, vs, k=5):
        if use_llm_inGrey:
            return False
        if task.get("accuracy_level", True):
            return False

        question = task["question"]
        try:
            scored_results = vs.similarity_search_with_score(question, k=k)
        except Exception:
            scored_results = []

        text_sources = []
        for doc, score in scored_results:
            text_sources.append({
                "filename": doc.metadata.get("source_file", "unknown"),
                "page": doc.metadata.get("page"),
                "similarity_score": float(score),
                "text": doc.page_content[:].strip()
            })

        has_info = any(score > 0.70 for doc, score in scored_results)
        value = "TBD-Info available" if has_info else "TBD-Info not available"

        item["value"] = value
        item["confidence"] = 0
        item["text_support"] = text_sources
        item["image_support"] = []
        item["similarity_query"] = question
        item["vector_search_based_on"] = "question"

        return True

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = tasks[start:end]
        ref_batch = item_refs[start:end]

        print(f"🔵 Starting batch: {start+1} → {end}")

        future_to_index = {}

        with ThreadPoolExecutor(max_workers=max_workers) as exe:
            for idx, task in enumerate(batch):
                if stats:
                    future = exe.submit(run_single_task_stats, task, rag_image)
                else:
                    future = exe.submit(run_single_task, task, rag_image)
                future_to_index[future] = idx

            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                task = batch[idx]
                item = ref_batch[idx]

                handled = handle_low_accuracy_item(item, task, vs)
                if handled:
                    processed += 1
                    print(f"Processed {processed}/{total} (vector-only grey mode)")
                    if progress_callback:
                        progress_callback(processed, total)
                    continue

                result = future.result()

                if stats and "_token_usage" in result:
                    usage = result["_token_usage"]
                    total_prompt_tokens += usage.get("prompt", 0)
                    total_completion_tokens += usage.get("completion", 0)
                    total_total_tokens += usage.get("total", 0)
                    total_llm_calls += 1

                result["question"] = task["question"]
                result["task_type"] = task["task_type"]

                update_json_item_grey(item, result)

                all_results.append(result)
                processed += 1
                print(f"Processed {processed}/{total}")
                if progress_callback:
                    progress_callback(processed, total)

        if end < total:
            print(f"⏳ Cooling down for {cooldown_sec} seconds...")
            time.sleep(cooldown_sec)

    print("✅ ALL TASKS COMPLETED.")

    if stats:
        return {
            "results": all_results,
            "stats": {
                "total_llm_calls": total_llm_calls,
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "total_tokens": total_total_tokens,
            }
        }

    return all_results


# -----------------------
# results_to_dataframe
# -----------------------

def results_to_dataframe(results):
    rows = []
    for result in results:
        raw_answer = result.get("answer", "")
        parsed = {}
        try:
            parsed = json.loads(raw_answer)
        except Exception:
            parsed = {}

        row = {
            "question": result.get("question"),
            "task_type": result.get("task_type"),
            "response": parsed.get("response"),
            "confidence": parsed.get("confidence"),
            "source_detected": result.get("source_detected"),
            "text_support": result.get("text_support"),
            "image_support": result.get("image_support"),
        }
        rows.append(row)
    import pandas as pd
    return pd.DataFrame(rows)


# -----------------------
# update_docx_tables_from_json_arial
# -----------------------
from docx import Document as DocxDocument
from docx.shared import Pt
from docx.oxml.ns import qn


def update_docx_tables_from_json_arial(docx_path, json_path, output_path):
    doc = DocxDocument(docx_path)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for table_obj in data.get("Tables", []):
        table_index = table_obj.get("Table")
        if table_index >= len(doc.tables):
            print(f"⚠️ Skipping missing table index: {table_index}")
            continue

        doc_table = doc.tables[table_index]

        for item in table_obj.get("Items", []):
            ai_fillable = item.get("ai_fillable", False)
            task_type = item.get("task_type")
            if not ai_fillable and task_type != "verdict_dependency":
                continue

            row = item.get("answer_row")
            col = item.get("answer_column")
            value = item.get("value")
            if value is None:
                continue

            try:
                cell = doc_table.cell(row, col)
                cell.text = ""
                paragraph = cell.paragraphs[0]
                run = paragraph.add_run(str(value))
                font = run.font
                font.name = "Arial"
                font.size = Pt(10)
                run._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
            except Exception as e:
                print(f"⚠️ Error updating table {table_index} cell ({row},{col}): {e}")

    doc.save(output_path)
    print(f"✅ DOCX successfully updated → {output_path}")


# -----------------------
# Main runner
# -----------------------
def attach_blob_urls_to_text_support(data, blob_urls):
    """
    Adds 'url' to each text_support item by matching filename
    WITHOUT considering file extension.
    """

    # Build base-name → url lookup
    blob_map = {}
    for url in blob_urls:
        fname = unquote(url.split("/")[-1])
        base = os.path.splitext(fname)[0]
        blob_map.setdefault(base, url)   # keep first match

    for table in data.get("Tables", []):
        for item in table.get("Items", []):
            for ts in item.get("text_support", []):
                ts["url"] = None
                fname = ts.get("filename")
                if not fname:
                    continue

                base = os.path.splitext(fname)[0]
                ts["url"] = blob_map.get(base)
    
    return data

def attach_blob_urls_to_image_support(data, blob_urls):
    """
    Adds 'file_url' to each image_support item
    by matching pdf_file name WITHOUT extension.
    """

    # Build base-name → url lookup
    blob_map = {}
    for url in blob_urls:
        fname = unquote(url.split("/")[-1])
        base = os.path.splitext(fname)[0]
        blob_map.setdefault(base, url)

    for table in data.get("Tables", []):
        for item in table.get("Items", []):
            for img in item.get("image_support", []):
                img["file_url"] = None
                pdf_file = img.get("pdf_file")
                if not pdf_file:
                    continue

                base = os.path.splitext(pdf_file)[0]
                img["file_url"] = blob_map.get(base)

    return data
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
# embeddings = build_embeddings(AOAI_ENDPOINT, AOAI_KEY, API_VERSION, EMBED_DEPLOY)
from langchain_azure_ai.vectorstores import AzureCosmosDBNoSqlVectorSearch
# Build embeddings for retriever
embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=AOAI_ENDPOINT,
    api_key=AOAI_KEY,
    openai_api_version=API_VERSION,
    azure_deployment=EMBED_DEPLOY,
)

# Build Cosmos client
cosmos_client = CosmosClient(
    COSMOS_URL,
    credential=COSMOS_KEY
)

# MUST MATCH INGESTION EXACTLY
vs = AzureCosmosDBNoSqlVectorSearch(
    cosmos_client=cosmos_client,
    embedding=embeddings,
    database_name=DB_NAME,
    container_name=CONT_NAME,

    # REQUIRED keyword-only args
    vector_embedding_policy={
        "vectorEmbeddings": [
            {
                "path": VECTOR_PATH,
                "dataType": "float32",
                "dimensions": EMBED_DIM,
                "distanceFunction": "cosine",
            }
        ]
    },

    indexing_policy={
        "includedPaths": [{"path": "/*"}],
        "excludedPaths": [
            {"path": "/\"_etag\"/?"}, 
            {"path": f"{VECTOR_PATH}/*"}
        ],
        "vectorIndexes": [
            {"path": VECTOR_PATH, "type": "quantizedFlat"}
        ],
    },

    cosmos_container_properties={"partition_key": "/id"},
    cosmos_database_properties={},

    vector_search_fields={
        "text_field": "text",
        "embedding_field": "vector",
        "metadata_field": "metadata",
    }
)
def run_trf_generation(
        blob_urls,
        vs,
        image_urls,
        input_json_path: str,
        docx_input_path: str,
        output_json_path: str,
        output_docx_path: str,
        output_excel_path: str,
        batch_size: int = 150,
        cooldown_sec: int = 15,
        max_workers: int = 10,
        use_llm_inGrey: bool = False,
        stats: bool = False,
        progress_callback=None,
    ):

    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    llm_itk = AzureChatOpenAI(
        azure_endpoint=AOAI_ENDPOINT,
        api_key=AOAI_KEY,
        openai_api_version=API_VERSION,
        azure_deployment=CHAT_DEPLOY,
        temperature=0.1,
    ).with_config({"response_format": "verbose"})

    llm2 = AzureChatOpenAI(
        azure_endpoint=AOAI_ENDPOINT,
        api_key=AOAI_KEY,
        openai_api_version=API_VERSION,
        azure_deployment=CHAT_DEPLOY,
        temperature=0,
    ).with_config({"response_format": "verbose"})

    retriever = vs.as_retriever(search_kwargs={"k": 5})

    rag_image = build_rag_image_pipeline_grey(
        retriever,
        llm_itk,
        llm2,
        build_vision_message_grey,
        attach_supporting_refs_grey if 'attach_supporting_refs_grey' in globals() else None,
        vs
    )

    tasks, item_refs = build_tasks_with_custom_prompt_grey(data, image_urls)
    # tasks=tasks[:15]
    # item_refs=item_refs[:15]
    results = process_tasks_with_batches_parallel_grey(
        tasks,
        item_refs,
        rag_image,
        vs,
        batch_size=batch_size,
        cooldown_sec=cooldown_sec,
        max_workers=max_workers,
        use_llm_inGrey=use_llm_inGrey,
        stats=stats,
        progress_callback=progress_callback
    )

    if isinstance(results, dict) and "results" in results:
        res_list = results["results"]
    else:
        res_list = results

    df = results_to_dataframe(res_list)

    try:
        df.to_excel(output_excel_path, index=False)
    except Exception:
        pass

    update_verdict_dependencies(data)
    data=attach_blob_urls_to_text_support(data, blob_urls)

    data=attach_blob_urls_to_image_support(data, blob_urls)


    try:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    try:
        update_docx_tables_from_json_arial(docx_input_path, output_json_path, output_docx_path)
    except Exception:
        pass

    return {
        "results": res_list,
        "stats": results.get("stats") if isinstance(results, dict) else None,
        "output_json": output_json_path,
        "output_docx": output_docx_path,
        "output_excel": output_excel_path
    }



# if __name__ == "__main__":

#     print("\n🚀 Starting TRF Generation Pipeline...\n")

#     # ----------------------------------------------------
#     # 1️⃣ Load IMAGE URLs saved from ingestion step
#     # ----------------------------------------------------
#     import json

#     IMAGE_URLS_PATH = "image_urls.json"  # adjust if needed

#     try:
#         with open(IMAGE_URLS_PATH, "r") as f:
#             image_urls = json.load(f)
#         print(f"✔ Loaded {len(image_urls)} image URLs from ingestion.")
#     except FileNotFoundError:
#         print("❌ ERROR: image_urls.json not found. Run ingestion_pipeline.py first.")
#         exit(1)


#     print("🔧 Initializing Cosmos + Vectorstore...")

#     client = CosmosClient(COSMOS_URL, credential=COSMOS_KEY,
#                           consistency_level=ConsistencyLevel.Eventual)

#     embeddings = build_embeddings(AOAI_ENDPOINT, AOAI_KEY, API_VERSION, EMBED_DEPLOY)

#     vs = build_vectorstore(
#         embeddings=embeddings,
#         client=client,
#         DB_NAME=DB_NAME,
#         CONT_NAME=CONT_NAME
#     )

#     print("✔ Vectorstore loaded from Cosmos DB.")

#     # ----------------------------------------------------
#     # 3️⃣ DEFINE INPUT + OUTPUT FILES
#     # ----------------------------------------------------
#     INPUT_JSON_PATH = "pta_final_5.json"
#     INPUT_DOCX_PATH = "input.docx"

#     OUTPUT_JSON = "iec_output.json"
#     OUTPUT_DOCX = "iec_output.docx"
#     OUTPUT_EXCEL = "iec_output.xlsx"

#     # ----------------------------------------------------
#     # 4️⃣ RUN TRF GENERATION
#     # ----------------------------------------------------
#     from trf_generation import run_trf_generation  # self-import allowed

#     result = run_trf_generation(
#         vs=vs,
#         image_urls=image_urls,
#         input_json_path=INPUT_JSON_PATH,
#         docx_input_path=INPUT_DOCX_PATH,
#         output_json_path=OUTPUT_JSON,
#         output_docx_path=OUTPUT_DOCX,
#         output_excel_path=OUTPUT_EXCEL,
#         batch_size=150,
#         cooldown_sec=15,
#         max_workers=10,
#         use_llm_inGrey=False,
#         stats=True
#     )

#     print("\n🎉 TRF Generation Completed Successfully!")
#     print(f"📄 Output JSON : {OUTPUT_JSON}")
#     print(f"📄 Output DOCX : {OUTPUT_DOCX}")
#     print(f"📄 Output XLSX : {OUTPUT_EXCEL}")

