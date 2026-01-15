# ============================================================
# IMPORTS
# ============================================================

import os
import json
from azure.cosmos import CosmosClient
from langchain_openai import AzureChatOpenAI
from openai import AzureOpenAI

from utility.letter_report.deploymentV1.core import *
from utility.letter_report.deploymentV1.config import *

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
#from utils import *
from utility.letter_report.deploymentV1.config import *
from utility.letter_report.deploymentV1.core import *
from azure.storage.blob import BlobClient
from azure.core.exceptions import ResourceNotFoundError, AzureError
# from templates import *
from utility.letter_report.deploymentV1.trf_essential import *
from utility.letter_report.deploymentV1.trf_utils import *
import pandas as pd
import math
import copy
import time
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
from utility.letter_report.deploymentV1.ocr_image_processor import load_and_process_images

import requests
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient

from azure.storage.blob import ContainerClient
from dotenv import load_dotenv
load_dotenv()

AOAI_ENDPOINT = os.getenv("DS_DS_AOAI_ENDPOINT")
AOAI_KEY = os.getenv("DS_AOAI_KEY")
API_VERSION = os.getenv("DS_API_VERSION")
EMBED_DEPLOY = os.getenv("DS_EMBED_DEPLOY")
COSMOS_URL = os.getenv("DS_COSMOS_URL")
COSMOS_KEY = os.getenv("DS_COSMOS_KEY")
DB_NAME=os.getenv("DS_DB_NAME")
CONT_NAME=os.getenv("DS_CONT_NAME")
DB_NAME_IMG=os.getenv("DB_NAME_IMG")
CONT_NAME_IMG=os.getenv("DS_CONT_NAME_IMG")
CHAT_DEPLOY=os.getenv("DS_CHAT_DEPLOY")




# ============================================================
# NOTEBOOK FUNCTIONS (PASTED AS-IS — ZERO MODIFICATION)
# ============================================================

# --------- ALL FUNCTIONS FROM letter_generation.ipynb ----------
# (Kept exactly as provided by you)

# [PASTE ALL YOUR FUNCTIONS HERE — UNCHANGED]
# find_cis_pdf
import os
import pdfplumber
from fuzzywuzzy import fuzz

def find_cis_pdf(folder_path, min_threshold_for_strong_match=70):
    """
    Scans all PDFs in the folder and returns the one with the highest CIS similarity score.
    Always returns the best candidate (the one with maximum matches).
    
    Returns:
        dict with:
            - 'filename': best matching PDF
            - 'score': percentage of key phrases found (0-100)
            - 'found_phrases': list of detected key phrases
            - 'phrase_details': dict of all phrases with their match scores
            - 'is_strong_match': True if score >= threshold
    """
    # Key phrases that uniquely identify an Intertek CIS form
    key_phrases = [
        "CLIENT INFORMATION SHEET (CIS)",
        "ETL Certification and Follow-Up Services",
        "Applicant:",
        "CellFE, Inc.",
        "Bill-To:",
        "Manufacturer:",
        "Gener8",                  # Appears in email or company name
        "Labeling Method:",
        "Obtained from another source (Direct Imprint)",
        "Purchased from Intertek",
        "Completed By:",
        "SFT-ET-OP-19c",
        "Intertek"
    ]
    
    best_filename = None
    best_score = -1
    best_found = []
    best_details = {}
    
    if not os.path.isdir(folder_path):
        raise ValueError(f"Folder not found: {folder_path}")
    
    print("Scanning PDFs for CIS form...\n")
    
    for filename in sorted(os.listdir(folder_path)):
        if not filename.lower().endswith('.pdf'):
            continue
            
        pdf_path = os.path.join(folder_path, filename)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    continue
                    
                page = pdf.pages[0]
                
                # 1. Try enhanced text extraction
                text = page.extract_text(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=True,
                    use_text_flow=True
                )
                
                # 2. Supplement with table extraction (critical for forms)
                table_text = ""
                for table in page.extract_tables():
                    for row in table:
                        cleaned = [cell.strip() if cell else "" for cell in row]
                        table_text += " ".join(cleaned) + "\n"
                
                # Combine both
                full_text = (text or "") + "\n" + table_text
                full_text_lower = full_text.lower()
                
                # 3. Fallback: word-level if still poor
                if len(full_text.strip()) < 300:
                    words = page.extract_words(x_tolerance=3, y_tolerance=3)
                    word_text = " ".join([w['text'] for w in words])
                    full_text_lower = (full_text_lower + " " + word_text.lower()).strip()
                
                # Evaluate matches
                found_phrases = []
                phrase_scores = {}
                
                for phrase in key_phrases:
                    ratio = fuzz.partial_ratio(phrase.lower(), full_text_lower)
                    phrase_scores[phrase] = ratio
                    if ratio > 82:  # Reliable threshold for partial match
                        found_phrases.append(phrase)
                
                match_count = len(found_phrases)
                score = (match_count / len(key_phrases)) * 100
                
                print(f"{filename}")
                print(f"   → {match_count}/{len(key_phrases)} key phrases found (score: {score:.1f}%)")
                if found_phrases:
                    print(f"   Found: {found_phrases}")
                else:
                    print(f"   Found: None")
                print()
                
                # Update best
                if score > best_score:
                    best_score = score
                    best_filename = filename
                    best_found = found_phrases
                    best_details = phrase_scores
                    
        except Exception as e:
            print(f"Error reading {filename}: {e}\n")
            continue
    
    # Always return the best one (maximum similarity)
    is_strong = best_score >= min_threshold_for_strong_match
    
    print("="*60)
    if best_filename:
        print(f"BEST CIS CANDIDATE: {best_filename}")
        print(f"Score: {best_score:.1f}% ({len(best_found)}/{len(key_phrases)} phrases matched)")
        print(f"Strong match: {is_strong}")
        print(f"Key phrases found: {best_found}")
    else:
        print("No PDFs found in folder.")
    
    return {
        'filename': best_filename,
        'score': best_score,
        'found_phrases': best_found,
        'phrase_details': best_details,
        'is_strong_match': is_strong
    }


import os
import pdfplumber
from fuzzywuzzy import fuzz

def find_cis_pdf(folder_path, min_threshold_for_strong_match=70):
    """
    Scans all PDFs in the folder and returns the one with the highest CIS similarity score.
    Always returns the best candidate (the one with maximum matches).
    
    Returns:
        dict with:
            - 'pdf_path': full path to best matching PDF
            - 'filename': best matching PDF filename
            - 'score': percentage of key phrases found (0-100)
            - 'found_phrases': list of detected key phrases
            - 'phrase_details': dict of all phrases with their match scores
            - 'is_strong_match': True if score >= threshold
    """
    # Key phrases that uniquely identify an Intertek CIS form
    key_phrases = [
        "CLIENT INFORMATION SHEET (CIS)",
        "ETL Certification and Follow-Up Services",
        "Applicant:",
        "CellFE, Inc.",
        "Bill-To:",
        "Manufacturer:",
        "Gener8",                  # Appears in email or company name
        "Labeling Method:",
        "Obtained from another source (Direct Imprint)",
        "Purchased from Intertek",
        "Completed By:",
        "SFT-ET-OP-19c",
        "Intertek"
    ]
    
    best_pdf_path = None
    best_filename = None
    best_score = -1
    best_found = []
    best_details = {}
    
    if not os.path.isdir(folder_path):
        raise ValueError(f"Folder not found: {folder_path}")
    
    print("Scanning PDFs for CIS form...\n")
    
    for filename in sorted(os.listdir(folder_path)):
        if not filename.lower().endswith('.pdf'):
            continue
            
        pdf_path = os.path.join(folder_path, filename)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    continue
                    
                page = pdf.pages[0]
                
                # 1. Try enhanced text extraction
                text = page.extract_text(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=True,
                    use_text_flow=True
                )
                
                # 2. Supplement with table extraction (critical for forms)
                table_text = ""
                for table in page.extract_tables():
                    for row in table:
                        cleaned = [cell.strip() if cell else "" for cell in row]
                        table_text += " ".join(cleaned) + "\n"
                
                # Combine both
                full_text = (text or "") + "\n" + table_text
                full_text_lower = full_text.lower()
                
                # 3. Fallback: word-level if still poor
                if len(full_text.strip()) < 300:
                    words = page.extract_words(x_tolerance=3, y_tolerance=3)
                    word_text = " ".join([w['text'] for w in words])
                    full_text_lower = (full_text_lower + " " + word_text.lower()).strip()
                
                # Evaluate matches
                found_phrases = []
                phrase_scores = {}
                
                for phrase in key_phrases:
                    ratio = fuzz.partial_ratio(phrase.lower(), full_text_lower)
                    phrase_scores[phrase] = ratio
                    if ratio > 82:  # Reliable threshold for partial match
                        found_phrases.append(phrase)
                
                match_count = len(found_phrases)
                score = (match_count / len(key_phrases)) * 100
                
                print(f"{filename}")
                print(f"   → {match_count}/{len(key_phrases)} key phrases found (score: {score:.1f}%)")
                if found_phrases:
                    print(f"   Found: {found_phrases}")
                else:
                    print(f"   Found: None")
                print()
                
                # Update best
                if score > best_score:
                    best_score = score
                    best_pdf_path = pdf_path
                    best_filename = filename
                    best_found = found_phrases
                    best_details = phrase_scores
                    
        except Exception as e:
            print(f"Error reading {filename}: {e}\n")
            continue
    
    # Always return the best one (maximum similarity)
    is_strong = best_score >= min_threshold_for_strong_match
    
    print("="*60)
    if best_pdf_path:
        print(f"BEST CIS CANDIDATE: {best_filename}")
        print(f"Path: {best_pdf_path}")
        print(f"Score: {best_score:.1f}% ({len(best_found)}/{len(key_phrases)} phrases matched)")
        print(f"Strong match: {is_strong}")
        print(f"Key phrases found: {best_found}")
    else:
        print("No PDFs found in folder.")
    
    return {
        'pdf_path': best_pdf_path,
        'filename': best_filename,
        'score': best_score,
        'found_phrases': best_found,
        'phrase_details': best_details,
        'is_strong_match': is_strong
    }


import pdfplumber

def extract_cis_fields(pdf_path: str) -> dict:
    """
    Extract form field values from a filled PDF Client Information Sheet.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary with extracted field values
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        
        # Extract all form field annotations
        annots = page.annots if hasattr(page, 'annots') and page.annots else []
        
        # Build a dictionary of field values by field name
        fields = {}
        for annot in annots:
            if 'data' in annot and 'T' in annot['data']:
                field_name = annot['data']['T'].decode('utf-8') if isinstance(annot['data']['T'], bytes) else annot['data']['T']
                if 'V' in annot['data']:
                    field_value = annot['data']['V']
                    if isinstance(field_value, bytes):
                        field_value = field_value.decode('utf-8')
                    # Clean up whitespace (only for strings)
                    if isinstance(field_value, str):
                        field_value = field_value.strip()
                    fields[field_name] = field_value
        
        # Extract specific fields based on the form field names
        # Field '1' = Legal Entity Name (Applicant)
        # Field '3' = Street Address
        # Field '4' = City, State, Postal Code, Country
        # Field '5' = Contacts (Primary)
        # Field '6' = Phone Number
        # Field '7' = Email
        company = fields.get('1', '')
        street = fields.get('3', '')
        city_state_zip = fields.get('4', '')
        contact_name = fields.get('5', '')
        phone = fields.get('6', '')
        email = fields.get('7', '')
        
        # Project Manager info
        # "Labeling Method" field contains the PM name (Shivam Patel)
        # Manufacturer contact email field contains the PM email
        pm_name = fields.get('Labeling Method', '')
        pm_email = fields.get('Location where final assembly will take place andor where Certification label will be applied 6', '')
        
        project_manager = None
        if pm_name and pm_email:
            project_manager = f"{pm_name}, {pm_email}"
        elif pm_name:
            project_manager = pm_name
        
        return {
            "CUSTOMER NAME": company,
            "«AppContactName»": contact_name,
            "«AppPhone»": phone,
            "«AppCOMPANYNAME»": company,
            "«AppStreetAddress»": street,
            "«AppEmail»": email,
            "«AppCityStZip»": city_state_zip,
            "Project Manager Name + Email": project_manager
        }

def find_and_extract_cis(folder_path, min_threshold_for_strong_match=70):
    """
    Finds and extracts fields from CIS PDF in one call.
    
    Returns:
        Extracted fields dict, or None if CIS not found or extraction failed
    """
    # Find the CIS PDF
    detection = find_cis_pdf(folder_path, min_threshold_for_strong_match)
    
    if not detection['pdf_path']:
        print("No CIS document found.")
        return None
    
    # Extract fields from it
    try:
        fields = extract_cis_fields(detection['pdf_path'])
        return fields
    except Exception as e:
        print(f"Error extracting fields: {e}")
        return None

# extract_cis_fields
# find_and_extract_cis
# contains_prepared_for_table

import os
import re
import fitz  # PyMuPDF


def contains_prepared_for_table(pdf_path):
    """
    Check if PDF contains the specific 'Prepared For:' table with expected structure.
    Looks for key indicators like name, company, address, phone, email pattern.
    """
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            t = page.get_text()
            if t:
                text += t + "\n"
    
    # Look for "Prepared For:" header
    if not re.search(r"Prepared\s*For\s*:", text, re.IGNORECASE):
        return False
    
    # Extract the section after "Prepared For:"
    match = re.search(r"Prepared\s*For\s*:(.{0,500})", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return False
    
    section = match.group(1)
    
    # Check for multiple indicators that this is the specific table structure
    indicators = [
        r"Gener8\s*LLC",  # Company name
        r"\(\d{3}\)\s*\d{3}-\d{4}",  # Phone number pattern like (650) 940-9898
        r"\w+@\w+\.\w+",  # Email pattern
        r"San\s*Jose|CA\s*95134|USA",  # Address components
        r"Consultant"  # Role/title
    ]
    
    # Require at least 3 of these indicators to be present in the section
    matches = sum(1 for pattern in indicators if re.search(pattern, section, re.IGNORECASE))
    
    return matches >= 3


def find_prepared_for_pdf(folder_path: str):
    """
    Find the PDF that contains the specific 'Prepared For:' table.
    Returns the full PDF path or None if not found.
    """
    for file in os.listdir(folder_path):
        if file.lower().endswith(".pdf"):
            pdf_path = os.path.join(folder_path, file)
            if contains_prepared_for_table(pdf_path):
                return pdf_path  # Return full path instead of just filename
    
    return None


import re
from PyPDF2 import PdfReader

def extract_prepared_for_generic(pdf_path: str) -> dict:
    """
    Extract customer information and project details from an Intertek proposal PDF.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary containing:
        - CUSTOMER NAME
        - AppContactName
        - AppPhone
        - AppCOMPANYNAME
        - AppStreetAddress
        - AppEmail
        - AppCityStZip
        - Project Name / Scope of Work
    """
    text = "\n".join(page.extract_text() or "" for page in PdfReader(pdf_path).pages)
    
    # Isolate Prepared For section only
    block = re.search(
        r"Prepared\s*For[:\s]*([\s\S]*?)(?:\nPrepared\s*by:|\nScope\s*of\s*Work:|\nProject|\Z)",
        text,
        re.IGNORECASE
    )
    block_text = block.group(1).strip() if block else text
    lines = [l.strip() for l in block_text.split("\n") if l.strip()]
    
    # Contact name = first line
    contact_name = lines[0] if lines else None
    
    # Company name = first company-like line
    company = None
    for line in lines:
        if re.search(r"\b(LLC|Inc|Company|Corp|Co\.|Pvt|Ltd|Limited|Group|Services|Net)\b", line, re.IGNORECASE):
            company = line
            break
    
    # Collect address lines after company
    address = ""
    if company:
        collecting = False
        addr = []
        for line in lines:
            if line == company:
                collecting = True
                continue
            if collecting:
                if re.search(r"Consultant|Representative|Prepared\s*by:|Scope\s*of\s*Work:", line, re.IGNORECASE):
                    break
                addr.append(line)
        address = ", ".join(addr)
    
    # Extract phone (first valid phone found anywhere in section)
    phone_match = re.search(r"\(?\+?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}", block_text)
    phone = phone_match.group(0) if phone_match else None
    
    # Extract email (if multiple, pick first that is NOT an intertek internal email)
    email_matches = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", block_text)
    email = None
    if email_matches:
        for e in email_matches:
            if "intertek" not in e.lower():
                email = e
                break
        if not email:
            email = email_matches[0]
    
    # City/Zip
    zip_match = re.search(r"\b\d{5,6}\b", address)
    city_zip = zip_match.group(0) if zip_match else None
    
    # Extract Project Name / Scope of Work
    # Try multiple patterns to find the project name
    project_name = None
    
    # Pattern 1: "PROJECT NAME" followed by the name on next line(s)
    # Stop at common headers like COMPILED BY, DATE, Prepared, etc.
    project_match = re.search(
        r"PROJECT\s*NAME[:\s]*\n([^\n]+(?:\n(?!(?:COMPILED|DATE|Prepared|QUOTE|Testing|Assumptions)[:\s])[^\n]+)*)",
        text,
        re.IGNORECASE | re.MULTILINE
    )
    if project_match:
        # Clean up the extracted text
        raw_text = project_match.group(1).strip()
        # Remove any trailing sections that start with all-caps words
        clean_text = re.sub(r'\s*(?:COMPILED|DATE|Prepared|QUOTE).*$', '', raw_text, flags=re.IGNORECASE)
        project_name = " ".join(clean_text.split())
    
    # Pattern 2: "Scope of Work:" followed by the description
    if not project_name:
        scope_match = re.search(
            r"Scope\s*of\s*Work[:\s]*\n([^\n]+)",
            text,
            re.IGNORECASE | re.MULTILINE
        )
        if scope_match:
            project_name = scope_match.group(1).strip()
    
    # Pattern 3: Look for certification-related text patterns
    if not project_name:
        cert_match = re.search(
            r"(c?ETL[uU]s?/?\w*\s+certification[^.\n]+)",
            text,
            re.IGNORECASE
        )
        if cert_match:
            project_name = cert_match.group(1).strip()
    
    return {
        "CUSTOMER NAME": company,
        "«AppContactName»": contact_name,
        "«AppPhone»": phone,
        "«AppCOMPANYNAME»": company,
        "«AppStreetAddress»": address,
        "«AppEmail»": email,
        "«AppCityStZip»": city_zip,
        "Scope of Work": project_name
    }
def process_quote_from_folder(folder_path: str):
    """
    Find the quote PDF in the folder and extract the 'Prepared For' information from it.
    
    Args:
        folder_path: Path to the folder containing PDFs
        
    Returns:
        Extracted fields from the quote PDF, or None if no quote PDF found
    """
    # Find the quote PDF
    quote_pdf_path = find_prepared_for_pdf(folder_path)
    
    if quote_pdf_path is None:
        print(f"No quote PDF found in folder: {folder_path}")
        return None
    
    print(f"Found quote PDF: {quote_pdf_path}")
    
    # Extract fields from the quote PDF
    fields = extract_prepared_for_generic(quote_pdf_path)
    
    return fields

# find_prepared_for_pdf
# extract_prepared_for_generic
# process_quote_from_folder
# update_scope_of_work_in_json
import json

def update_scope_of_work_in_json(input_json_path, output_json_path, extracted_data):
    """
    Reads input JSON file
    Updates value of:
      - key == "KEY1"
      - key == "<ETL Listing/CB/Other Evaluation>"
    using Scope of Work from extracted_data
    Writes updated JSON to output file
    """

    scope_of_work = extracted_data.get("Scope of Work", "")

    # Load input JSON
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Traverse pages and items
    for page in data.get("pages", []):
        for item in page.get("items", []):
            if item.get("key") in ["KEY1", "<ETL Listing/CB/Other Evaluation>"]:
                item["value"] = scope_of_work

    # Write output JSON
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated JSON saved to: {output_json_path}")

# merge_quote_and_cis_data

def merge_quote_and_cis_data(folder_path: str, min_threshold_for_strong_match=70):

    """

    Extract data from Quote PDF and CIS PDF, then merge into a single JSON.

    Quote data gets first priority. CIS fills only missing/empty fields.

    """



    quote_data = process_quote_from_folder(folder_path)

    cis_data = find_and_extract_cis(folder_path, min_threshold_for_strong_match)



    if quote_data is None and cis_data is None:

        print("No data extracted from either Quote or CIS documents.")

        return None



    merged_data = {}



    # Step 1: Fill quote data first

    if quote_data:

        merged_data.update(quote_data)



    # Step 2: CIS fills only missing or empty values, DOES NOT override quote values

    if cis_data:

        for k, v in cis_data.items():

            if k not in merged_data or merged_data[k] in ["", None]:

                merged_data[k] = v



    # Step 3: Save output JSON in same folder

    output_path = os.path.join(folder_path, "letter_f1.json")

    with open(output_path, "w", encoding="utf-8") as f:

        json.dump(merged_data, f, indent=2, ensure_ascii=False)



    return merged_data


# fill_letter_json

def fill_letter_json(
    src_dir: str,
    letter_json_path: str,
    output_path: str = "letter.json"
):
    """
    Fill letter.json values using data extracted from source directory
    and save to a new file.

    Args:
        src_dir: Path to source files directory
        letter_json_path: Path to the input letter.json file
        output_path: Output file path (default = letter_f1.json)

    Returns:
        Updated JSON dict
    """

    # --------------------------------------------------
    # Step 1: Run merge pipeline internally
    # --------------------------------------------------
    extracted_data = merge_quote_and_cis_data(src_dir)

    if not extracted_data:
        raise ValueError("merge_quote_and_cis_data returned empty data")

    # --------------------------------------------------
    # Step 2: Load letter JSON
    # --------------------------------------------------
    with open(letter_json_path, "r", encoding="utf-8") as f:
        letter_json = json.load(f)

    # --------------------------------------------------
    # Step 3: Fill values
    # --------------------------------------------------
    for page in letter_json.get("pages", []):
        for item in page.get("items", []):
            key = item.get("key")
            if key in extracted_data and extracted_data[key]:
                item["value"] = extracted_data[key]

    # --------------------------------------------------
    # Step 4: Save output
    # --------------------------------------------------
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(letter_json, f, indent=2, ensure_ascii=False)

    return letter_json

# replace_keys_with_values_no_format_change_all
# this will chnage filders from json. Run after UI recivees new data
from docx import Document

def replace_keys_with_values_no_format_change_all(
    input_docx: str,
    output_docx: str,
    data: dict
):
    """
    Replaces placeholders with values WITHOUT changing formatting.
    Works even if Word splits placeholder across multiple runs.
    """

    doc = Document(input_docx)

    # Build replacement map
    replacements = {}
    for page in data.get("pages", []):
        for item in page.get("items", []):
            key = str(item.get("key", "")).strip()
            value = str(item.get("value", "")).strip()
            if not key:
                continue
            replacements[key] = value
            replacements[f"<{key}>"] = value  # optional bracket form

    # --- RUN JOIN FALLBACK REPLACEMENT ---
    def replace_in_para(para):
        full_text = "".join(run.text for run in para.runs)
        for old, new in replacements.items():
            if old in full_text:
                full_text = full_text.replace(old, new)

        # Push replaced text back while keeping formatting
        for run in para.runs:
            run.text = ""  # clear
        if para.runs:
            para.runs[0].text = full_text  # write in first run

    # Replace in paragraphs
    for para in doc.paragraphs:
        replace_in_para(para)

    # Replace in tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    replace_in_para(para)

    doc.save(output_docx)


from docx import Document

def replace_keys_with_values_no_format_change_v2(
    input_docx,
    output_docx,
    data
):
    """
    Replaces placeholders with values WITHOUT changing formatting.
    Works even if Word splits placeholder across multiple runs.
    Only replaces keys where ai_fillable == True.
    """

    doc = Document(input_docx)

    # -------------------------------------------------
    # Build replacement map (ai_fillable only)
    # -------------------------------------------------
    replacements = {}

    for page in data.get("pages", []):
        for item in page.get("items", []):

            if item.get("ai_fillable") is not True:
                continue

            key = str(item.get("key", "")).strip()
            value = str(item.get("value", "")).strip()

            if not key:
                continue

            replacements[key] = value
            replacements[f"<{key}>"] = value  # optional bracket form

    # -------------------------------------------------
    # Run-join fallback replacement
    # -------------------------------------------------
    def replace_in_para(para):
        if not para.runs:
            return

        full_text = "".join(run.text for run in para.runs)

        for old, new in replacements.items():
            if old in full_text:
                full_text = full_text.replace(old, new)

        # Clear runs but keep formatting
        for run in para.runs:
            run.text = ""

        para.runs[0].text = full_text

    # -------------------------------------------------
    # Replace in paragraphs
    # -------------------------------------------------
    for para in doc.paragraphs:
        replace_in_para(para)

    # -------------------------------------------------
    # Replace in tables
    # -------------------------------------------------
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    replace_in_para(para)

    doc.save(output_docx)

# replace_keys_with_values_no_format_change_v2
# get_first_doc_or_docx

def get_first_doc_or_docx(folder_path):
    """
    Returns the full path of the first .doc or .docx file found in a folder.
    Returns None if no such file exists.
    """
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    for filename in sorted(os.listdir(folder_path)):
        if filename.lower().endswith((".doc", ".docx")):
            return os.path.join(folder_path, filename)

    return None

# extract_table1a

# format_critical_components_df
# insert_dataframe_below_anchor
# read_docx_full
# extract_iec61010_non_conformances_full_doc

def insert_dataframe_below_anchor(
    input_docx,
    output_docx,
    df,
    anchor_text
):
    doc = Document(input_docx)

    anchor_paragraph = None
    for para in doc.paragraphs:
        if anchor_text in para.text:
            anchor_paragraph = para
            break

    if anchor_paragraph is None:
        raise ValueError("Anchor text not found in document.")

    # -------------------------------------------------
    # INSERT BLANK PARAGRAPH AFTER ANCHOR (XML SAFE)
    # -------------------------------------------------
    blank_p = OxmlElement("w:p")
    anchor_paragraph._p.addnext(blank_p)

    # -------------------------------------------------
    # CREATE TABLE
    # -------------------------------------------------
    rows, cols = df.shape
    table = doc.add_table(rows=rows + 1, cols=cols)
    table.style = "Table Grid"

    # -----------------------------
    # Header row (Amber background)
    # -----------------------------
    for col_idx, col_name in enumerate(df.columns):
        cell = table.rows[0].cells[col_idx]
        cell.text = str(col_name)

        tc_pr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "FFC000")  # Amber
        tc_pr.append(shd)

    # -----------------------------
    # Data rows
    # -----------------------------
    for row_idx in range(rows):
        for col_idx in range(cols):
            table.rows[row_idx + 1].cells[col_idx].text = str(df.iat[row_idx, col_idx])

    # -------------------------------------------------
    # INSERT TABLE AFTER BLANK PARAGRAPH
    # -------------------------------------------------
    blank_p.addnext(table._element)

    doc.save(output_docx)



from docx import Document

def read_docx_full(path):
    doc = Document(path)
    content = []

    # Read normal paragraphs
    for p in doc.paragraphs:
        if p.text.strip():
            content.append(p.text.strip())

    # Read ALL tables (CRITICAL for IEC TRFs)
    for table in doc.tables:
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    row_text.append(cell_text)
            if row_text:
                content.append(" | ".join(row_text))

    return "\n".join(content)

def extract_iec61010_non_conformances_full_doc(
    document_text,
    deployment_name
):
    system_prompt = """
You are an IEC 61010-1 CB Scheme compliance expert.

TASK:
- Review the FULL Test Report Form (TRF)
- Compare each clause with IEC 61010-1 requirements
- Identify ONLY NON-CONFORMANCES

RULES:
- Verdict = F → Non-conformance
- Missing mandatory markings or documentation → Non-conformance
- TBD = testing not yet performed → DO NOT list
- N/A with justification → Ignore
- Do NOT invent issues

OUTPUT (STRICT JSON ARRAY):
[
  {
    "clause": "5.1.3",
    "requirement": "Equipment shall be marked with rated voltage, current, and frequency",
    "finding": "No electrical ratings marked on the equipment"
  }
]

Return [] if no non-conformances exist.
"""
    client = AzureOpenAI(
        api_key=DS_AOAI_KEY,
        api_version=DS_API_VERSION,
        azure_endpoint=DS_AOAI_ENDPOINT
    )

    response = client.chat.completions.create(
        model=deployment_name,   # MUST be Azure deployment name
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""
FULL TRF DOCUMENT:
------------------
{document_text}
------------------
"""
            }
        ]
    )

    output = response.choices[0].message.content.strip()
    findings = json.loads(output)

    return pd.DataFrame(
        findings,
        columns=["clause", "requirement", "finding"]
    ).rename(columns={
        "clause": "Clause",
        "requirement": "Requirement of the Clause",
        "finding": "Remark and Findings"
    })

# download_files_from_blob
# extract_images_from_docx
# extract_images_from_excel
# identify_iec61010_non_conforming_images_batch
def download_files_from_blob(
    blob_file_list,
    download_dir,
    connection_string,
    container_name
):
    """
    Downloads files from Azure Blob Storage.
    Supports full blob URLs and validates container name.
    """

    # ----------------------------------------
    # Validate & normalize container name
    # ----------------------------------------
    if not isinstance(container_name, str):
        raise ValueError(f"container_name must be string. Got: {type(container_name)}")

    container_name = container_name.strip()

    if container_name.startswith("http"):
        parsed = urlparse(container_name)
        container_name = parsed.path.strip("/").split("/")[0]

    if not container_name:
        raise ValueError("container_name is empty after normalization")

    print(f"📦 Using container: {container_name}")

    os.makedirs(download_dir, exist_ok=True)

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    downloaded_files = []

    for blob_item in blob_file_list:

        # -----------------------------------
        # Handle full blob URL or blob name
        # -----------------------------------
        if blob_item.startswith("http"):
            parsed = urlparse(blob_item)
            path_parts = parsed.path.strip("/").split("/")
            blob_name = "/".join(path_parts[1:])   # remove container part
        else:
            blob_name = blob_item

        local_path = os.path.join(download_dir, os.path.basename(blob_name))

        print(f"⬇️ Downloading blob: {blob_name}")

        blob_client = container_client.get_blob_client(blob_name)

        with open(local_path, "wb") as f:
            f.write(blob_client.download_blob().readall())

        downloaded_files.append(local_path)

    return downloaded_files


import os
from docx import Document

def extract_images_from_docx(docx_path, output_dir=None):
    """
    Extracts all images from a .docx file and saves them to output_dir
    (defaults to current working directory).
    """
    image_paths= []
    if output_dir is None:
        output_dir = os.getcwd()

    os.makedirs(output_dir, exist_ok=True)

    doc = Document(docx_path)
    image_count = 0

    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            image_count += 1
            image = rel.target_part.blob
            image_ext = rel.target_part.content_type.split("/")[-1]

            image_filename = f"extracted_image_{image_count}.{image_ext}"
            image_path = os.path.join(output_dir, image_filename)

            with open(image_path, "wb") as f:
                f.write(image)
            image_paths.append(image_path)

    return image_paths,image_count



import os
import subprocess
import platform
from openpyxl import load_workbook

def extract_images_from_excel(excel_path, output_dir=None):
    """
    Extract images from Excel files.
    - .xlsx / .xlsm: direct
    - .xls: converted using LibreOffice
    Works on Linux and Windows.
    """

    if output_dir is None:
        output_dir = os.getcwd()

    os.makedirs(output_dir, exist_ok=True)
    excel_path = os.path.abspath(excel_path)
    lower = excel_path.lower()

    # ----------------------------------
    # Locate LibreOffice executable
    # ----------------------------------
    if platform.system() == "Windows":
        soffice = r"C:\Program Files\LibreOffice\program\soffice.exe"
        if not os.path.exists(soffice):
            soffice = r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
        if not os.path.exists(soffice):
            raise RuntimeError("LibreOffice is not installed or soffice.exe not found")
    else:
        soffice = "soffice"

    # ----------------------------------
    # Convert .xls -> .xlsx if needed
    # ----------------------------------
    if lower.endswith(".xls") and not lower.endswith(".xlsx"):
        subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to",
                "xlsx",
                "--outdir",
                output_dir,
                excel_path,
            ],
            check=True,
        )

        base = os.path.splitext(os.path.basename(excel_path))[0]
        excel_path = os.path.join(output_dir, base + ".xlsx")

        if not os.path.exists(excel_path):
            raise RuntimeError("LibreOffice conversion failed")

    # ----------------------------------
    # Extract images from .xlsx
    # ----------------------------------
    if not excel_path.lower().endswith((".xlsx", ".xlsm")):
        raise ValueError("Unsupported Excel format")

    wb = load_workbook(excel_path)
    extracted_paths = []
    counter = 1

    for sheet in wb.worksheets:
        for img in getattr(sheet, "_images", []):
            data = img._data()
            ext = img.format.lower() if img.format else "png"

            img_path = os.path.join(
                output_dir,
                f"excel_image_{counter}.{ext}"
            )

            with open(img_path, "wb") as f:
                f.write(data)

            extracted_paths.append(img_path)
            counter += 1

    return extracted_paths



import base64
import json
import os
from openai import AzureOpenAI

def identify_iec61010_non_conforming_images_batch(
    image_paths,
    clauses_start=4,
    clauses_end=17
):
    """
    Batch IEC 61010 image compliance checker using Azure OpenAI SDK.
    Returns per-image verdict with non-conformance details.
    """

    client = AzureOpenAI(
        api_key=DS_AOAI_KEY,
        api_version=DS_API_VERSION,
        azure_endpoint=DS_AOAI_ENDPOINT
    )

    deployment = DS_CHAT_DEPLOY

    results = []

    for idx, image_path in enumerate(image_paths):

        # ----------------------------
        # Encode image
        # ----------------------------
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

        system_prompt = f"""
You are an IEC 61010 compliance expert.

Evaluate ONLY the provided image.
Check IEC 61010 clauses {clauses_start} to {clauses_end}.
Identify NON-CONFORMANCES only.

Rules:
- Do NOT assume compliance
- Do NOT infer hidden measurements
- If visual evidence is insufficient, return INSUFFICIENT_EVIDENCE
- Be conservative and audit-safe

Return STRICT JSON ONLY:

{{
  "image_verdict": "NON_CONFORMING | CONFORMING | INSUFFICIENT_EVIDENCE",
  "non_conforming_clauses": [
    {{
      "clause": "IEC 61010-X",
      "issue": "Clear technical reason",
      "risk": "Safety / Fire / Electric Shock / Mechanical / Thermal"
    }}
  ],
  "confidence_score": 0.0 to 1.0,
  "notes": "Optional"
}}
"""

        try:
            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=800
            )

            raw_text = response.choices[0].message.content

            try:
                parsed = json.loads(raw_text)
            except Exception:
                parsed = {
                    "image_verdict": "ERROR",
                    "raw_response": raw_text
                }

        except Exception as e:
            parsed = {
                "image_verdict": "ERROR",
                "error": str(e)
            }

        results.append({
            "image_index": idx,
            "image_path": image_path,
            "result": parsed
        })

    return results




from docx import Document
from docx.shared import Inches

def _normalize(text):
    return " ".join(text.replace("\u00a0", " ").split()).upper()

def insert_photos_before_section_6_table(
    docx_path,
    output_path,
    image_paths,
    image_width_inches=3
):
    doc = Document(docx_path)

    for table in doc.tables:
        table_text = " ".join(
            _normalize(cell.text)
            for row in table.rows
            for cell in row.cells
        )

        if "SECTION 6" in table_text or "PROJECT STATUS" in table_text:

            tbl_element = table._tbl
            parent = tbl_element.getparent()
            tbl_index = parent.index(tbl_element)

            insert_index = tbl_index

            for img_path in image_paths:
                # Paragraph with image
                img_para = doc.add_paragraph()
                img_run = img_para.add_run()
                img_run.add_picture(img_path, width=Inches(image_width_inches))
                parent.insert(insert_index, img_para._p)
                insert_index += 1

                # Blank paragraph for spacing (NEW LINE)
                spacer_para = doc.add_paragraph("")
                parent.insert(insert_index, spacer_para._p)
                insert_index += 1

            doc.save(output_path)
            return

    raise ValueError("SECTION 6 table anchor not found")



import os

def orchestrate_iec61010_image_compliance_pipeline(
    blob_file_list,
    local_download_dir,
    source_docx_name,
    output_docx_path,
    connection_string,
    container_name
):
    """
    End-to-end orchestration:
    1. Download files from blob
    2. Extract images from DOCX and XLS/XLSX into src_files
    3. Identify IEC 61010 non-conforming images
    4. Insert non-conforming images into DOCX before Section 6 table
    """

    # ---------------------------------------------------------
    # 1. Download files from blob
    # ---------------------------------------------------------
    print("⬇️ Downloading files from blob...")
    downloaded_files = download_files_from_blob(
        blob_file_list=blob_file_list,
        download_dir=local_download_dir,
        connection_string=connection_string,
        container_name=container_name
    )

    # ---------------------------------------------------------
    # 2. Extract images into src_files directory
    # ---------------------------------------------------------
    print("🖼️ Extracting images from documents into src_files...")
    extracted_images = []

    for file_path in downloaded_files:
        file_lower = file_path.lower()

        if file_lower.endswith(".docx"):
            images, count = extract_images_from_docx(file_path, output_dir=local_download_dir)
            extracted_images.extend(images)

        elif file_lower.endswith((".xls", ".xlsx")):
            images = extract_images_from_excel(file_path, output_dir=local_download_dir)
            extracted_images.extend(images)

    if not extracted_images:
        print("⚠️ No images extracted from documents.")
        return

    print("\n📂 Extracted Images:")
    for img in extracted_images:
        print(" -", os.path.abspath(img))

    # ---------------------------------------------------------
    # 3. Identify IEC 61010 non-conforming images
    # ---------------------------------------------------------
    print("\n🔍 Checking IEC 61010 compliance...")
    results = identify_iec61010_non_conforming_images_batch(extracted_images)

    non_conforming_images = []

    print("\n🚨 Non-Conforming Images:")
    for r in results:
        if r["result"]["image_verdict"] == "NON_CONFORMING":
            print("❌ NON-CONFORMING:", r["image_path"])
            non_conforming_images.append(r["image_path"])

    if not non_conforming_images:
        print("✅ No non-conforming images found.")
        return

    # ---------------------------------------------------------
    # 4. Insert non-conforming images into letter.docx
    # ---------------------------------------------------------
    print("\n📄 Inserting non-conforming images into letter...")

    try:
        insert_photos_before_section_6_table(
            docx_path=output_docx_path,
            output_path=output_docx_path,
            image_paths=non_conforming_images
        )

        print("✅ Non-conforming images inserted into letter successfully.")

    except Exception as e:
        print("⚠️ Failed to insert images into letter.")
        print(f"Reason: {e}")


# insert_photos_before_section_6_table
# orchestrate_iec61010_image_compliance_pipeline
# replace_header_keys_with_values_header
from docx import Document

def replace_header_keys_with_values_header(input_docx, output_docx, data):
    """
    Replaces specific header placeholders from page 3 onwards:
    - «AppCOMPANYNAME»
    - Intertek Report: No:
    """

    TARGET_KEYS = {"«AppCOMPANYNAME»", "Intertek Report: No:"}

    doc = Document(input_docx)

    # Build replacement map ONLY from page_number >= 3
    replacements = {}
    for page in data.get("pages", []):
        if page.get("page_number", 0) < 3:
            continue

        for item in page.get("items", []):
            placeholder = str(item.get("key", "")).strip()
            value = str(item.get("value", "")).strip()

            if placeholder in TARGET_KEYS and value:
                replacements[placeholder] = value

    # If nothing to replace, exit early
    if not replacements:
        doc.save(output_docx)
        return output_docx

    # Replace helper (UNCHANGED logic)
    def replace_in_header(header):
        for para in header.paragraphs:
            for run in para.runs:
                for old, new in replacements.items():
                    if old in run.text:
                        run.text = run.text.replace(old, new)

        for table in header.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        for run in para.runs:
                            for old, new in replacements.items():
                                if old in run.text:
                                    run.text = run.text.replace(old, new)

    # Replace in ALL section headers (important for linked headers)
    for section in doc.sections:
        replace_in_header(section.header)

    doc.save(output_docx)
    return output_docx
 


# ============================================================
# ENTRY FUNCTION
# ============================================================

def ingest_letter_pipeline(
    blob_urls,
    container_name,
    src_files_dir,
    letter_json_path,
    letter_header_json_path,
    letter_template_docx,
    output_letter_docx
):
    """
    Single entry function for full letter generation pipeline.
    """

    print("\n==============================")
    print("🚀 LETTER GENERATION PIPELINE")
    print("==============================\n")

    # -------------------------------------------------------
    # VECTOR DATABASE CONNECTION
    # -------------------------------------------------------
    

    embeddings = build_embeddings(DS_AOAI_ENDPOINT, DS_AOAI_KEY, DS_API_VERSION, DS_EMBED_DEPLOY)

    vs = build_vectorstore(
        embeddings,
        DS_COSMOS_URL,
        DS_COSMOS_KEY,
        DS_DB_NAME,
        DS_CONT_NAME
    )

    vs2 = build_vectorstore2(
        embeddings,
        DS_COSMOS_URL,
        DS_COSMOS_KEY,
        DS_DB_NAME_IMG,
        DS_CONT_NAME_IMG
    )

    retriever = vs.as_retriever(search_kwargs={"k": 5})

    llm = AzureChatOpenAI(
        azure_endpoint=DS_AOAI_ENDPOINT,
        api_key=DS_AOAI_KEY,
        openai_api_version=DS_API_VERSION,
        azure_deployment=DS_CHAT_DEPLOY,
        temperature=0.1,
    ).with_config({"response_format": "json_object"})

    



    rag_image = build_rag_image_pipeline_v5(
        retriever,
        llm,
        build_vision_message_v5,
        attach_supporting_refs_grey,
        vs
    )

    # -------------------------------------------------------
    # STEP 1 — Fill Letter JSON
    # -------------------------------------------------------

    find_and_extract_cis("src_files")
    result = process_quote_from_folder("src_files")

    fill_letter_json(
        src_dir=src_files_dir,
        letter_json_path=letter_json_path,
        output_path="letter.json"
    )

    fill_letter_json(
        src_dir=src_files_dir,
        letter_json_path=letter_header_json_path,
        output_path="letter_header.json"
    )

    update_scope_of_work_in_json("letter.json","letter.json",result)

    with open("letter.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    with open("letter_header.json", "r", encoding="utf-8") as f:
        data_header = json.load(f)

    # -------------------------------------------------------
    # STEP 2 — Build Tasks
    # -------------------------------------------------------

    tasks, item_refs = build_tasks_with_custom_prompt_letter(data)
    retriever2 = vs2.as_retriever(search_kwargs={"k": 5})
    tasks = update_tasks_with_top5_images(tasks, retriever2)

    tasks_header, item_refs_header = build_tasks_with_custom_prompt_letter(data_header)
    tasks_header = update_tasks_with_top5_images(tasks_header, retriever2)

    # -------------------------------------------------------
    # STEP 3 — Run RAG
    # -------------------------------------------------------

    results = process_tasks_with_batches_parallel_grey(
        tasks,
        item_refs,
        rag_image,
        vs,
        batch_size=150,
        cooldown_sec=15,
        max_workers=6,
        use_llm_inGrey=False,
        stats=True
    )

    results_header = process_tasks_with_batches_parallel_grey(
        tasks_header,
        item_refs_header,
        rag_image,
        vs,
        batch_size=150,
        cooldown_sec=15,
        max_workers=6,
        use_llm_inGrey=False,
        stats=True
    )

    # -------------------------------------------------------
    # STEP 4 — Update Letter DOCX
    # -------------------------------------------------------

    replace_keys_with_values_no_format_change_v2(
        input_docx=letter_template_docx,
        output_docx=output_letter_docx,
        data=data
    )

    replace_header_keys_with_values_header(
        input_docx=output_letter_docx,
        output_docx=output_letter_docx,
        data=data_header
    )

    # -------------------------------------------------------
    # STEP 5 — Extract Critical Components
    # -------------------------------------------------------

    doc_path = get_first_doc_or_docx(src_files_dir)
    docx_trf = ensure_docx(doc_path)

    # df = extract_table1a(docx_trf, src_files_dir)
    # df = format_critical_components_df(df)

    # insert_dataframe_below_anchor(
    #     input_docx=output_letter_docx,
    #     output_docx=output_letter_docx,
    #     df=df,
    #     anchor_text="Details for the following critical components or materials have not been provided as required:"
    # )
    try:
        df = extract_table1a(docx_trf)
        df = format_critical_components_df(df)

        insert_dataframe_below_anchor(
            input_docx=output_letter_docx,
            output_docx=output_letter_docx,
            df=df,
            anchor_text="Details for the following critical components or materials have not been provided as required:"
        )

        print("✅ Critical components table inserted successfully.")

    except IndexError as e:
        print("⚠️ Critical components table not found in TRF. Skipping this step.")
        print(f"Reason: {e}")

    except Exception as e:
        print("⚠️ Failed to extract critical components table. Skipping this step.")
        print(f"Reason: {e}")


    # -------------------------------------------------------
    # STEP 6 — Extract IEC 61010 Non-Conformances
    # -------------------------------------------------------

    text = read_docx_full(docx_trf)

    print("############  DOCUMENT READ    #######################################")

    print(text)

    df_9_nonpass = extract_iec61010_non_conformances_full_doc(
        document_text=text,
        deployment_name=DS_CHAT_DEPLOY
    )
    print('######'*5)
    print(df_9_nonpass)

    insert_dataframe_below_anchor(
        input_docx=output_letter_docx,
        output_docx=output_letter_docx,
        df=df_9_nonpass,
        anchor_text="The following documents were evaluated during the intrinsic safety analysis and constructional evaluation:"
    )

    # -------------------------------------------------------
    # STEP 7 — Image Compliance Pipeline (uses SAME blob_urls)
    # -------------------------------------------------------

    orchestrate_iec61010_image_compliance_pipeline(
        blob_file_list=blob_urls,   # SAME LIST
        local_download_dir=src_files_dir,
        source_docx_name=output_letter_docx,
        output_docx_path=output_letter_docx,
        connection_string=AZURE_CONN_STRING,
        container_name=container_name
    )

    # -------------------------------------------------------
    # STEP 8 — Save Outputs
    # -------------------------------------------------------

    with open("letter_output.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    with open("letter_header_output.json", "w", encoding="utf-8") as f:
        json.dump(data_header, f, indent=2, ensure_ascii=False)

    print("\n==============================")
    print("✅ LETTER GENERATION COMPLETE")
    print("==============================\n")

    return {
        "letter_json": "letter_output.json",
        "header_json": "letter_header_output.json",
        "letter_docx": output_letter_docx
    }


# ============================================================
# CLI RUNNER
# ============================================================

if __name__ == "__main__":

    # blob_urls = [
    #     # 'https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/Project%20Summary%20Report.pdf',
    #         'https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/105709135MPK-001_TRF.doc',
    #         # 'https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/105709135MPK-002_TRF.doc',
    #         # "https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/Lewco_CiS.pdf" ,
    #         # "https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/Qu-01414060-2.pdf"
    #     ]
    blob_urls =['https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/Qu-01390131-0.pdf',
    # 'https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/105709135MPK-002_TRF.doc',
    "https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/105581614MPK-001A_CR.docx",
    'https://saaffine.blob.core.windows.net/nasa-ebooks-pdfs-all/Client_Information_Sheet_-_FUS_CIS_1_.pdf']



    ingest_letter_pipeline(
        blob_urls=blob_urls,
        container_name=BLOB_CONTAINER_NAME,
        src_files_dir="src_files",
        letter_json_path="letter_old.json",
        letter_header_json_path="letter_header_old.json",
        letter_template_docx="Letter_Template.docx",
        output_letter_docx="letter.docx"# final report
    )
