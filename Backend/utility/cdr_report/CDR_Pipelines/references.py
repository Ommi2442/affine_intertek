
import re
import json
from collections import Counter
from typing import List, Tuple, Set, Optional
import utility.cdr_report.CDR_Pipelines.switch as switch


from langchain_core.documents import Document
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from azure.cosmos import CosmosClient
from utility.cdr_report.CDR_Pipelines.configs import(
    cosmos_client,
    DB_NAME,
    CONT_NAME,
    score_llm,
    llm
)
from collections import defaultdict
from utility.cdr_report.CDR_Pipelines.prompts import ref_prompt as prompt
from utility.cdr_report.CDR_Pipelines.prompts import score_prompt

from langchain_community.callbacks import get_openai_callback
from utility.cdr_report.CDR_Pipelines.token_tracker import token_tracker
import json

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(
    r"(\+\d[\d\s\-\(\)]{6,}\d|\(\d{3}\)\s*\d{3}\-\d{4}|\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b)"
)

ADDR_HINT_RE = re.compile(
    r"(Street Address|Address|City, State|Postal|Zip|Country|Name and address of factory|Factory|Manufacturer|Bill-To|Applicant|Legal Entity Name|Prepared\s*For|Prepared\s*by)",
    re.I,
)
FORM_FILENAME_RE = re.compile(r"(cis|client[_\s-]?information|customer[_\s-]?information|agreement|agent)", re.I)
FORM_CONTENT_RE  = re.compile(r'("Applicant"|"Bill-To"|"Manufacturer"|Legal Entity Name|Street Address)', re.I)
QUOTE_FILENAME_RE = re.compile(
    r"(^|[/\\_\-\s])("
    r"qu"
    r"|quote"
    r"|quotation"
    r"|proforma"
    r"|pro[-\s]?invoice"
    r"|sales[_\s-]?quote"
    r")([_\-\s\d]|\.|$)",
    re.I,
)
QUOTE_CONTENT_RE = re.compile(r"(quotation|quote\s*(no|number)|prepared\s*for|buyer|customer|ship[-\s]?to|bill[-\s]?to)",re.I,)
ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]")  # zero-width chars
COMPONENT_SUPPLIER_RE = re.compile(
    r"(constituent|critical)\s+component|"
    r"component\s+manufacturer|"
    r"spare\s*part|parts?\s+manufacturer|"
    r"bill\s+of\s+materials|\bBOM\b|"
    r"approved\s+components?|"
    r"sub-?supplier|supplier\s+name|vendor|distributor|"
    r"part\s*(no\.|number)|item\s*no\.|mpn\b|sku\b",
    re.I,
)

OEM_SIGNAL_RE = re.compile(
    r"prepared\s*for|applicant|bill-?to|ship-?to|sold-?to|"
    r"factory\s+address|manufacturing\s+location|place\s+of\s+manufacture|"
    r"oem|original\s+equipment\s+manufacturer|final\s+assembly|assembled\s+in",
    re.I,
)

from collections import defaultdict

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from utility.cdr_report.CDR_Pipelines.utils import to_tabular_json
from pathlib import Path
from utility.cdr_report.CDR_Pipelines.utils import enrich_sheet1_extractions_by_headers
from utility.cdr_report.CDR_Pipelines.utils import sheet1_json_main
from utility.cdr_report.CDR_Pipelines.utils import enrich_sheet1_extractions_by_headers
from utility.cdr_report.CDR_Pipelines.utils import add_text_support_to_result_json
import utility.cdr_report.CDR_Pipelines.configs as configs
# OUTPUT_PATH   = Path(r".\utility\cdr_report\CDR_Pipelines\sheet1_3filled_dummy.json")
OUTPUT_PATH   = Path("sheet1_3filled_dummy.json")
from langchain_core.output_parsers import JsonOutputParser
from utility.cdr_report.CDR_Pipelines.utils import top_chunks_as_json


def limit_manufacturers_to_two(data_json: dict) -> dict:
    key = "ManufacturersSection"
    manufacturers = data_json.get(key)
    if isinstance(manufacturers, list) and len(manufacturers) > 2:
        data_json[key] = manufacturers[:2]
    return data_json

def get_bom_source_files(vs) -> set[str]:
    configs.require_runtime()
    BOM_SOURCE_FILES = switch.get_bom_filenames(vs=vs)
    ex_files = {x.lower() for x in BOM_SOURCE_FILES}
    return ex_files


def drop_excluded(docs, ex_files):
    kept = []
    for d in docs:
        sf = (d.metadata.get("source_file") or "").lower()
        if sf not in ex_files:
            kept.append(d)
    return kept

def drop_component_suppliers(docs: List[Document]) -> List[Document]:
    kept = []
    for d in docs:
        t = d.page_content or ""
        if COMPONENT_SUPPLIER_RE.search(t) and not OEM_SIGNAL_RE.search(t):
            continue
        kept.append(d)
    return kept




def clip_text(text: str, head: int = 2200, tail: int = 1200) -> str:
    if not text:
        return ""
    if len(text) <= head + tail:
        return text
    return text[:head] + "\n...\n" + text[-tail:]


def format_docs(docs: List[Document]) -> str:
    parts = []
    for d in docs:
        src = d.metadata.get("citation") or d.metadata.get("source_file") or d.metadata.get("source") or ""
        parts.append(f"Source: {src}\n{clip_text(d.page_content or '')}")
    return "\n\n".join(parts)

def extract_signals(text: str) -> Tuple[Set[str], Set[str], bool]:
    if not text:
        return set(), set(), False
    emails = set(EMAIL_RE.findall(text))
    phones = set(PHONE_RE.findall(text))
    has_addr_hint = bool(ADDR_HINT_RE.search(text))
    return emails, phones, has_addr_hint




def is_form_like(doc: Document) -> bool:
    sf = (doc.metadata.get("source_file") or "")
    txt = (doc.page_content or "")

    return bool(
        FORM_CONTENT_RE.search(txt)
        or FORM_FILENAME_RE.search(sf)
        or QUOTE_CONTENT_RE.search(txt)
        or QUOTE_FILENAME_RE.search(sf)
    )



def doc_usefulness_score(doc: Document) -> int:
    sf = (doc.metadata.get("source_file") or "").lower()
    txt = doc.page_content or ""
    emails, phones, has_addr_hint = extract_signals(txt)

    score = 0
    if has_addr_hint:
        score += 3
    score += min(len(emails), 3) * 2
    score += min(len(phones), 2) * 1

    # prefer structured / likely OEM docs
    if OEM_SIGNAL_RE.search(txt):
        score += 5

    # prefer quote/invoice-like sources
    if QUOTE_FILENAME_RE.search(sf) or QUOTE_CONTENT_RE.search(txt):
        score +=7

    # penalize component/BOM-like sections (unless it also has OEM signals)
    if COMPONENT_SUPPLIER_RE.search(txt) and not OEM_SIGNAL_RE.search(txt):
        score -= 8

    if sf.endswith(".pdf"):
        score += 2
    if sf.endswith(".xlsx") or sf.endswith(".xls"):
        score += 1

    return score

def fetch_all_chunks_for_source(container, source_file: str):
    query = """
    SELECT c.id, c.metadata, c.text
    FROM c
    WHERE c.metadata.source_file = @src
    """
    params = [{"name": "@src", "value": source_file}]
    return list(container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))


def expand_form_sources(container, docs: List[Document], max_sources: int = 3) -> List[Document]:
    sources = []
    seen = set()
    for d in docs:
        sf = d.metadata.get("source_file") or ""
        if sf and is_form_like(d) and sf not in seen:
            sources.append(sf)
            seen.add(sf)

    sources = sources[:max_sources]
    if not sources:
        return docs

    # remove original chunks for expanded sources
    base = [d for d in docs if (d.metadata.get("source_file") or "") not in set(sources)]

    expanded = list(base)
    for sf in sources:
        rows = fetch_all_chunks_for_source(container, sf)
        expanded.extend([
            Document(
                page_content=r.get("text", "") or "",
                metadata={**(r.get("metadata") or {}), "chunk_id": r.get("id")}
            )
            for r in rows
        ])

    return expanded

def _norm_sig(text: str) -> str:
    if not text:
        return ""
    text = ZERO_WIDTH_RE.sub("", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1200]  # stable signature window

def dedupe_docs(docs: List[Document]) -> List[Document]:
    seen = set()
    out = []
    for d in docs:
        chunk_id = d.metadata.get("chunk_id")
        sf = d.metadata.get("source_file")
        page = d.metadata.get("page") or d.metadata.get("page_label")
        sig = _norm_sig(d.page_content or "")

        if chunk_id:
            key = ("id", chunk_id)
        else:
            key = (sf, page, sig)

        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out




def cap_per_source(docs: List[Document], max_per_source: int = 4) -> List[Document]:
    buckets = defaultdict(list)
    for d in docs:
        sf = d.metadata.get("source_file") or "UNKNOWN"
        buckets[sf].append(d)

    out = []
    for sf, ds in buckets.items():
        ds.sort(key=doc_usefulness_score, reverse=True)
        out.extend(ds[:max_per_source])
    return out



def build_fallback_query(user_question: str) -> str:
    # You can tune this. Goal: pull anything that contains relevant structured identifiers.
    return (
        user_question
        + " Applicant Bill-To Manufacturer Factory Legal Entity Name Street Address Contacts Email Phone Fax "
        + " Name and address of factory " 
        + " Prepared For: "
    )

def add_general_fallback(
    docs: List[Document],
    candidates: List[Document],
    max_extra_docs: int = 8,
    require_any_email: bool = True,
) -> List[Document]:
    covered_emails, covered_phones = set(), set()
    covered_addr = False

    for d in docs:
        e, p, a = extract_signals(d.page_content or "")
        covered_emails |= e
        covered_phones |= p
        covered_addr = covered_addr or a

    remaining = [c for c in candidates if c not in docs]
    remaining.sort(key=doc_usefulness_score, reverse=True)

    chosen = []
    for c in remaining:
        if len(chosen) >= max_extra_docs:
            break
        e, p, a = extract_signals(c.page_content or "")
        adds_new = bool((e - covered_emails) or (p - covered_phones) or (a and not covered_addr))
        if not adds_new:
            continue

        chosen.append(c)
        covered_emails |= e
        covered_phones |= p
        covered_addr = covered_addr or a

    # Ensure at least one email-bearing doc if none exists yet
    if require_any_email and len(covered_emails) == 0:
        for c in remaining:
            if len(chosen) >= max_extra_docs:
                break
            e, _, _ = extract_signals(c.page_content or "")
            if e:
                chosen.append(c)
                covered_emails |= e

    return docs + chosen

def build_context_docs(vs, container, retrieved_docs: List[Document], user_question: str, ex_files, max_final: int = 25) -> List[Document]:
    original = list(retrieved_docs)

    # Expand CIS/Agreement-like sources (and ideally remove originals for those expanded sources)
    expanded = expand_form_sources(container, original, max_sources=3)
    expanded = dedupe_docs(expanded)

    # Second retrieval pass: real fallback to other files not in initial top-k
    fallback_query = build_fallback_query(user_question)
    fallback_candidates = vs.similarity_search(
        fallback_query,
        k=80,
        search_type="vector"
    )
    fallback_candidates = drop_excluded(fallback_candidates, ex_files)
    fallback_candidates = drop_component_suppliers(fallback_candidates) # changes

    # Merge candidates broadly (include expanded so novelty selection sees everything)
    merged_candidates = dedupe_docs(expanded + fallback_candidates)

    final_docs = add_general_fallback(
        docs=expanded,
        candidates=merged_candidates,
        max_extra_docs=10,
        require_any_email=True
    )

    final_docs = dedupe_docs(final_docs) #
    final_docs.sort(key=doc_usefulness_score, reverse=True) #
    final_docs = cap_per_source(final_docs, max_per_source=4)#
    final_docs = dedupe_docs(final_docs)#
    # final_docs = exclude_bom_docs(final_docs)
    
    return final_docs[:max_final]



def references_main(vs, ref):

    configs.require_runtime()

    cosmos_container = configs.get_cosmos_container_client()

    ex_files = get_bom_source_files(vs)

    retriever = vs.as_retriever(
        search_type="vector",
        k=20,
        search_kwargs={}
    )

    rag_chain_debug = (
        RunnableParallel(
            docs=retriever
            | RunnableLambda(
                lambda docs: drop_component_suppliers(
                    drop_excluded(docs, ex_files)
                )
            ),
            question=RunnablePassthrough(),
        )
        | RunnableLambda(lambda x: {
            "raw_docs": x["docs"],
            "docs": build_context_docs(
                vs,
                cosmos_container,
                x["docs"],
                x["question"],
                ex_files
            ),
            "question": x["question"],
        })
        | RunnableLambda(lambda x: {
            "docs": x["docs"],
            "context": format_docs(x["docs"]),
            "question": x["question"],
        })
        | RunnableLambda(lambda x: {
            "docs": x["docs"],
            "answer": run_llm_with_tracking(
                (prompt | llm | JsonOutputParser()),
                {
                    "context": x["context"],
                    "question": x["question"]
                }
            )
        })
    )

    CURRENT_QUESTION = (
        "Extract the Applicant and ALL Manufacturer/Factory details "
        "(including all manufacturer contacts and emails). "
        "Look for sections like Applicant, Bill-To, Manufacturer, "
        "Legal Entity Name, Street Address."
    )

    out = rag_chain_debug.invoke(CURRENT_QUESTION)

    context = format_docs(out["docs"])
    extracted = out["answer"]

    # ========================================
    # SCORE LLM TRACKING
    # ========================================

    scores = run_llm_with_tracking(
        (score_prompt | score_llm | JsonOutputParser()),
        {
            "context": context,
            "extracted_json": json.dumps(
                extracted,
                ensure_ascii=False
            )
        }
    )

    if hasattr(scores, "dict"):
        scores_obj = scores.dict()
    else:
        scores_obj = scores

    with open(
        "confidence.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            scores_obj,
            f,
            indent=4,
            ensure_ascii=False,
            default=str
        )

    result = to_tabular_json(out['answer'])

    data_json = ref | result

    data_json['ApplicantSection']['Applicant'] = ref['Applicant']
    data_json['ApplicantSection']['Address'] = ref['Address']

    template = json.loads(
        configs.TEMPLATE_PATH.read_text(encoding="utf-8")
    )

    data_json = limit_manufacturers_to_two(data_json)

    template = sheet1_json_main(data_json, template)

    template = enrich_sheet1_extractions_by_headers(
        template,
        scores
    )

    template = add_text_support_to_result_json(
        template,
        out['docs'],
        top_k=5
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            template,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    return template


# ========================================
# SHARED TRACKING HELPER
# ========================================

def run_llm_with_tracking(chain, payload):

    with get_openai_callback() as cb:
        result = chain.invoke(payload)

    token_tracker.update(
        prompt_tokens=cb.prompt_tokens,
        completion_tokens=cb.completion_tokens,
        total_tokens=cb.total_tokens,
    )

    return result