# New process for OCR extraction of images (don't run)

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from langchain_core.documents import Document
from openai import AzureOpenAI

from projects.keyvault_load import load_keyvault_secrets

load_dotenv()
load_keyvault_secrets()

AZURE_CONN_STRING = os.getenv("azure-conn-string")

DB_NAME_IMG = os.getenv("cosmos-db-image")
CONT_NAME_IMG = os.getenv("cosmos-cont-image")

CHUNK_SIZE = int(os.getenv("chunk-size"))
CHUNK_OVERLAP = int(os.getenv("chunk-overlap"))

TOP_K = int(os.getenv("lt-top-k"))
EMBED_DIM = int(os.getenv("embed-dim"))
VECTOR_PATH = os.getenv("vector-path")

BLOB_CONTAINER_NAME = os.getenv("blob-container")
CONN_STR = os.getenv("LT_conn_str")

IMAGE_EXTS = os.getenv("lt-image-exts")

AOAI_ENDPOINT = os.getenv("aoai-endpoint")
AOAI_KEY = os.getenv("aoai-key")
API_VERSION = os.getenv("api-version")

EMBED_DEPLOY = os.getenv("embed-deploy")
CHAT_DEPLOY = os.getenv("chat-deploy")

COSMOS_URL = os.getenv("cosmos-url")
COSMOS_KEY = os.getenv("cosmos-key")

COSMOS_DB = os.getenv("cosmos-db-text")
COSMOS_CONT = os.getenv("cosmos-cont-text")

DB_NAME = COSMOS_DB
CONT_NAME = COSMOS_CONT

MAX_THREADS = int(os.getenv("lt-max-threads"))
MAX_RETRIES = int(os.getenv("lt-top-k"))
INITIAL_BACKOFF = int(os.getenv("lt-initial-backoff"))

client = AzureOpenAI(
    api_key=AOAI_KEY,
    api_version=API_VERSION,
    azure_endpoint=AOAI_ENDPOINT,
)


def extract_clean_image_name(blob_url: str):
    """
    Returns the FULL relative image name:
    <pdf_file>/page_4.png   OR   <pure_image.png>
    Removes SAS tokens.
    """

    parsed = urlparse(blob_url)
    path = parsed.path  # /container/.../<whatever>
    parts = path.split("/")

    # Identify pdf folder if present
    pdf_file = None
    for part in parts:
        if part.lower().endswith(".pdf"):
            pdf_file = part
            break

    # Extract clean PNG filename without SAS
    image_filename = os.path.basename(path)  # page_4.png
    # Make FULL relative path
    if pdf_file:
        return f"{pdf_file}/{image_filename}"
    else:
        return image_filename


MAX_THREADS = 10
MAX_RETRIES = 5
INITIAL_BACKOFF = 3


def process_single_image(url, index, total, vision_deploy_name):
    """
    Single-thread processing with retry/backoff logic and progress prints.
    """
    print(f"[INFO] Processing image {index}/{total} → {url}")

    backoff = INITIAL_BACKOFF

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Validate URL
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()

            image_name = url.split("/")[-1]

            # Call Azure LLM Vision
            completion = client.chat.completions.create(
                model=vision_deploy_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": url},
                            {
                                "type": "text",
                                "text": (
                                    "Perform OCR on this image and also provide a detailed "
                                    "description. Combine both into one response."
                                ),
                            },
                        ],
                    }
                ],
                max_tokens=2048,
            )

            extracted_text = completion.choices[0].message.content.strip()
            image_name = extract_clean_image_name(url)

            print(f"[SUCCESS] Completed image {index}/{total} → {url}")

            return Document(
                page_content=extracted_text,
                metadata={
                    "image_name": image_name,
                    "blob_url": url,
                    "source_type": "image",
                },
            )

        except Exception as e:
            print(
                f"[WARN] Attempt {attempt}/{MAX_RETRIES} failed for image {index} → {url}: {e}"
            )

            if attempt == MAX_RETRIES:
                print(
                    f"[ERROR] Giving up on image {index} → {url} after {MAX_RETRIES} attempts."
                )
                return None

            print(f"[INFO] Cooling down {backoff}s before retry (image {index})...")
            time.sleep(backoff)
            backoff *= 2  # exponential backoff


def load_and_process_images(image_urls, vision_deploy_name=CHAT_DEPLOY):
    docs = []
    total = len(image_urls)

    print(f"[START] Processing {total} images with up to {MAX_THREADS} threads.\n")

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_idx = {
            executor.submit(
                process_single_image, url, idx + 1, total, vision_deploy_name
            ): idx
            for idx, url in enumerate(image_urls)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            url = image_urls[idx]

            try:
                result = future.result()
                if result is not None:
                    docs.append(result)
                else:
                    print(f"[ERROR] Image {idx + 1}/{total} → returned None")
            except Exception as e:
                print(
                    f"[FATAL] Unhandled error for image {idx + 1}/{total} → {url}: {e}"
                )

    print(f"\n[COMPLETE] Finished processing {total} images.\n")
    return docs
