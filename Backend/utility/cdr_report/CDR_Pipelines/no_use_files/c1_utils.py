# utils.py


# NOTE:
# c1_utils is intentionally runtime-agnostic.
# Do NOT access configs.runtime or project_id here.
# This module must remain safe to import before init_runtime().



import re
import json
import numpy as np
import pandas as pd
from openai import AzureOpenAI
from azure.cosmos import CosmosClient, PartitionKey
import utility.cdr_report.CDR_Pipelines.configs as configs

# ==================== CLIENT INITIALIZATION ====================
openai_client = AzureOpenAI(
    api_key=configs.AZURE_OPENAI_KEY,
    azure_endpoint=configs.AZURE_OPENAI_ENDPOINT,
    api_version=configs.AZURE_OPENAI_API_VERSION
)

cosmos_client = CosmosClient(configs.COSMOS_ENDPOINT, configs.COSMOS_KEY)
cosmos_db = cosmos_client.get_database_client(configs.COSMOS_DB_NAME)
# cosmos_container = cosmos_db.create_container_if_not_exists(
#     id=configs.COSMOS_CONTAINER_NAME,
#     partition_key=PartitionKey(path=configs.PARTITION_KEY)
# )

# Alias for compatibility with original code
client = openai_client

# ==================== HELPER FUNCTIONS ====================
def safe_json_load(text):
    """
    Extracts first JSON array or object from text safely.
    Returns None if extraction fails.
    """
    if not text or not text.strip():
        return None

    # Remove markdown fences
    text = text.strip()
    text = re.sub(r"^```.*?\n", "", text)
    text = re.sub(r"\n```$", "", text)

    # Try array first
    match = re.search(r"\[\s*{.*}\s*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Try object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None

def cosine_distance(a, b):
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def clean_value(v):
    if pd.isna(v):
        return None
    return v

