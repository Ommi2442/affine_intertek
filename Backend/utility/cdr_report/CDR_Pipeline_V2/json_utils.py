import json
import re
from copy import deepcopy
from pathlib import Path

def shift_cell(cell, row_offset=0, col_offset=0):
    """
    "A6" -> shift rows/cols.
    """
    if not cell:
        return cell

    m = re.match(r"^([A-Z]+)(\d+)$", cell)
    if not m:
        return cell

    col_letters, row = m.group(1), int(m.group(2))

    # convert letters -> number
    col_num = 0
    for ch in col_letters:
        col_num = col_num * 26 + (ord(ch) - ord("A") + 1)

    col_num += col_offset
    row += row_offset

    # number -> letters
    out = ""
    while col_num > 0:
        col_num, rem = divmod(col_num - 1, 26)
        out = chr(rem + ord("A")) + out

    return f"{out}{row}"

def fill_block(items, prefix, data_map):
    for it in items:
        if it.get("prefix") == prefix and it.get("task_type") == "extraction":
            field = it.get("field")

            # normalize label for lookup
            lookup_field = field
            if isinstance(field, str) and re.match(r"^Manufacturer\s+\d+$", field):
                lookup_field = "Manufacturer"

            if lookup_field in data_map:
                it["value"] = data_map[lookup_field]

def sheet1_json_main(data_json, template):
# --- locate Sheet 1 ---
    sheet1 = next(s for s in template["Sheets"] if s["sheet_no"] == 1)
    items = sheet1["Items"]

    # --- 1) Fill "Report" section fields present in template ---
    # (Template has field "Report Number" and "Standard(s)" in Sheet 1) :contentReference[oaicite:5]{index=5}
    report_map = {
        "Report Number": data_json.get("Report Number"),
        "Standard(s)": data_json.get("Standard"),
    }
    fill_block(items, "Report", report_map)

    # --- 2) Fill Applicant block ---
    fill_block(items, "Applicant", data_json.get("ApplicantSection", {}))

    # --- 3) Fill Manufacturer 1 block (already exists in template) ---
    mfgs = data_json.get("ManufacturersSection", [])
    if mfgs:
        fill_block(items, "Manufacturer 1", mfgs[0])

    # --- 4) Identify base blocks to clone ---
    base_left_block  = [deepcopy(it) for it in items if it.get("prefix") == "Applicant" and it.get("task_type") == "extraction"]
    base_right_block = [deepcopy(it) for it in items if it.get("prefix") == "Manufacturer 1" and it.get("task_type") == "extraction"]
    blank_row_item   = next(deepcopy(it) for it in items if it.get("task_type") == "blank" and it.get("question_cell") == "A13")

    # Applicant starts at row 6 and blank at row 13 -> each pair consumes 8 rows (7 + blank) :contentReference[oaicite:6]{index=6}
    PAIR_SPAN = 8  # rows to shift per new pair block

    # --- 5) Build pairs after the first one ---
    # pair1 already: Applicant + Manufacturer1
    remaining = mfgs[1:]  # Manufacturer 2..N
    pairs = []
    i = 0
    while i < len(remaining):
        left = remaining[i]
        right = remaining[i+1] if (i+1) < len(remaining) else None
        pairs.append((left, right))
        i += 2

    new_items = []
    new_items.extend(items)  # keep original sheet1 items as-is

    # --- 6) Append cloned blocks for each pair with blank row after each pair ---
    for pair_index, (m_left, m_right) in enumerate(pairs, start=1):
        row_offset = pair_index * PAIR_SPAN  # pair2 starts 8 rows below, etc.

        # manufacturer numbering in data list: original mfgs[0] was Manufacturer 1
        left_num = 1 + (pair_index * 2 - 1)   # 2,4,6,...
        right_num = left_num + 1              # 3,5,7,...

        # ---- left side (A/B/C): reuse Applicant layout but rename first field to "Manufacturer"
        left_block = deepcopy(base_left_block)
        for it in left_block:
            it["prefix"] = f"Manufacturer {left_num}"

            # change the first row label from "Applicant" -> "Manufacturer"
            if it.get("field") == "Applicant":
                it["field"] = f"Manufacturer {left_num}"

            # shift all cell addresses down
            it["question_cell"] = shift_cell(it.get("question_cell"), row_offset=row_offset)
            it["answer_cell"]   = shift_cell(it.get("answer_cell"), row_offset=row_offset)
            it["vm_range"]      = shift_cell(it.get("vm_range"), row_offset=row_offset)
            it["fm_range"]      = shift_cell(it.get("fm_range"), row_offset=row_offset)

        # fill values
        left_data = {
            "Manufacturer": m_left.get("Manufacturer", "N/A"),
            "Address":      m_left.get("Address", "N/A"),
            "Country":      m_left.get("Country", "N/A"),
            "Contact":      m_left.get("Contact", "N/A"),
            "Phone":        m_left.get("Phone", "N/A"),
            "FAX":          m_left.get("FAX", "N/A"),
            "Email":        m_left.get("Email", "N/A"),
        }
        fill_block(left_block, f"Manufacturer {left_num}", left_data)

        # ---- right side (D/E/F): reuse Manufacturer 1 layout
        right_block = []
        if m_right:
            right_block = deepcopy(base_right_block)
            for it in right_block:
                it["prefix"] = f"Manufacturer {right_num}"
                
                if isinstance(it.get("field"), str) and it["field"].startswith("Manufacturer"):
                    it["field"] = f"Manufacturer {right_num}"

                it["question_cell"] = shift_cell(it.get("question_cell"), row_offset=row_offset)
                it["answer_cell"]   = shift_cell(it.get("answer_cell"), row_offset=row_offset)

                # IMPORTANT: keep the same relative pattern as your template.
                # Your template's Manufacturer 1 vm_range uses column F with a -2 row pattern (ex: D6 -> F4) :contentReference[oaicite:7]{index=7}
                it["vm_range"]      = shift_cell(it.get("vm_range"), row_offset=row_offset)
                it["fm_range"]      = shift_cell(it.get("fm_range"), row_offset=row_offset)

            right_data = {
                "Manufacturer": m_right.get("Manufacturer", "N/A"),
                "Address":      m_right.get("Address", "N/A"),
                "Country":      m_right.get("Country", "N/A"),
                "Contact":      m_right.get("Contact", "N/A"),
                "Phone":        m_right.get("Phone", "N/A"),
                "FAX":          m_right.get("FAX", "N/A"),
                "Email":        m_right.get("Email", "N/A"),
            }
            fill_block(right_block, f"Manufacturer {right_num}", right_data)

        # ---- blank row after each pair
        blank_copy = deepcopy(blank_row_item)
        blank_copy["question_cell"] = shift_cell(blank_copy.get("question_cell"), row_offset=row_offset)
        blank_copy["fm_range"]      = shift_cell(blank_copy.get("fm_range"), row_offset=row_offset)

        # append in a clean group order
        new_items.extend(left_block)
        new_items.extend(right_block)
        new_items.append(blank_copy)

    # replace sheet1 items with expanded list
    sheet1["Items"] = new_items

    print("Original manufacturers in data:", len(mfgs))
    print("Total Sheet1 items after expansion:", len(sheet1["Items"]))
    return template
import re

MFG_HDR_RE = re.compile(r"^Manufacturer\s+(\d+)$", re.IGNORECASE)

def enrich_sheet1_extractions_by_headers(
    template: dict,
    scores: dict,
    evidence: dict | None = None,
    *,
    sheet_no: int = 1,
    strict: bool = False,
) -> dict:
    """
    Enrich Sheet-1 extraction items using HEADER rows:
      - Applicant header: field == "Applicant"
      - Manufacturer header: field == "Manufacturer N"

    Then apply confidence/text_support to subsequent rows in that block based on field names.
    Does NOT rely on prefix for mapping.
    """

    sheet = next((s for s in template.get("Sheets", []) if s.get("sheet_no") == sheet_no), None)
    if not sheet:
        return template

    # ---- scores
    conf_root = (scores or {}).get("confidence", {}) or {}
    app_conf = conf_root.get("applicant", {}) or {}
    mfg_conf_list = conf_root.get("manufacturers", []) or []

    # ---- optional evidence
    ev_root = evidence or {}
    app_ev = ev_root.get("applicant", {}) or {}
    mfg_ev_list = ev_root.get("manufacturers", []) or []

    # Map your sheet field labels -> scoring keys
    # NOTE: Manufacturer N / Applicant headers map to "name"
    def field_to_score_key(field: str | None) -> str | None:
        if not field:
            return None
        f = field.strip()

        if f == "Applicant":
            return "name"

        if MFG_HDR_RE.match(f):
            return "name"

        if f == "Address":
            return "address"
        if f == "Country":
            return "country"
        if f == "Contact":
            return "contacts"
        if f == "Phone":
            return "phone"
        if f == "FAX":
            return "fax"
        if f == "Email":
            return "email"

        return None

    # current context while scanning rows
    current_kind = None   # "applicant" or "mfg"
    current_midx = None   # 0-based manufacturer index when current_kind=="mfg"

    for it in sheet.get("Items", []):
        if it.get("task_type") != "extraction":
            continue

        field = it.get("field")

        # ---- detect headers and switch context
        if field == "Applicant":
            current_kind = "applicant"
            current_midx = None
        else:
            m = MFG_HDR_RE.match((field or "").strip())
            if m:
                n = int(m.group(1))            # Manufacturer 1/2/3...
                midx = n - 1                   # list index
                if strict and (midx < 0 or midx >= len(mfg_conf_list)):
                    raise ValueError(f"Manufacturer {n} exists in template but scores has only {len(mfg_conf_list)} manufacturers.")
                current_kind = "mfg"
                current_midx = midx

        # ---- choose confidence object based on current context
        if current_kind == "applicant":
            conf_obj = app_conf
            ev_obj = app_ev
        elif current_kind == "mfg" and current_midx is not None and current_midx < len(mfg_conf_list):
            conf_obj = mfg_conf_list[current_midx] or {}
            ev_obj = mfg_ev_list[current_midx] if current_midx < len(mfg_ev_list) else {}
        else:
            # not inside applicant/manufacturer context -> skip
            continue

        # ---- apply confidence / evidence based on field label mapping
        key = field_to_score_key(field)
        if not key:
            continue

        if key in conf_obj:
            it["confidence"] = conf_obj[key]

        if evidence is not None and key in ev_obj:
            it["text_support"] = ev_obj[key]

    return template

def top_chunks_as_json(vs, question: str, k_search: int = 300, top_k: int = 5, text_chars: int = 3500, dedupe: bool = True):
    """
    One-function solution (no _get_scored_pairs).
    Returns a JSON-ready list of dicts:
      { "source": ..., "page_number": ..., "score": ..., "text": ... }
    """

    # 1) Get (Document, score) directly from vectorstore
    pairs = None
    last_err = None

    # Try the most common APIs safely (Azure Cosmos vectorstore supports similarity_search_with_score)
    for call in (
        lambda: vs.similarity_search_with_score(question, k=k_search),
        lambda: vs.similarity_search_with_score(question, k=k_search, search_type="vector"),
        lambda: vs.similarity_search_with_relevance_scores(question, k=k_search),  # may raise NotImplementedError
    ):
        try:
            pairs = call()
            break
        except Exception as e:
            last_err = e

    if pairs is None:
        raise RuntimeError(f"Could not fetch scored docs from vectorstore. Last error: {last_err}")

    # 2) Normalize output shape: relevance_scores returns (doc, score) too, but ensure it
    pairs = [(doc, float(score)) for (doc, score) in pairs]

    # 3) Decide sorting direction (similarity: higher better; distance: lower better)
    scores = [s for _, s in pairs if s is not None]
    looks_like_similarity = bool(scores) and (min(scores) >= 0.0 and max(scores) <= 1.0)
    reverse = looks_like_similarity  # similarity => DESC, distance => ASC

    pairs_sorted = sorted(pairs, key=lambda x: x[1], reverse=reverse)

    # 4) Build JSON
    out = []
    seen = set()

    for doc, score in pairs_sorted:
        md = doc.metadata or {}

        # dedupe key
        if dedupe:
            key = md.get("chunk_id") or md.get("id") or (
                md.get("source_file"),
                md.get("page") or md.get("page_label"),
                (doc.page_content or "")[:200],
            )
            if key in seen:
                continue
            seen.add(key)

        source = md.get("citation") or md.get("source_file") or md.get("source") or "UNKNOWN"
        page = md.get("page") or md.get("page_label")  # may be None / str / int

        out.append({
            "source": source,
            "page_number": int(page) if isinstance(page, (int, float)) else page,
            "score": float(score),
            "text": (doc.page_content or "")[:text_chars],
        })

        if len(out) >= top_k:
            break

    return out
