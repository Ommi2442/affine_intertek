from utility.cdr_report.CDR_Pipelines.prompts import *
from langchain_openai import AzureChatOpenAI
# Instead of: from langchain.schema import Document
from langchain_core.documents import Document
from pathlib import Path
# Instead of: from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import utility.cdr_report.CDR_Pipelines.configs as configs
OUTPUT_PATH   = Path("features.json")
import json
import textwrap
# import matplotlib.pyplot as plt
# from PIL import Image
import requests
from io import BytesIO
from utility.cdr_report.CDR_Pipelines.json_utils import fill_sheet6_from_final_sections
from utility.cdr_report.CDR_Pipelines.configs import (AOAI_ENDPOINT, API_VERSION, AOAI_KEY)
#from utility.cdr_report.CDR_Pipelines.configs import llm
from utility.cdr_report.CDR_Pipelines.utils import _get_status_code_from_exception, is_rate_limit_error, invoke_with_rate_limit_retry
# Cell 1: Imports & LLM setup

from langchain_openai import AzureChatOpenAI
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

import json
import textwrap
# import matplotlib.pyplot as plt
# from PIL import Image
import requests
from io import BytesIO
from typing import List, Dict, Any


# Cell 2: Multimodal RAG retrieval (text from VS + image URLs as-is)
from urllib.parse import urlparse, unquote
import os

def build_image_candidates(image_urls):
    out = []
    for i, u in enumerate(image_urls or [], start=1):
        path = unquote(urlparse(u).path)  # remove %20 etc
        name = os.path.basename(path) or f"image_{i}"
        out.append({"id": f"img_{i:02d}", "name": name, "url": u})
    return out

def rag_multimodal_retrieve(
    section_name: str,
    custom_queries: List[str],
    vs,
    image_urls: List[str],
    k: int = 12,
) -> Dict[str, Any]:
    """
    Multimodal-first RAG:
    - Retrieves text evidence from vector store
    - ALWAYS carries all provided images
    - Deduplicates by (source_file, page)
    """
    image_candidates = build_image_candidates(image_urls)
    queries = [section_name]
    if custom_queries:
        queries.extend(custom_queries)

    retrieved = []
    retrieval_errors = []
    for q in queries:
        try:
            retrieved.extend(vs.similarity_search_with_score(q, k=k))
        except Exception as e:
            #print(f"[WARN] similarity_search failed for query '{q}': {e}")
            retrieval_errors.append(f"{q}: {repr(e)}")
    if retrieval_errors:
        # Option 1 (best for correctness): fail fast so you notice it immediately
        raise RuntimeError("RAG retrieval failed: " + " | ".join(retrieval_errors))

    # Deduplicate by (filename, page)
    seen = set()
    text_chunks: List[Document] = []
    for doc, score in retrieved:
        key = (doc.metadata.get("source_file"), doc.metadata.get("page"))
        if key not in seen:
            seen.add(key)
            doc.metadata["score"] = score
            text_chunks.append(doc)

    context_text = "\n\n".join([d.page_content for d in text_chunks])

    evidence = {
        "context_text": context_text,
        "text_chunks": [
            {
                "filename": d.metadata.get("source_file"),
                "page": d.metadata.get("page"),
                "preview_text": d.page_content,
                "similarity_score": d.metadata.get("score"),
            }
            for d in text_chunks
        ],
        "image_urls": [c["url"] for c in image_candidates],
        "image_candidates": [{"id": c["id"], "name": c["name"]} for c in image_candidates],
        "image_candidates_full": image_candidates, 
    }

    return evidence



# Cell 4: Prompt template + multimodal message construction

BASE_SYSTEM_PROMPT = """
You are an expert test engineer writing the '{section_name}' section of an IEC CDR.

Use the provided text evidence and all images to extract factual, non-hallucinated information.

GENERAL RULES:
- Use BOTH text and images as evidence where available.
- If a specific numerical value is NOT visible in text/images, use "unknown" instead of inventing.
- Do NOT output placeholders like "___".
- Return ONLY a single valid JSON object (no commentary, no markdown).

OUTPUT SCHEMA (must match exactly in keys and nesting):
{json_schema}
""".strip()


def build_multimodal_messages(
    section_name: str,
    instruction_text: str,
    template_text: str,
    evidence: Dict[str, Any],
    json_schema: str,
):
    """
    Construct GPT-4o multimodal messages (System + Human with text + images).
    Prompt is fully parameterized by:
      - section_name
      - instruction_text
      - template_text
      - json_schema
    """

    system_msg = SystemMessage(
        content=BASE_SYSTEM_PROMPT.format(
            section_name=section_name,
            json_schema=json_schema,
        )
    )

    # This text goes in the HumanMessage (along with images)
    text_block = f"""
SECTION NAME:
{section_name}

SECTION-SPECIFIC INSTRUCTIONS:
{instruction_text}

NARRATIVE TEMPLATE (for the final 'filled_text' sentence):
{template_text}

TEXT EVIDENCE (from RAG):
{evidence['context_text']}
""".strip()
    
    # ✅ STEP 3: Append image candidates list (IDs + names) so model can return only IDs
    candidates = evidence.get("image_candidates", [])
    if candidates:
        candidates_lines = "\n".join(
            f"{c['id']} | {c.get('name','')}".strip()
            for c in candidates
            if isinstance(c, dict) and c.get("id")
        )
        text_block += (
            "\n\nIMAGE CANDIDATES (choose from these IDs ONLY; do NOT invent):\n"
            f"{candidates_lines}\n\n"
            "Return ONLY IDs that appear in the list above.\n"
            "When selecting images, return ONLY the relevant IDs in the output field "
            "'relevant_image_ids'. If none are relevant, return []."
        )
    # Start with text
    content: List[Dict[str, Any]] = [{"type": "text", "text": text_block}]

    # ALWAYS include all images as separate "image_url" parts
    for url in evidence.get("image_urls", []):
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": url},
            }
        )

    human_msg = HumanMessage(content=content)

    return [system_msg, human_msg]

def llm_generate_multimodal(messages, llm: AzureChatOpenAI) -> Dict[str, Any]:
    response = invoke_with_rate_limit_retry(
        llm,
        messages,
        retries=6,
        wait_seconds=5.0,
        jitter=0.5
    )

    content = response.content
    if isinstance(content, list):
        text_parts = [c.get("text", "") for c in content if isinstance(c, dict)]
        content = "".join(text_parts)

    try:
        data = json.loads(content)
    except Exception as e:
        print("[WARN] JSON parse failed, returning raw content. Error:", e)
        data = {"raw_content": content}

    return data



# Cell 6: Run one multimodal section end-to-end

def run_multimodal_section(
    name: str,
    instruction: str,
    template: str,
    custom_queries: List[str],
    vs,
    image_urls: List[str],
    llm: AzureChatOpenAI,
    json_schema: str,
):
    # Step 1 — retrieve evidence (text RAG + images)
    evidence = rag_multimodal_retrieve(
        section_name=name,
        custom_queries=custom_queries,
        vs=vs,
        image_urls=image_urls,
        k=12,
    )

    # Step 2 — build GPT-4o multimodal messages
    messages = build_multimodal_messages(
        section_name=name,
        instruction_text=instruction,
        template_text=template,
        evidence=evidence,
        json_schema=json_schema,
    )
    #print(messages)
    # Step 3 — LLM generation (JSON)
    section_json = llm_generate_multimodal(messages, llm)

    # We return both:
    # - evidence (for debug/trace)
    # - section_json (parsed JSON)
    return {
        "evidence": evidence,
        "section_json": section_json,
    }


from concurrent.futures import ThreadPoolExecutor, as_completed

def run_one_section(cfg, vs, image_urls, llm):
    # Return ONLY the result dict
    return run_multimodal_section(
        name=cfg["name"],
        instruction=cfg["instruction"],
        template=cfg["template"],
        custom_queries=cfg.get("custom_queries", []),
        vs=vs,
        image_urls=image_urls,
        llm=llm,
        json_schema=cfg["json_schema"],
    )

def run_sections_parallel(section_cfgs, vs, image_urls, llm, max_workers=6):
    results = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(run_one_section, cfg, vs, image_urls, llm): cfg["key"]
                   for cfg in section_cfgs}

        for fut in as_completed(futures):
            key = futures[fut]
            try:
                results[key] = fut.result()   # <-- now this is the dict with evidence/section_json
            except Exception as e:
                errors[key] = str(e)

    return results, errors


section_cfgs = [
    {
        "key": "spacing",
        "name": "Spacing",
        "instruction": spacing_instruction,
        "template": spacing_template,
        "custom_queries": ["creepage", "clearance", "primary circuits spacing"],
        "json_schema": spacing_json_schema,
    },
    {
        "key": "mechanical",
        "name": "Mechanical Assembly",
        "instruction": mechanical_instruction,
        "template": mechanical_template,
        "custom_queries": [
            "mechanical assembly", "mounting", "lockwashers", "starwashers",
            "switch mounting", "connector mounting"
        ],
        "json_schema": mechanical_json_schema,
    },
    {
        "key": "corrosion",
        "name": "Corrosion Protection",
        "instruction": corrosion_instruction,
        "template": corrosion_template,
        "custom_queries": [
            "corrosion", "corrosion protection", "painted metal parts",
            "plated metal parts", "coating on ferrous parts", "surface finish"
        ],
        "json_schema": corrosion_json_schema,
    },
    {
        "key": "access",
        "name": "Accessibility of Live Parts",
        "instruction": access_instruction,
        "template": access_template,
        "custom_queries": [
            "accessibility of live parts", "accessible live parts",
            "primary live parts enclosure", "openings in enclosure",
            "live parts accessibility test"
        ],
        "json_schema": access_json_schema,
    },
    {
        "key": "grounding",
        "name": "Grounding",
        "instruction": grounding_instruction,
        "template": grounding_template,
        "custom_queries": [
            "grounding", "protective earth", "equipment grounding terminal",
            "ground symbol", "PE terminal", "double insulated", "class II construction"
        ],
        "json_schema": grounding_json_schema,
    },
    {
        "key": "polarized",
        "name": "Polarized Connection",
        "instruction": polarized_instruction,
        "template": polarized_template,
        "custom_queries": [
            "polarized power connection", "polarized plug", "unequal blades",
            "keyed connector", "ungrounded conductor", "single pole switches and fuses"
        ],
        "json_schema": polarized_json_schema,
    },
    {
        "key": "internal_wiring",
        "name": "Internal Wiring",
        "instruction": internal_wiring_instruction,
        "template": internal_wiring_template,
        "custom_queries": [
            "internal wiring routing", "wiring away from sharp or moving parts",
            "bushings", "grommets", "wire AWG", "wire voltage rating",
            "wire temperature rating", "internal harness"
        ],
        "json_schema": internal_wiring_json_schema,
    },
    {
        "key": "markings",
        "name": "Markings",
        "instruction": markings_instruction,
        "template": markings_template,
        "custom_queries": [
            "rating label", "markings on enclosure", "nameplate", "model number",
            "electrical ratings", "manufacturer label", "French markings"
        ],
        "json_schema": markings_json_schema,
    },
    {
        "key": "instructions",
        "name": "Installation, Operating and Safety Instructions",
        "instruction": instructions_instruction,
        "template": instructions_template,
        "custom_queries": [
            "user manual", "installation instructions", "operating instructions",
            "safety instructions", "IFU", "printed leaflet", "online manual"
        ],
        "json_schema": instructions_json_schema,
    },
]

from typing import List, Dict, Any

def pick_image_support(section_json: dict, evidence: dict) -> List[str]:
    # Build id -> url map from evidence (best source of truth)
    id2url = {}
    for c in (evidence.get("image_candidates_full") or []):
        if isinstance(c, dict) and isinstance(c.get("id"), str) and isinstance(c.get("url"), str):
            id2url[c["id"]] = c["url"]

    out: List[str] = []
    seen = set()

    # 1) Preferred: relevant_image_ids (Option A)
    ids = section_json.get("relevant_image_ids")
    if isinstance(ids, list):
        for img_id in ids:
            if isinstance(img_id, str):
                url = id2url.get(img_id)
                if url and url not in seen:
                    out.append(url)
                    seen.add(url)
        return out

    # 2) Fallback: image_evidence
    ev = section_json.get("image_evidence")
    if isinstance(ev, list):
        for item in ev:
            if not isinstance(item, dict):
                continue

            # Prefer image_id if present (also maps to URL)
            img_id = item.get("image_id")
            if isinstance(img_id, str):
                url = id2url.get(img_id)
                if url and url not in seen:
                    out.append(url)
                    seen.add(url)
                continue

            # Otherwise accept blob_url if present
            blob_url = item.get("blob_url")
            if isinstance(blob_url, str) and blob_url.strip():
                if blob_url not in seen:
                    out.append(blob_url)
                    seen.add(blob_url)

        return out

    return []


import re

def build_all_sections_final_json(
    section_cfgs,
    vs,
    image_urls,
    llm,
    max_workers=6,
):
    """
    Runs all sections in parallel + applies your per-section post-processing.
    Returns:
      {
        "final": { "spacing": {...}, "mechanical": {...}, ... },
        "raw": parallel_results,
        "errors": parallel_errors
      }
    """

    def na_prefix(text, prefix):
        return f"{prefix} - N/A" if (text or "").strip().upper() == "N/A" else text

    parallel_results, parallel_errors = run_sections_parallel(
        section_cfgs=section_cfgs,
        vs=vs,
        image_urls=image_urls,
        llm=llm,
        max_workers=max_workers
    )

    final = {}

    # -------------------------
    # SPACING
    # -------------------------
    if "spacing" in parallel_results:
        spacing_evidence = parallel_results["spacing"]["evidence"]
        spacing_section_json = parallel_results["spacing"]["section_json"]

        spacing_filled_text = (spacing_section_json.get("filled_text") or "").replace("unknown", "___")

        spacing_filled_text = re.sub(
            r'(\bIllustration\b)\s+[^\s.]+(\s+for\s+areas\s+to\s+verify\b)',
            r'\1 __\2',
            spacing_filled_text,
            flags=re.IGNORECASE
        )

        # spacing_filled_text = re.sub(
        #     r'\bForm\b\s+[^\s]+\s+for\s+areas\s+to\s+verify\b',
        #     'Form __ for areas to verify',
        #     spacing_filled_text,
        #     flags=re.IGNORECASE
        # )

        # spacing_filled_text = re.sub(
        #     r'(\bIllustration\s*)\d+\b',
        #     r'\1__',
        #     spacing_filled_text,
        #     flags=re.IGNORECASE
        # )

        final["spacing"] = {
            "filled_text": spacing_filled_text,
            "text_support": spacing_evidence["text_chunks"][0:5],
            "image_support": pick_image_support(spacing_section_json, spacing_evidence),
            "confidence": spacing_section_json.get("overall_confidence"),
        }

    # -------------------------
    # MECHANICAL
    # -------------------------
    if "mechanical" in parallel_results:
        mechanical_evidence = parallel_results["mechanical"]["evidence"]
        mechanical_section_json = parallel_results["mechanical"]["section_json"]

        mechanical_filled_text = na_prefix(mechanical_section_json.get("filled_text"), "Mechanical Assembly")

        final["mechanical"] = {
            "filled_text": mechanical_filled_text,
            "text_support": mechanical_evidence["text_chunks"][0:5],
            "image_support": pick_image_support(mechanical_section_json, mechanical_evidence),
            "confidence": mechanical_section_json.get("overall_confidence"),
        }

    # -------------------------
    # CORROSION
    # -------------------------
    if "corrosion" in parallel_results:
        corrosion_evidence = parallel_results["corrosion"]["evidence"]
        corrosion_section_json = parallel_results["corrosion"]["section_json"]

        corrosion_filled_text = na_prefix(corrosion_section_json.get("filled_text"), "Corrosion Protection")

        final["corrosion"] = {
            "filled_text": corrosion_filled_text,
            "text_support": corrosion_evidence["text_chunks"][0:5],
            "image_support": pick_image_support(corrosion_section_json, corrosion_evidence),
            "confidence": corrosion_section_json.get("overall_confidence"),
        }

    # -------------------------
    # ACCESSIBILITY OF LIVE PARTS
    # -------------------------
    if "access" in parallel_results:
        access_evidence = parallel_results["access"]["evidence"]
        access_section_json = parallel_results["access"]["section_json"]

        access_filled_text = na_prefix(access_section_json.get("filled_text"), "Accessibility of Live Parts")

        final["access"] = {
            "filled_text": access_filled_text,
            "text_support": access_evidence["text_chunks"][0:5],
            "image_support": pick_image_support(access_section_json, access_evidence),
            "confidence": access_section_json.get("overall_confidence"),
        }

    # -------------------------
    # GROUNDING
    # -------------------------
    if "grounding" in parallel_results:
        grounding_evidence = parallel_results["grounding"]["evidence"]
        grounding_section_json = parallel_results["grounding"]["section_json"]

        grounding_filled_text = na_prefix(grounding_section_json.get("filled_text"), "Grounding")

        final["grounding"] = {
            "filled_text": grounding_filled_text,
            "text_support": grounding_evidence["text_chunks"][0:5],
            "image_support": pick_image_support(grounding_section_json, grounding_evidence),
            "confidence": grounding_section_json.get("overall_confidence"),
        }

    # -------------------------
    # POLARIZED CONNECTION
    # -------------------------
    if "polarized" in parallel_results:
        polarized_evidence = parallel_results["polarized"]["evidence"]
        polarized_section_json = parallel_results["polarized"]["section_json"]

        polarized_filled_text = na_prefix(polarized_section_json.get("filled_text"), "Polarized Connection")

        final["polarized"] = {
            "filled_text": polarized_filled_text,
            "text_support": polarized_evidence["text_chunks"][0:5],
            "image_support": pick_image_support(polarized_section_json, polarized_evidence),
            "confidence": polarized_section_json.get("overall_confidence"),
        }

    # -------------------------
    # INTERNAL WIRING
    # -------------------------
    if "internal_wiring" in parallel_results:
        internal_wiring_evidence = parallel_results["internal_wiring"]["evidence"]
        internal_wiring_section_json = parallel_results["internal_wiring"]["section_json"]

        internal_wiring_filled_text = internal_wiring_section_json.get("filled_text") or ""

        final["internal_wiring"] = {
            "filled_text": internal_wiring_filled_text,
            "text_support": internal_wiring_evidence["text_chunks"][0:5],
            "image_support": pick_image_support(internal_wiring_section_json, internal_wiring_evidence),
            "confidence": internal_wiring_section_json.get("overall_confidence"),
        }

    # -------------------------
    # MARKINGS
    # -------------------------
    if "markings" in parallel_results:
        markings_evidence = parallel_results["markings"]["evidence"]
        markings_section_json = parallel_results["markings"]["section_json"]

        # Better than replace("unknown","__"): enforce your policy
        status = (markings_section_json.get("markings_status") or "").lower()
        if status == "unknown":
            markings_filled_text = "Null"
        else:
            markings_filled_text = markings_section_json.get("filled_text") or ""

        final["markings"] = {
            "filled_text": markings_filled_text,
            "text_support": markings_evidence["text_chunks"][0:5],
            "image_support": pick_image_support(markings_section_json, markings_evidence),
            "confidence": markings_section_json.get("overall_confidence"),
        }

    # -------------------------
    # INSTRUCTIONS
    # -------------------------
    if "instructions" in parallel_results:
        instructions_evidence = parallel_results["instructions"]["evidence"]
        instructions_section_json = parallel_results["instructions"]["section_json"]

        instructions_filled_text = na_prefix(
            instructions_section_json.get("filled_text"),
            "Installation, Operating and Safety Instructions"
        )

        final["instructions"] = {
            "filled_text": instructions_filled_text,
            "text_support": instructions_evidence["text_chunks"][0:5],
            "image_support": pick_image_support(instructions_section_json, instructions_evidence),
            "confidence": instructions_section_json.get("overall_confidence"),
        }

    return {
        "final": final,
        "raw": parallel_results,
        "errors": parallel_errors,
    }

def features_main(vs, image_urls, llm=None):
    import utility.cdr_report.CDR_Pipelines.configs as configs
    configs.require_runtime()

    llm = llm or configs.llm
    all_out = build_all_sections_final_json(
        section_cfgs=section_cfgs,
        vs=vs,
        image_urls=image_urls,
        llm=llm,
        max_workers=6
    )
    with open(configs.TEMPLATE_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)
    final_sections = all_out["final"]
    errors = all_out["errors"]
    with open("errors_sheet6.txt", "w", encoding="utf-8") as f:
        f.write("=== ERRORS (sheet 6 pipeline) ===\n\n")
        f.write(json.dumps(errors, indent=2, ensure_ascii=False))
        f.write("\n")
    with open("final_sections.json", "w", encoding="utf-8") as f:
        json.dump(final_sections, f, indent=2, ensure_ascii=False)
    features=fill_sheet6_from_final_sections(payload, final_sections)
    OUTPUT_PATH   = Path("sheet1_6filled_dummy.json")
    OUTPUT_PATH.write_text(json.dumps(features, indent=2, ensure_ascii=False), encoding="utf-8")
    return features
