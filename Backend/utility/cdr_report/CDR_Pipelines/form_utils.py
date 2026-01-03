import json
from utility.cdr_report.CDR_Pipelines.prompts import ref_prompt as prompt
# --------- Extraction utils from TRF ---------

def _norm(text: str) -> str:
    """Normalize label text for matching."""
    if not isinstance(text, str):
        return ""
    text = text.replace("\t", " ").replace("\n", " ")
    return " ".join(text.split()).strip().lower()


def get_field_value(trf_json: dict, *keywords: str):
    """
    Search all Tables / Items for a field whose label contains ALL the
    given keywords (case-insensitive). Return its 'value'.
    """
    tables = trf_json.get("Tables", [])
    kws = [_norm(k) for k in keywords]

    for table in tables:
        for item in table.get("Items", []):
            label = _norm(item.get("field", ""))
            if all(k in label for k in kws):
                return item.get("value")
    return None

def build_ref(trf_filled: dict) -> dict:
    """
    Takes TRF filled JSON (dict) and returns the 'ref' dict using the same logic.
    """
    ref = {
        "Report Number": get_field_value(trf_filled, "report number"),
        "Date of issue": get_field_value(trf_filled, "date of issue"),
        "Standard": get_field_value(trf_filled, "standard"),
        "Applicant": get_field_value(trf_filled, "Applicant’s name"),
        "Test item description": get_field_value(trf_filled, "test item description"),
        "Ratings": get_field_value(trf_filled, "ratings"),
        # works for your Table 8 entry, no hard-coding of table index:
        "General product information and other remarks": get_field_value(
            trf_filled,
            "general product information and other remarks",  # part of label
            "description of unit",                           # extra keyword
        ),
        "Description of model differences": get_field_value(
            trf_filled, "description of model differences"
        ),
        "Model/Type reference": get_field_value(
            trf_filled, "model/type reference"
        ),
        "Trade mark": get_field_value(
            trf_filled, "trade mark"
        ),
    }

    # text1 = "General product information and other remarks:"
    # text2 = "Description of unit:"
    # # ref["General product information and other remarks"] = (
    # #     ref["General product information and other remarks"]
    # #     .replace(text1, "")
    # #     .replace(text2, "")
    # # )
    # val = ref["General product information and other remarks"]
    # if isinstance(val, str):
    #     ref["General product information and other remarks"] = val.replace(text1, "").replace(text2, "").strip()

    key = "General product information and other remarks"
    val = ref.get(key)
    
    if isinstance(val, str):
        text1 = "General product information and other remarks:"
        text2 = "Description of unit:"
        ref[key] = val.replace(text1, "").replace(text2, "").strip()

    # 2) Replace None/empty/null-like values for ALL ref keys
    for k, v in ref.items():
        if v is None:
            ref[k] = "Info not in TRF"
        elif isinstance(v, str) and v.strip().lower() in {"", "null", "none"}:
            ref[k] = "Info not in TRF"

    return ref

# from azure.cosmos import CosmosClient
# cosmos_client = CosmosClient(url=COSMOS_URL, credential=COSMOS_KEY)
# container = cosmos_client.get_database_client(DB_NAME).get_container_client(CONT_NAME)
###########################################
## PROCESSING SHEET1-LLM OUTPUT ###########
###########################################
def _join(values, sep="\n", fallback="N/A"):
    """Join non-empty values, dedupe while keeping order; return fallback if nothing."""
    out, seen = [], set()
    for v in values or []:
        if v is None:
            continue
        v = str(v).strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return sep.join(out) if out else fallback


def to_tabular_json(data: dict) -> dict:
    """
    Builds tabular-style fields for applicant + manufacturers by combining contacts:
    Contact, Email, Phone, FAX
    """
    def pack(entity: dict, name_key="name"):
        contacts = (entity or {}).get("contacts") or []
        return {
            "Name": entity.get(name_key),
            "Address": entity.get("address"),
            "Country": entity.get("country"),
            "Contact": _join([c.get("name") for c in contacts if isinstance(c, dict)]),
            "Email":   _join([c.get("email") for c in contacts if isinstance(c, dict)]),
            "Phone":   _join([c.get("phone") for c in contacts if isinstance(c, dict)]),
            "FAX":     _join([c.get("fax") for c in contacts if isinstance(c, dict)]),
        }

    applicant = data.get("applicant") or {}
    manufacturers = data.get("manufacturers") or []

    applicant_section = {
        "Applicant": applicant.get("name"),
        "Address": applicant.get("address"),
        "Country": applicant.get("country"),
        "Contact": pack(applicant)["Contact"],
        "Phone":   pack(applicant)["Phone"],
        "FAX":     pack(applicant)["FAX"],
        "Email":   pack(applicant)["Email"],
    }

    manufacturers_section = []
    for m in manufacturers:
        if not isinstance(m, dict):
            continue
        packed = pack(m)
        manufacturers_section.append({
            "Label": m.get("label"),
            "Manufacturer": packed["Name"],
            "Address": packed["Address"],
            "Country": packed["Country"],
            "Contact": packed["Contact"],
            "Phone": packed["Phone"],
            "FAX": packed["FAX"],
            "Email": packed["Email"],
        })

    return {
        "ApplicantSection": applicant_section,
        "ManufacturersSection": manufacturers_section
    }


