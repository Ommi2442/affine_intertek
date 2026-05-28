import json
import os

# =========================================================
# CDR & TRF MAPPINGs
# =========================================================

LETTER_CDR_MAPPING = {
    "CUSTOMER NAME": ("Applicant", "Applicant"),
    "«AppCOMPANYNAME»": ("Applicant", "Applicant"),
    "«AppContactName»": ("Applicant", "Contact"),
    "«AppPhone»": ("Applicant", "Phone"),
    "«AppFax»": ("Applicant", "FAX"),
    "«AppEmail»": ("Applicant", "Email"),
    "«AppStreetAddress»": ("Applicant", "Address"),
}

LETTER_TRF_MAPPING = {
    "CUSTOMER NAME": "Applicant’s name\t:",
    "«AppCOMPANYNAME»": "Applicant’s name\t:",
    "«AppStreetAddress»": "Address\t:"
    }

# =========================================================
# BUILD CDR & TRF LOOKUPs
# =========================================================

def build_cdr_lookup(cdr_payload):

    lookup = {}

    for sheet in cdr_payload["Sheets"]:
        if sheet["sheet_no"] != 1:
            continue
        for item in sheet["Items"]:
            prefix = item.get("prefix")
            field = item.get("field")
            value = item.get("value")
            if prefix and field:
                lookup[(prefix, field)] = value

    return lookup


def build_trf_lookup(trf_payload):

    lookup = {}

    for table in trf_payload["Tables"]:
        for item in table["Items"]:
            field = item.get("field")
            value = item.get("value")
            if field:
                lookup[field] = value

    return lookup


# =========================================================
# OVERWRITE FUNCTION
# =========================================================

def overwrite_letter_values(letter_json, lookup, mapping):

    for page in letter_json["pages"]:
        for item in page["items"]:
            key = item.get("key")
            if key in mapping:
                source_key = mapping[key]
                if source_key in lookup:
                    value = lookup[source_key]
                    if value is not None:
                        item["value"] = value

    return letter_json



def letter_coherence(letter_json_path, letter_output_path, cdr_path, trf_path):

    try:
        with open(letter_json_path, "r", encoding="utf-8") as f:
            letter_json = json.load(f)

        updated_letter = letter_json

        # PRIORITY LOGIC
        if os.path.exists(cdr_path):
            print("Using CDR payload")

            with open(cdr_path, "r", encoding="utf-8") as f:
                cdr_payload = json.load(f)

            lookup = build_cdr_lookup(cdr_payload)
            updated_letter = overwrite_letter_values(letter_json,lookup,LETTER_CDR_MAPPING)

        elif os.path.exists(trf_path):
            print("Using TRF payload")

            with open(trf_path, "r", encoding="utf-8") as f:
                trf_payload = json.load(f)

            lookup = build_trf_lookup(trf_payload)
            updated_letter = overwrite_letter_values(letter_json,lookup,LETTER_TRF_MAPPING)

        else:
            print("Neither CDR nor TRF JSON found")


    except Exception as e:
        print(f"Letter coherence failed: {e}")
        updated_letter = letter_json


    # =========================================================
    # SAVE OUTPUT
    # =========================================================

    try:
        with open(letter_output_path, "w", encoding="utf-8") as f:
            json.dump(updated_letter, f, indent=4, ensure_ascii=False)
        print(f"{letter_output_path} updated successfully")

    except Exception as e:
        print(f"Failed to save letter output: {e}")