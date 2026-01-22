#!/usr/bin/env python
# coding: utf-8


from pathlib import Path
from typing import List, Dict, Any
from PyPDF2 import PdfReader
from PyPDF2.generic import IndirectObject
import fitz  # PyMuPDF
import base64
from dotenv import load_dotenv
import os
from pathlib import Path
import json
# Load .env from the current folder (where the notebook is)
# env_path = Path('.') / '.env'
# load_dotenv(dotenv_path=env_path)
from openai import OpenAI
#from dotenv import load_dotenv
import os
import importlib
import utility.cdr_report.CDR_Pipelines.configs as configs
# importlib.reload(configs)
from openai import AzureOpenAI

from utility.cdr_report.CDR_Pipelines.configs import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION
)


# AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
# AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
# AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

# 🔍 Optional sanity check (don’t print the key!)
#print("Endpoint:", AZURE_OPENAI_ENDPOINT)
#print("API version:", AZURE_OPENAI_API_VERSION)

# ✅ Azure OpenAI client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

def _resolve_indirect(obj):
    if isinstance(obj, IndirectObject):
        return obj.get_object()
    return obj


def _has_freetext_annotations(reader: PdfReader, max_pages: int = 3) -> bool:
    """Return True if any of the first `max_pages` pages contain /FreeText annotations.

    Many "editable"-looking PDFs (Fill & Sign / typewriter tools) store user-entered
    text as /FreeText annotations under each page's /Annots array. These are NOT
    AcroForm/XFA fields, so they won't appear under /Root -> /AcroForm.
    """

    try:
        pages = reader.pages
        n = min(len(pages), max_pages)

        for i in range(n):
            page = pages[i]
            annots = page.get("/Annots")
            annots = _resolve_indirect(annots) or []

            for a in annots:
                aobj = _resolve_indirect(a)
                subtype = aobj.get("/Subtype")
                # subtype is usually a NameObject like '/FreeText'
                if subtype and str(subtype) == "/FreeText":
                    return True
        return False
    except Exception:
        return False
def is_editable_form_pdf(path: Path) -> bool:
    """
    Return True if the PDF appears to contain *editable* content:
      - AcroForm fields (/Root -> /AcroForm -> /Fields)
      - XFA forms (/Root -> /AcroForm -> /XFA)
      - FreeText annotations (/Annots -> /Subtype /FreeText)

    Note: FreeText annotations are NOT form fields; they are an annotation layer.
    Ensures the file handle is closed (important on Windows) by using a 'with' block.
    """
    try:
        # Open the file explicitly so it gets closed after we're done
        with open(path, "rb") as f:
            reader = PdfReader(f)

            root = _resolve_indirect(reader.trailer.get("/Root"))
            if not root:
                return False

            acroform = root.get("/AcroForm")
            # If there's no AcroForm, it still may be "editable" via FreeText annotations.
            if not acroform:
                return _has_freetext_annotations(reader)

            acroform = _resolve_indirect(acroform)

            fields = acroform.get("/Fields")
            if isinstance(fields, IndirectObject):
                fields = fields.get_object()

            # If we have any form fields, it's editable
            if fields and len(fields) > 0:
                return True

            # Check for XFA forms as well
            xfa = acroform.get("/XFA")
            if isinstance(xfa, IndirectObject):
                xfa = xfa.get_object()

            if xfa:
                return True

            # No fields/XFA found. Fall back to FreeText annotations.
            return _has_freetext_annotations(reader)
    except Exception:
        return False

def flatten_and_get_images(input_path: str, output_path: str, dpi: int = 200):
    """
    Flattens the PDF AND returns a list of page images (pixmaps).
    Uses context managers so files are always closed, even on errors.
    """
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pixmaps = []

    # Ensure both documents are closed reliably
    with fitz.open(input_path) as src_doc, fitz.open() as out_doc:
        for page in src_doc:
            pix = page.get_pixmap(matrix=mat)
            pixmaps.append(pix)

            new_page = out_doc.new_page(width=pix.width, height=pix.height)
            new_page.insert_image(new_page.rect, pixmap=pix)

        out_doc.save(output_path)

    return pixmaps

# ============================
# 3) Convert pixmaps to PNG paths
# ============================

def save_pixmaps_to_images(pixmaps: List[fitz.Pixmap], out_dir: Path, stem: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    image_paths = []

    for i, pix in enumerate(pixmaps, start=1):
        img_path = out_dir / f"{stem}_page{i}.png"
        pix.save(str(img_path))
        image_paths.append(img_path)

    return image_paths


prompt_lm = """
You are reading a scanned "Client Information Sheet".

Extract ALL fields into a STRICT JSON object with this exact shape:

{
  "Applicant": {
    "Legal Entity Name": string or null,
    "DBA": string or null,
    "Street Address": string or null,
    "City, State, Postal Code, Country": string or null,
    "Phone Number": string or null,
    "Email": string or null,
    "Contacts": [
      {
        "Name": string or null,
        "Role": string or null,
        "Phone Number": string or null,
        "Email": string or null
      }
    ]
  },
  "Bill-To": {
    "Legal Entity Name": string or null,
    "Street Address": string or null,
    "City, State, Postal Code, Country": string or null,
    "Accounts Payable Contact": string or null,
    "Phone Number": string or null,
    "Email": string or null
  },
  "Manufacturer": {
    "Legal Entity Name": string or null,
    "Street Address": string or null,
    "City, State, Postal Code, Country": string or null,
    "Contacts": [
      {
        "Name": string or null,
        "Role": string or null,
        "Phone Number": string or null,
        "Email": string or null
      }
    ],
    "Estimated Production Date": string or null,
    "Labeling Method": string or null
  },
  "Completed By": string or null,
  "Dates": {
    "Form Completion": string or null
  },
  "Signatures": string or null
}

Rules:
- DO NOT put fields like "Legal Entity Name" at the root.
- All applicant fields must be inside "Applicant".
- All bill-to fields must be inside "Bill-To".
- All manufacturer/production facility fields must be inside "Manufacturer".
- Use null if something is missing or unreadable.
- Return ONLY JSON, no extra text.
"""

def image_to_data_uri(path: Path) -> str:
    b = path.read_bytes()
    b64 = base64.b64encode(b).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def extract_page_with_llm(img_path: Path) -> str:
    """
    Sends a single PNG page to GPT-4.1 (vision-enabled)
    and extracts structured JSON from the form.
    """
    data_uri = image_to_data_uri(img_path)

    prompt = prompt_lm

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ]
    )

    return response.choices[0].message.content

from pathlib import Path
import shutil
import time
from typing import Dict, Any

def process_pdfs(
    src_root: str = configs.SRC_ROOT,
    flattened_dir: str = configs.FLAT_ROOT,
    images_root: str = configs.IMG_ROOT,
    dpi: int = 200,
    archive_root: str | None = None,
) -> Dict[str, Any]:
    src_root = Path(src_root)
    flattened_dir = Path(flattened_dir)
    images_root = Path(images_root)

    flattened_dir.mkdir(exist_ok=True)
    images_root.mkdir(exist_ok=True)

    # ✅ NEW: archive folder NEXT TO src_root (same parent)
    if archive_root is None:
        archive_root = src_root.parent / "archived_editable"
    else:
        archive_root = Path(archive_root)

    archive_root.mkdir(parents=True, exist_ok=True)

    results: Dict[str, Any] = {}

    #print(f"Scanning {src_root.resolve()} ...")

    for pdf_path in src_root.glob("*.pdf"):
        if not pdf_path.is_file():
            continue

        #print(f"\nChecking {pdf_path.name}...")

        if not is_editable_form_pdf(pdf_path):
            #print(" → Not editable. Skipping.")
            continue

        #print(" → Editable PDF detected.")

        # 1) Flatten PDF
        flat_pdf_path = flattened_dir / f"{pdf_path.stem}_flat.pdf"
        pixmaps = flatten_and_get_images(str(pdf_path), str(flat_pdf_path), dpi=dpi)
        #print(" ✔ Flattened PDF created.")

        # 2) Archive original (now outside src_root)
        archive_path = archive_root / pdf_path.name
        #print(f"   → Archiving original editable to {archive_path}")

        for attempt in range(3):
            try:
                shutil.move(str(pdf_path), str(archive_path))
                break
            except PermissionError as e:
                #print(f"   ⚠️ PermissionError on move (attempt {attempt+1}/3): {e}")
                if attempt == 2:
                    print("   ❌ Skipping archive for this file. It may be open in another program.")
                else:
                    time.sleep(0.5)

        # 3) Save images + LLM extraction as you already do...
        img_dir = images_root / pdf_path.stem
        img_paths = save_pixmaps_to_images(pixmaps, img_dir, pdf_path.stem)

        llm_outputs = []
        for img_path in img_paths:
            #print(f"   → Sending {img_path.name} to GPT-4.1...")
            output = extract_page_with_llm(img_path)
            llm_outputs.append(output)

        results[pdf_path.name] = {
            "original": archive_path,
            "flattened": flat_pdf_path,
            "images": img_paths,
            "extracted": llm_outputs,
        }

    return results

def extract_cis():
    import utility.cdr_report.CDR_Pipelines.configs as configs
    configs.require_runtime()
    results = process_pdfs(
        src_root=configs.SRC_ROOT,
        flattened_dir=configs.FLAT_ROOT,
        images_root=configs.IMG_ROOT,
        dpi=200
    )

    
    all_cis=[]

    for pdfs in results.keys():
        dic_cis={}
        dic_cis['filename']=pdfs
        dic_cis['text']=results[pdfs]['extracted'][0]
        all_cis.append(dic_cis)
    return all_cis
# with open("src_files\\all_cis_info.txt", "w", encoding="utf-8") as f:
#     json.dump(all_cis, f, indent=4, default=str)

