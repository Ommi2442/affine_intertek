import platform
import subprocess
import pythoncom
from docx2pdf import convert
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
import json


from azure.storage.blob import ContentSettings

def convert_docx_to_pdf(docx_path: str, pdf_path: str):
    print('*************** 3.1 ******************************', docx_path)

    print('*************** 3.2 ******************************', pdf_path)


    system = platform.system().lower()

    print('*************** 3.3 ******************************', system)
    

    # ---------- WINDOWS (MS WORD via COM) ----------
    if system == "windows":
        pythoncom.CoInitialize()     # ✅ REQUIRED
        try:
            convert(docx_path, pdf_path)
        finally:
            pythoncom.CoUninitialize()  # ✅ REQUIRED
        return

    # ---------- LINUX (LIBREOFFICE) ----------
    if system == "linux":
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                os.path.dirname(pdf_path),
                docx_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    raise RuntimeError(f"Unsupported OS for DOCX conversion: {system}")



def fetch_final_json_record(container, project_id: str):
    query = """
        SELECT * FROM c
        WHERE c.project_id = @pid
        AND c.file_type = ".json"
    """

    params = [{"name": "@pid", "value": project_id}]

    items = list(
        container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        )
    )

    return items[0]




def replace_json_blob(
    blob_service,
    container_name: str,
    blob_path: str,
    json_data: dict
):
    blob_client = blob_service.get_blob_client(
        container=container_name,
        blob=blob_path
    )

    blob_client.upload_blob(
        json.dumps(json_data, indent=2, ensure_ascii=False),
        overwrite=True,
        content_settings=ContentSettings(
            content_type="application/json"
        )
    )



def replace_local_final_json(project_id: str, json_data: dict):
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data" / project_id
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    final_path = DATA_DIR / "final_output.json"

    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    return final_path




def update_docx_tables_from_json_arial(docx_path, json_path):
    """
    Update an existing DOCX in-place using JSON values.
    - Updates only cells where ai_fillable = True OR task_type = verdict_dependency
    - Applies Arial 10 font to updated cells
    - Saves changes back to the same DOCX file
    """

    doc = Document(docx_path)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for table_obj in data.get("Tables", []):
        table_index = table_obj.get("Table")

        # Skip invalid table index
        if table_index is None or table_index >= len(doc.tables):
            print(f"⚠️ Skipping missing table index: {table_index}")
            continue

        doc_table = doc.tables[table_index]

        for item in table_obj.get("Items", []):

            ai_fillable = item.get("ai_fillable", False)
            task_type = item.get("task_type")

            # Update only allowed fields
            if not ai_fillable and task_type != "verdict_dependency":
                continue

            row = item.get("answer_row")
            col = item.get("answer_column")
            value = item.get("value")

            if value is None:
                continue

            try:
                cell = doc_table.cell(row, col)
                cell.text = ""  # clear existing content

                p = cell.paragraphs[0]
                run = p.add_run(str(value))

                font = run.font
                font.name = "Arial"
                font.size = Pt(10)

                # Ensure Arial for East Asian text as well
                run._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")

            except Exception as e:
                print(
                    f"⚠️ Error updating table {table_index} "
                    f"cell ({row},{col}): {e}"
                )

    # Save back to the same DOCX
    doc.save(docx_path)
    print(f"✅ DOCX updated successfully → {docx_path}")



