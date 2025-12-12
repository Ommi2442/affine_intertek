import re
import tempfile
import shutil
import requests
from urllib.parse import urlparse, unquote
from email import policy
from email.parser import BytesParser
import extract_msg
import uuid
from langchain_core.documents import Document
import io
import openpyxl
import xlrd
# from utils import *
from azure.storage.blob import BlobClient
from azure.core.exceptions import ResourceNotFoundError, AzureError
# from templates import *
import pandas as pd
import math
import copy
import time
import docx2pdf
from azure.cosmos import CosmosClient, PartitionKey, exceptions
import json, os
from azure.cosmos import CosmosClient, ConsistencyLevel
from typing import List, Dict, Any, Tuple
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_azure_ai.vectorstores import AzureCosmosDBNoSqlVectorSearch
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from azure.cosmos import CosmosClient
from langchain_openai import AzureOpenAIEmbeddings
from operator import itemgetter
from langchain_core.runnables import (
    RunnableParallel, RunnableLambda, RunnableMap
)
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_never, RetryCallState
from openai import RateLimitError  # Make sure this import exists
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor, as_completed
from azure.core.exceptions import HttpResponseError
import time
from langchain_community.callbacks import get_openai_callback
from langchain_core.runnables import (
    RunnableParallel, RunnableMap, RunnableLambda, RunnablePassthrough
)
from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser



pd.set_option('display.max_colwidth', None)  # Don't truncate cell text
pd.set_option('display.max_rows', None)      # Show all rows (optional)
pd.set_option('display.max_columns', None) 

def classify_source(answer, context_text, llm_classifier):
    """
    Classifies whether the answer relies on:
    - text
    - image
    - both
    """

    prompt = f"""
You are a classifier. Your job is to decide the source of the answer.

ANSWER:
{answer}

TEXT CONTEXT (retrieved):
{context_text}

Rules:
- If the key facts in ANSWER exist in TEXT CONTEXT -> "text"
- If the key facts in ANSWER exist only in the image -> "image"
- If both contain the supporting facts -> "both"
- If unsure -> choose the most likely

Reply with exactly one word:
text
image
both
"""

    resp = llm_classifier.invoke([{
        "role": "user",
        "content": prompt
    }])

    return resp.content.strip().lower()



# def attach_supporting_refs(docs, image_urls, llm_output, llm_classifier, vs, k=5):
#     # ---------------------------------------------------
#     # Build full context text for classification
#     # ---------------------------------------------------
#     context_text = "\n".join([d.page_content for d in docs])

#     # STEP 1: Classify whether the answer came from text / image / both
#     source = classify_source(llm_output, context_text, llm_classifier)

#     text_sources = []
#     image_sources = []

#     # ---------------------------------------------------
#     # STEP 2: Retrieve top-k similar text chunks via cosine similarity
#     # ---------------------------------------------------
#     try:
#         scored_results = vs.similarity_search_with_score(llm_output, k=k)
#         # scored_results → list of (Document, score)
#     except Exception as e:
#         scored_results = []
#         print("Vector search failed:", str(e))

#     # ---------------------------------------------------
#     # STEP 3: Add text chunks + similarity scores
#     # ---------------------------------------------------
#     if source in ("text", "both"):
#         for doc, score in scored_results:
#             filename = doc.metadata.get("source_file", "unknown")
#             page = doc.metadata.get("page", None)
#             preview = doc.page_content[:500].strip()

#             text_sources.append({
#                 "filename": filename,
#                 "page": page,
#                 "similarity_score": float(score),   # cosine distance or similarity
#                 "text": preview
#             })

#     # ---------------------------------------------------
#     # STEP 4: Add image references
#     # ---------------------------------------------------
#     if source in ("image", "both"):
#         for url in image_urls:
#             image_sources.append({
#                 "filename": url.split("/")[-1],
#                 "url": url
#             })

#     # ---------------------------------------------------
#     # STEP 5: Return final structured output
#     # ---------------------------------------------------
#     return {
#         "answer": llm_output,
#         "source_detected": source,
#         "text_support": text_sources,
#         "image_support": image_sources
#     }




## CAD and Schematic Support

def attach_supporting_refs_grey(
        docs,
        image_urls,
        llm_output,
        llm_classifier,
        vs,
        accuracy_level=None,
        grey=False,
        question=None,
        k=5):

    """
    Attaches both text and image supporting references.
    Image references now include:
        - pdf_file
        - page number
        - blob url
    """

    # ---------------------------------------------------
    # STEP 1 — Build full context text
    # ---------------------------------------------------
    context_text = "\n".join([d.page_content for d in docs])

    # Detect whether answer depends on: text / image / both
    source = classify_source(llm_output, context_text, llm_classifier)

    text_sources = []
    image_sources = []

    # ---------------------------------------------------
    # STEP 2 — Similarity search (using QUESTION, not answer)
    # ---------------------------------------------------
    similarity_query = question.strip() if question else llm_output.strip()

    try:
        scored_results = vs.similarity_search_with_score(similarity_query, k=k)
    except Exception as e:
        print("Vector search failed:", str(e))
        scored_results = []

    # ---------------------------------------------------
    # STEP 3 — Add text references (top-k from vector search)
    # ---------------------------------------------------
    for doc, score in scored_results:
        text_sources.append({
            "filename": doc.metadata.get("source_file", "unknown"),
            "page": doc.metadata.get("page"),
            "similarity_score": float(score),
            "text": doc.page_content[:].strip()
        })

    # ---------------------------------------------------
    # STEP 4 — Add image references (PDF images)
    # ---------------------------------------------------
    if source in ("image", "both"):

        for img in image_urls:

            # NEW FORMAT: dict from upload_pdf_images_and_append_urls
            if isinstance(img, dict) and "url" in img:
                image_sources.append({
                    "pdf_file": img.get("pdf_file", "unknown"),
                    "page": img.get("page"),
                    "image_file": img.get("image_file"),
                    "url": img["url"]
                })

            # OLD FORMAT (string-only URL)
            elif isinstance(img, str):
                image_sources.append({
                    "pdf_file": None,
                    "page": None,
                    "image_file": img.split("/")[-1],
                    "url": img
                })

    # ---------------------------------------------------
    # FINAL STRUCTURED OUTPUT
    # ---------------------------------------------------
    return {
        "answer": llm_output,
        "source_detected": source,
        "similarity_query": similarity_query,
        "vector_search_based_on": "question",

        "text_support": text_sources,
        "image_support": image_sources,

        "accuracy_level": accuracy_level,
        "grey_mode": grey
    }


## CAD and Schematic Support

def build_rag_image_pipeline_grey(retriever, llm, llm2, build_vision_message, attach_supporting_refs, vs):
    from langchain_core.runnables import (
        RunnableParallel, RunnableMap, RunnableLambda, RunnablePassthrough
    )
    from operator import itemgetter
    from langchain_core.output_parsers import StrOutputParser

    rag_image = (
        # --------------------------------------------------------
        # STEP 1 — Retrieve context + pass through key fields
        # --------------------------------------------------------
        RunnableParallel(
            context=itemgetter("question") | retriever,
            question=itemgetter("question"),
            image=itemgetter("image"),
            task_type=itemgetter("task_type"),
            custom_prompt=itemgetter("custom_prompt"),
            accuracy_level=itemgetter("accuracy_level"),
            grey=itemgetter("grey"),
        )

        # --------------------------------------------------------
        # STEP 2 — Build LLM vision messages
        # --------------------------------------------------------
        | RunnableMap({
            "inputs": RunnablePassthrough(),
            "messages": lambda x: build_vision_message(
                # x,
                # grey=x.get("grey", False)
                {
                **x,
                "image": [
                    img["url"] if isinstance(img, dict) else img
                    for img in x["image"]
                    ]
                },
                grey=x.get("grey", False)
                        )
        })

        # --------------------------------------------------------
        # STEP 3 — Run LLM on prepared messages
        # --------------------------------------------------------
        | RunnableMap({
            "inputs": itemgetter("inputs"),
            "llm_output": (
                itemgetter("messages")
                | llm
                | StrOutputParser()
            )
        })

        # --------------------------------------------------------
        # STEP 4 — Attach supporting references
        # --------------------------------------------------------
        | RunnableLambda(
            lambda x: {
                **attach_supporting_refs(
                    docs=x["inputs"]["context"],
                    image_urls=x["inputs"]["image"],
                    llm_output=x["llm_output"],
                    llm_classifier=llm2,
                    vs=vs,
                    accuracy_level=x["inputs"]["accuracy_level"],
                    grey=x["inputs"]["grey"],
                    question=x["inputs"]["question"]     # ⭐ REQUIRED for similarity scores
                ),
                "question": x["inputs"]["question"],
                "task_type": x["inputs"]["task_type"],
                "custom_prompt": x["inputs"]["custom_prompt"],
                "accuracy_level": x["inputs"]["accuracy_level"],
                "grey": x["inputs"]["grey"]
            }
        )
    )

    return rag_image



def build_tasks_with_custom_prompt(data, image_urls):
    tasks = []
    item_refs = []

    for table in data["Tables"]:
        for item in table["Items"]:

            if not item.get("ai_fillable"):
                continue

            # ---------------------------------------------
            # PRIORITY #1 — custom prompt overrides all
            # ---------------------------------------------
            if "custom_prompt" in item and item["custom_prompt"]:
                modified_question = f"{item['custom_prompt']}\n{item['field']}"

            # ---------------------------------------------
            # PRIORITY #2 — normal logic (remark / verdict)
            # ---------------------------------------------
            else:
                if item["task_type"] == "verdict":
                    modified_question = (
                        "Give the verdict as Pass, Fail, or N/A only.\n"
                        f"{item['field']}"
                    )
                else:
                    modified_question = item["field"]

            tasks.append({
                "question": modified_question,
                "image": image_urls,
                "task_type": item["task_type"],
                "custom_prompt": item.get("custom_prompt")
            })

            item_refs.append(item)

    return tasks, item_refs




def print_retry_details(retry_state: RetryCallState):
    exception = retry_state.outcome.exception()
    wait_time = retry_state.next_action.sleep

    print(f"\n⚠️ Rate limit hit. Retrying attempt #{retry_state.attempt_number} in {wait_time:.1f} seconds...")
    print(f"   → Error: {exception}\n")


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_never,   # Never stop, retry until available
    wait=wait_exponential(multiplier=2, min=5, max=300),
    before_sleep=print_retry_details
)
def run_single_task(task,rag_image):
    return rag_image.invoke(task)


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_never,   # Never stop, retry until available
    wait=wait_exponential(multiplier=2, min=5, max=300),
    before_sleep=print_retry_details
)
def run_single_task_stats(task, rag_image):
    with get_openai_callback() as cb:
        response = rag_image.invoke(task)
    
    response["_token_usage"] = {
        "prompt": cb.prompt_tokens,
        "completion": cb.completion_tokens,
        "total": cb.total_tokens
    }
    return response

# def run_single_task_stats(task,rag_image):
#     response = rag_image.invoke(task)

#     # Track tokens
#     usage = response.get("usage", {})

#     response["_token_usage"] = {
#         "prompt": usage.get("prompt_tokens", 0),
#         "completion": usage.get("completion_tokens", 0),
#         "total": usage.get("total_tokens", 0),
#     }

#     return response


def normalize_verdict(value):
    if not isinstance(value, str):
        return "N/A"

    v = value.strip().lower()

    if v.startswith("p"):
        return "P"
    if v.startswith("f"):
        return "F"
    return "N/A"




def update_json_item(item, result):
    # Skip items that should not be modified
    if not item.get("ai_fillable", False):
        return

    raw_answer = result.get("answer", "")
    
    # -----------------------------------------
    #   PARSE JSON SAFELY
    # -----------------------------------------
    try:
        parsed = json.loads(raw_answer)
    except Exception:
        parsed = {}

    response = parsed.get("response")
    confidence = parsed.get("confidence", 0)

    # -----------------------------------------
    #   FIX EMPTY OR MISSING RESPONSE
    # -----------------------------------------
    # Case 1: response key missing → fallback to raw_answer
    if response is None:
        response = raw_answer

    # Case 2: response is empty string → LLM failed under parallel load
    if isinstance(response, str) and response.strip() == "":
        # Fallback rule:
        # 1. If custom prompt expected a descriptive answer → "Not available"
        # 2. If extraction field → try fallback to raw LLM text
        response = parsed.get("fallback", None) or "Not available"

    # Final cleanup
    if not isinstance(response, str):
        response = str(response)

    response = response.strip()

    # -----------------------------------------
    #  UPDATE VALUE BASED ON TASK TYPE
    # -----------------------------------------

    task_type = item.get("task_type")

    # For remark/extraction/custom → direct assignment
    if task_type in ("remark", "extraction", "extract", "custom", None):
        item["value"] = response

    elif task_type == "verdict":
        item["value"] = normalize_verdict(response)

    # -----------------------------------------
    #  CONFIDENCE AND SUPPORT INFO
    # -----------------------------------------
    item["confidence"] = confidence
    item["text_support"] = result.get("text_support", [])
    item["image_support"] = result.get("image_support", [])


import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def process_tasks_with_batches_parallel(
        tasks,
        item_refs,          # ⬅ add this
        rag_image,
        batch_size=150,
        cooldown_sec=15,
        max_workers=6):

    total = len(tasks)
    processed = 0
    all_results = []

    # -----------------------------------------
    #  Process in batches
    # -----------------------------------------
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = tasks[start:end]
        ref_batch = item_refs[start:end]   # match items to tasks

        print(f"\n🔵 Starting batch: {start+1} → {end}")

        future_to_index = {}

        # -----------------------------------------
        # PARALLEL EXECUTION
        # -----------------------------------------
        with ThreadPoolExecutor(max_workers=max_workers) as exe:

            for idx, task in enumerate(batch):
                future = exe.submit(run_single_task, task,rag_image)
                future_to_index[future] = idx

            for future in as_completed(future_to_index):

                idx = future_to_index[future]
                task = batch[idx]
                item = ref_batch[idx]   # ← JSON ITEM

                result = future.result()

                # Attach metadata
                result["question"] = task["question"]
                result["task_type"] = task["task_type"]

                # Save result for later if needed
                all_results.append(result)

                # -----------------------------------------
                #     UPDATE JSON ITEM HERE
                # -----------------------------------------
                update_json_item(item, result)

                processed += 1
                print(f"Processed {processed}/{total} tasks...")

        # -----------------------------------------
        # COOLDOWN BETWEEN BATCHES
        # -----------------------------------------
        if end < total:
            print(f"⏳ Cooling down for {cooldown_sec} seconds...")
            time.sleep(cooldown_sec)

    print("\n✅ ALL TASKS COMPLETED.")
    return all_results

def process_tasks_with_batches_parallel_grey(
        tasks,
        item_refs,
        rag_image,
        vs,
        batch_size=150,
        cooldown_sec=15,
        max_workers=6):

    total = len(tasks)
    processed = 0
    all_results = []

    # -----------------------------------------------------
    # Helper: handle low-accuracy, ai-fillable items
    # -----------------------------------------------------
    def handle_low_accuracy_item(item, vs, question, k=5):
        """
        Handles: ai_fillable=true AND accuracy_level=false.
        Fills:
            value
            confidence=0
            text_support=[...]
            image_support=[]
        And returns True to SKIP LLM.
        """

        if not item.get("ai_fillable", False):
            return False

        if item.get("accuracy_level", True):  # must be False
            return False

        if item.get("task_type") != "remark":
            return False

        # Perform vector search
        try:
            scored_results = vs.similarity_search_with_score(question, k=k)
        except:
            scored_results = []

        # Build text_sources exactly like attach_supporting_refs
        text_sources = []
        for doc, score in scored_results:
            filename = doc.metadata.get("source_file", "unknown")
            page = doc.metadata.get("page")
            preview = doc.page_content[:500].strip()

            text_sources.append({
                "filename": filename,
                "page": page,
                "similarity_score": float(score),
                "text": preview
            })

        # Determine value based on score threshold
        has_info = any(score > 0.60 for doc, score in scored_results)

        if has_info:
            item["value"] = "TBD-Info available"
        else:
            item["value"] = "TBD-Info not available"

        # Mandatory metadata fields
        item["confidence"] = 0
        item["text_support"] = text_sources
        item["image_support"] = []

        return True  # handled, skip LLM

    # -----------------------------------------------------
    # Process batches
    # -----------------------------------------------------
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = tasks[start:end]
        ref_batch = item_refs[start:end]

        print(f"\n🔵 Starting batch: {start+1} → {end}")

        future_to_index = {}

        with ThreadPoolExecutor(max_workers=max_workers) as exe:

            for idx, task in enumerate(batch):
                future = exe.submit(run_single_task, task, rag_image)
                future_to_index[future] = idx

            for future in as_completed(future_to_index):

                idx = future_to_index[future]
                task = batch[idx]
                item = ref_batch[idx]

                question = task["question"]

                # ---------------------------------------------------------
                # 1) NEW: handle low-accuracy items WITHOUT LLM
                # ---------------------------------------------------------
                handled = handle_low_accuracy_item(
                    item=item,
                    vs=vs,
                    question=question,
                    k=5
                )

                if handled:
                    processed += 1
                    print(f"Processed {processed}/{total} tasks... (vector only)")
                    continue

                # ---------------------------------------------------------
                # 2) Normal LLM path for other items
                # ---------------------------------------------------------
                result = future.result()

                result["question"] = task["question"]
                result["task_type"] = task["task_type"]

                update_json_item(item, result)

                all_results.append(result)

                processed += 1
                print(f"Processed {processed}/{total} tasks...")

        # -----------------------------------------------------
        # Batch cooldown
        # -----------------------------------------------------
        if end < total:
            print(f"⏳ Cooling down for {cooldown_sec} seconds...")
            time.sleep(cooldown_sec)

    print("\n✅ ALL TASKS COMPLETED.")
    return all_results




def process_tasks_with_batches_parallel_stats(
        tasks,
        item_refs,
        rag_image,
        batch_size=150,
        cooldown_sec=15,
        max_workers=6):

    total = len(tasks)
    processed = 0
    all_results = []

    # ---------------------------
    # GLOBAL COUNTERS
    # ---------------------------
    stats = {
        "llm_calls": 0,
        "embedding_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = tasks[start:end]
        ref_batch = item_refs[start:end]

        print(f"\n🔵 Starting batch: {start+1} → {end}")

        future_to_index = {}

        with ThreadPoolExecutor(max_workers=max_workers) as exe:
            for idx, task in enumerate(batch):
                future = exe.submit(run_single_task_stats, task, rag_image)
                future_to_index[future] = idx

            for future in as_completed(future_to_index):

                idx = future_to_index[future]
                task = batch[idx]
                item = ref_batch[idx]

                result = future.result()

                # ---------------------------
                # TOKEN COUNTING
                # ---------------------------
                usage = result.get("_token_usage", {})

                stats["llm_calls"] += 1
                stats["prompt_tokens"] += usage.get("prompt", 0)
                stats["completion_tokens"] += usage.get("completion", 0)
                stats["total_tokens"] += usage.get("total", 0)

                # If rag_image uses embeddings internally:
                if result.get("used_embeddings", False):
                    stats["embedding_calls"] += 1

                # ---------------------------
                # NORMAL RESULT HANDLING
                # ---------------------------
                result["question"] = task["question"]
                result["task_type"] = task["task_type"]

                all_results.append(result)
                update_json_item(item, result)

                processed += 1
                print(f"Processed {processed}/{total} tasks...")

        if end < total:
            print(f"⏳ Cooling down for {cooldown_sec} seconds...")
            time.sleep(cooldown_sec)

    print("\n✅ ALL TASKS COMPLETED.")
    print("\n📊 TOKEN & CALL STATS ---------------------------------------")
    print(f"LLM calls       : {stats['llm_calls']}")
    print(f"Embedding calls : {stats['embedding_calls']}")
    print(f"Prompt tokens   : {stats['prompt_tokens']}")
    print(f"Completion tokens: {stats['completion_tokens']}")
    print(f"Total tokens     : {stats['total_tokens']}")
    print("--------------------------------------------------------------")

    return all_results, stats


def results_to_dataframe(results):
    """ Convert RAG results list into a structured pandas DataFrame. 
    Extracts question, task_type, response, confidence, source_detected,
    text_support,    and image_support. 
    
    Parameters:
        results (list): The list returned by your rag_image pipeline.
    Returns: pd.DataFrame: 
        Clean dataframe with parsed fields. """ 
    rows = [] 
    for result in results:
        # Extract "answer" which contains JSON string
        raw_answer = result.get("answer", "")
        
        # Try to parse JSON 
        parsed = {}
        try: 
            parsed = json.loads(raw_answer)
        except Exception: 
            parsed = {}
        
        # Construct one row
        row = { "question": result.get("question"),
               "task_type": result.get("task_type"),
               "response": parsed.get("response"),
               "confidence": parsed.get("confidence"),
               "source_detected": result.get("source_detected"), 
               "text_support": result.get("text_support"),
               "image_support": result.get("image_support"), 
        } 
        
        rows.append(row) 
        
    return pd.DataFrame(rows)


# Then apply rules:

# ✔ 1. If ANY dependency value == "" → result = ""

# (empty string means unresolved / not filled)

# ✔ 2. If ANY dependency value == "F" → result = "F"
# ✔ 3. If ALL dependency values ∈ {"N/A"} → result = "N/A"
# ✔ 4. If ALL dependency values ∈ {"P", "N/A"} → result = "P"
# ✔ Otherwise result = "" (fallback)

def update_verdict_dependencies(data):
    """
    Update all items with task_type = 'verdict_dependency'
    based on the values of items at dependency_rows.
    """

    print("\n🔍 Updating verdict_dependency items...\n")

    for table in data["Tables"]:
        items = table["Items"]

        # Build a lookup: answer_row → value at verdict column (col=3)
        verdict_map = {}
        for item in items:
            if item["answer_column"] == 3:  # verdict / verdict_dependency column
                verdict_map[item["answer_row"]] = item.get("value")

        # Now update verdict_dependency items
        for item in items:
            if item.get("task_type") != "verdict_dependency":
                continue

            dep_rows = item.get("dependency_rows")
            if not dep_rows:
                continue

            # Collect dependent values
            dep_vals = [
                verdict_map.get(row)
                for row in dep_rows
                if row in verdict_map
            ]

            # Normalize empty → ""
            dep_vals = [v if v is not None else "" for v in dep_vals]

            # Apply rules
            if any(v == "" for v in dep_vals):
                final_val = ""
            elif any(v == "F" for v in dep_vals):
                final_val = "F"
            elif all(v == "N/A" for v in dep_vals):
                final_val = "N/A"
            elif all(v in ("P", "N/A") for v in dep_vals):
                final_val = "P"
            else:
                final_val = ""

            old_val = item.get("value")
            item["value"] = final_val

            # Print only if updated or changed
            print(f"Updated: {item['field']} → {final_val} (was: {old_val})")

    print("\n✅ Verdict dependency update complete.\n")


def update_docx_tables_from_json(docx_path, json_path, output_path):
    """
    Update DOCX tables using JSON values.
    
    Update a cell if:
        - ai_fillable == True
          OR
        - task_type == "verdict_dependency"
    """

    doc = Document(docx_path)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for table_obj in data["Tables"]:
        table_index = table_obj["Table"]

        # Skip invalid table indices
        if table_index >= len(doc.tables):
            print(f"⚠️ Skipping missing table index: {table_index}")
            continue

        doc_table = doc.tables[table_index]

        for item in table_obj["Items"]:

            ai_fillable = item.get("ai_fillable", False)
            task_type = item.get("task_type")

            # ---------------------------------------------
            # UPDATE CONDITIONS
            # ---------------------------------------------
            if not ai_fillable and task_type != "verdict_dependency":
                continue   # skip all other items

            # Extract coordinates & value
            row = item.get("answer_row")
            col = item.get("answer_column")
            value = item.get("value")

            # Skip if value missing
            if value is None:
                continue

            # Try updating DOCX cell
            try:
                cell = doc_table.cell(row, col)
                cell.text = str(value)
            except Exception as e:
                print(f"⚠️ Error updating table {table_index} cell ({row},{col}): {e}")

    doc.save(output_path)
    print(f"✅ DOCX successfully updated → {output_path}")


