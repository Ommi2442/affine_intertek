import platform
import subprocess
import pythoncom
from docx2pdf import convert
from pathlib import Path
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


