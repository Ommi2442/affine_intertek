import re


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def excel_row(cell):
    if not cell:
        return 0
    m = re.search(r"(\d+)$", cell)
    return int(m.group(1)) if m else 0


# ------------------------------------------------------------
# Sheet 1: FULL replace Items from template
# ------------------------------------------------------------
def update_sheet1_items_from_template(cdr, template):
    cdr_sheet1 = next(
        (s for s in cdr.get("Sheets", []) if s.get("sheet_no") == 1),
        None
    )

    tpl_sheet1 = next(
        (s for s in template.get("Sheets", []) if s.get("sheet_no") == 1),
        None
    )

    if not cdr_sheet1 or not tpl_sheet1:
        print("⚠ Sheet 1 missing in CDR or template. Skipping.")
        return

    tpl_items = tpl_sheet1.get("Items")
    if not isinstance(tpl_items, list):
        print("⚠ Template Sheet 1 Items invalid. Skipping.")
        return

    cdr_sheet1["Items"] = tpl_items
    print(f"✅ Sheet 1 replaced with {len(tpl_items)} template items")


# ------------------------------------------------------------
# Sheet 2: Replace Items from A3 onwards using description
# ------------------------------------------------------------
def update_sheet2_items_from_description(cdr, description):
    sheet2 = next(
        (s for s in cdr.get("Sheets", []) if s.get("sheet_no") == 2),
        None
    )

    if sheet2 is None:
        print("⚠ Sheet 2 not found. Skipping.")
        return

    items = sheet2.setdefault("Items", [])

    # Preserve rows before A3
    preserved = [
        i for i in items
        if excel_row(i.get("question_cell")) < 3
    ]

    # ---- FIX: description can be list OR dict ----
    if isinstance(description, list):
        new_items = description
    elif isinstance(description, dict):
        new_items = description.get("Items", [])
    else:
        print("⚠ description invalid type. Skipping Sheet 2.")
        return

    if not isinstance(new_items, list):
        print("⚠ description.Items invalid. Skipping Sheet 2.")
        return

    sheet2["Items"] = preserved + new_items
    print(f"✅ Sheet 2 updated with {len(new_items)} items")


# ------------------------------------------------------------
# Sheet 3: Replace Items from A3 onwards using 3c2
# ------------------------------------------------------------
def update_sheet3_items(cdr, s3j):
    sheet3 = next(
        (s for s in cdr.get("Sheets", []) if s.get("sheet_no") == 3),
        None
    )

    if sheet3 is None:
        print("⚠ Sheet 3 not found. Skipping.")
        return

    items = sheet3.setdefault("Items", [])

    preserved = [
        i for i in items
        if excel_row(i.get("question_cell")) < 3
    ]

    new_items = s3j.get("Items", [])
    if not isinstance(new_items, list):
        print("⚠ 3c2.Items invalid. Skipping Sheet 3.")
        return

    sheet3["Items"] = preserved + new_items
    print(f"✅ Sheet 3 updated with {len(new_items)} items")


# ------------------------------------------------------------
# Sheet 4: Replace Rows from A3 onwards using 4c2
# ------------------------------------------------------------
def update_sheet4_rows(cdr, s4j):
    sheet4 = next(
        (s for s in cdr.get("Sheets", []) if s.get("sheet_no") == 4),
        None
    )

    if sheet4 is None:
        print("⚠ Sheet 4 not found. Skipping.")
        return

    rows = sheet4.setdefault("Rows", [])

    preserved = [
        r for r in rows
        if excel_row(r.get("start_cell")) < 3
    ]

    new_rows = s4j.get("Items", [])
    if not isinstance(new_rows, list):
        print("⚠ 4c2.Items invalid. Skipping Sheet 4.")
        return

    sheet4["Rows"] = preserved + new_rows
    print(f"✅ Sheet 4 updated with {len(new_rows)} rows")


# ------------------------------------------------------------
# Sheet 6: FULL replace Items from features
# ------------------------------------------------------------
def update_sheet6_items_from_features(cdr, features):
    cdr_sheet6 = next(
        (s for s in cdr.get("Sheets", []) if s.get("sheet_no") == 6),
        None
    )

    features_sheet6 = next(
        (s for s in features.get("Sheets", []) if s.get("sheet_no") == 6),
        None
    )

    if not cdr_sheet6 or not features_sheet6:
        print("⚠ Sheet 6 missing in CDR or features. Skipping.")
        return

    features_items = features_sheet6.get("Items")
    if not isinstance(features_items, list):
        print("⚠ Features Sheet 6 Items invalid. Skipping.")
        return

    cdr_sheet6["Items"] = features_items
    print(f"✅ Sheet 6 replaced with {len(features_items)} features items")


# ------------------------------------------------------------
# Orchestrator (THIS is what main.py calls)
# ------------------------------------------------------------
def post_process_cdr(cdr, template, description, features, s3j, s4j):
    """
    Applies all post-processing rules in correct order.
    """
    update_sheet1_items_from_template(cdr, template)
    update_sheet2_items_from_description(cdr, description)
    update_sheet6_items_from_features(cdr, features)
    update_sheet3_items(cdr, s3j)
    update_sheet4_rows(cdr, s4j)
    return cdr
