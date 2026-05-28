from typing import Any

TRF_STAGES = [
    "GATHER_PROJECT_INFO",
    "DOWNLOAD_BLOB_FILES",
    "CREATE_CHUNKS",
    "EXTRACT_IMAGE_INFO",
    "CREATE_EMBEDDINGS",
    "BUILD_TASKS",
    "ENRICH_TASKS_WITH_IMAGES",
    "FETCH_LLM_RESPONSES",
    "APPLY_POST_PROCESSING",
    "UPDATE_REPORT",
    "UPDATE_FORMAT",
    "FINALIZE_REPORT",
]


def get_trf_message(stage: str, **kwargs: Any) -> str:
    """
    Returns the user-facing progress message for a given TRF stage.
    """
    messages = {
        "GATHER_PROJECT_INFO": "gathering project information",
        "DOWNLOAD_BLOB_FILES": "downloading blob files",
        "CREATE_CHUNKS": "creating chunks",
        "EXTRACT_IMAGE_INFO": "extracting info from images",
        "CREATE_EMBEDDINGS": "creating embeddings",
        "BUILD_TASKS": "building tasks",
        "ENRICH_TASKS_WITH_IMAGES": "enriching tasks with images",
        "FETCH_LLM_RESPONSES": f"fetching response from llm - ({kwargs.get('processed', 0)} of {kwargs.get('total', 0)})",
        "APPLY_POST_PROCESSING": "applying post processing",
        "UPDATE_REPORT": "updating report",
        "UPDATE_FORMAT": "updating format",
        "FINALIZE_REPORT": "finalizing report",
    }
    return messages.get(stage, "")


CDR_STAGES = [
    "INITIALIZE_WORKFLOW",
    "PREPARE_INPUT_DOCUMENTS",
    "RETRIEVE_SOURCE_FILES",
    "PROCESS_TRF_DOCUMENTS",
    "EXTRACT_EMBEDDED_IMAGES",
    "PARSE_CIS_INFORMATION",
    "STRUCTURE_EXTRACTED_CONTENT",
    "CREATE_VECTOR_STORE",
    "INDEX_SEARCHABLE_CONTENT",
    "BUILD_REFERENCE_MAPPINGS",
    "GENERATE_PRODUCT_DESCRIPTIONS",
    "IDENTIFY_KEY_FEATURES",
    "ORGANIZE_GENERATED_ASSETS",
    "GENERATE_PHOTOS_SHEET",
    "GENERATE_CRITICAL_COMPONENTS_SHEET",
    "RUN_FINAL_VALIDATIONS",
    "EXPORT_FINAL_WORKBOOK",
]


def get_cdr_message(stage: str, **kwargs: Any) -> str:
    """
    Returns the user-facing progress message for a given CDR stage.
    """
    messages = {
        "INITIALIZE_WORKFLOW": "initializing workflow",
        "PREPARE_INPUT_DOCUMENTS": "preparing input documents",
        "RETRIEVE_SOURCE_FILES": "retrieving source files",
        "PROCESS_TRF_DOCUMENTS": "processing trf documents",
        "EXTRACT_EMBEDDED_IMAGES": "extracting embedded images",
        "PARSE_CIS_INFORMATION": "parsing cis information",
        "STRUCTURE_EXTRACTED_CONTENT": "structuring extracted content",
        "CREATE_VECTOR_STORE": "creating vector store",
        "INDEX_SEARCHABLE_CONTENT": "indexing searchable content",
        "BUILD_REFERENCE_MAPPINGS": "building reference mappings",
        "GENERATE_PRODUCT_DESCRIPTIONS": "generating product descriptions",
        "IDENTIFY_KEY_FEATURES": "identifying key features",
        "ORGANIZE_GENERATED_ASSETS": "organizing generated assets",
        "GENERATE_PHOTOS_SHEET": "generating photos sheet",
        "GENERATE_CRITICAL_COMPONENTS_SHEET": "generating critical components sheet",
        "RUN_FINAL_VALIDATIONS": "running final validations",
        "EXPORT_FINAL_WORKBOOK": "exporting final workbook",
    }
    return messages.get(stage, "")


LETTER_STAGES = [
    "INITIALIZE_LETTER_PIPELINE",
    "LOAD_TEMPLATE",
    "FETCH_PROJECT_DETAILS",
    "LOAD_TRF_DATA",
    "EXTRACT_REPORT_SUMMARY",
    "GENERATE_LETTER_CONTENT",
    "FORMAT_LETTER_CONTENT",
    "INSERT_DYNAMIC_FIELDS",
    "APPLY_BRANDING",
    "VALIDATE_LETTER_CONTENT",
    "GENERATE_PDF",
    "SAVE_FINAL_LETTER",
]


def get_letter_message(stage: str, **kwargs: Any) -> str:
    """
    Returns the user-facing progress message for a given Letter stage.
    """
    messages = {
        "INITIALIZE_LETTER_PIPELINE": "initializing letter pipeline",
        "LOAD_TEMPLATE": "loading letter template",
        "FETCH_PROJECT_DETAILS": "fetching project details",
        "LOAD_TRF_DATA": "loading trf data",
        "EXTRACT_REPORT_SUMMARY": "extracting report summary",
        "GENERATE_LETTER_CONTENT": "generating letter content",
        "FORMAT_LETTER_CONTENT": "formatting letter content",
        "INSERT_DYNAMIC_FIELDS": "inserting dynamic fields",
        "APPLY_BRANDING": "applying branding",
        "VALIDATE_LETTER_CONTENT": "validating letter content",
        "GENERATE_PDF": "generating pdf",
        "SAVE_FINAL_LETTER": "saving final letter",
    }
    return messages.get(stage, "")
