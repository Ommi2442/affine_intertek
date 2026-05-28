# Letter Generation Pipeline Workflow

```text
Worker_main
└── letter-job (run)
    └── API Endpoint: "/run-letter"
        └── process_letter_direct()
            File: projects/letter_processor.py

            Flow:
            1. Query project container
               └── Fetch project/job metadata from Cosmos DB

            2. Validate letter generation status
               └── Check if letter_progress < 100
               └── Prevent duplicate/redundant execution

            3. update_letter_progress()
               └── Update current progress in project container
               └── Upsert latest project state to Cosmos DB

            4. run_full_ingestion()
               File:
               utility/letter_report/deploymentV1/ingest_trf_letter.py

               Responsibilities:
               └── Download/process source files
               └── Extract content/images/tables
               └── Build ingestion artifacts/vector data

            5. main()
               File:
               utility/letter_report/deploymentV1/letter_ingestor.py

               Responsibilities:
               └── Run ingestion orchestration
               └── Prepare structured data for generation
               └── Store processed chunks/metadata

            6. letter_gen()
               File:
               utility/letter_report/deploymentV1/letter_generator.py

               Responsibilities:
               └── Generate final letter content using LLM/RAG pipeline
               └── Build structured JSON response/output

            7. Save generated JSON locally
               └── Persist final output artifact
               └── Used for debugging/audit/reprocessing

            8. update_letter_progress()
               └── Mark progress completion
               └── Update final status in Cosmos DB
               └── Set letter_progress = 100
```

---

## `process_letter_direct()` Workflow

## Function Purpose

`process_letter_direct()` orchestrates the complete Letter Generation pipeline including:

* Project validation
* Progress tracking
* Document ingestion
* Vector DB preparation
* Letter generation
* Local artifact creation
* Blob/Cosmos upload
* Final status update

---

## High-Level Workflow

```text
Worker_main
└── letter-job
    └── /run-letter API
        └── process_letter_direct()
            ├── Validate Inputs
            ├── Fetch Project Metadata
            ├── Check Existing Progress
            ├── Update Initial Progress
            ├── Run Ingestion Pipeline
            ├── Run Letter Ingestor
            ├── Generate Letter
            ├── Save Outputs
            ├── Upload Artifacts
            └── Mark Completion
```

---

## `run_full_ingestion()` Workflow Documentation

## Purpose

`run_full_ingestion()` is the master ingestion orchestration pipeline responsible for:

* Downloading and processing source files
* Extracting PDF text and schematic images
* Creating vector embeddings
* Performing OCR on images
* Building text and image vector stores in Cosmos DB

The pipeline prepares all searchable RAG context required for downstream Letter/TRF generation.

---

## Function Signature

```python
run_full_ingestion(
    project_id,
    blob_urls,
    text_container,
    image_container
)
```

---

## Parameters

| Parameter         | Description                                  |
| ----------------- | -------------------------------------------- |
| `project_id`      | Unique project identifier                    |
| `blob_urls`       | List of Azure Blob document URLs             |
| `text_container`  | Cosmos vector container for text embeddings  |
| `image_container` | Cosmos vector container for image embeddings |

---

## Pipeline Steps

## 1. STEP 1 — Process Blob URLs

## Objective

Download all source files and normalize them into ingestion-ready formats.

---

## 2. Prepare Files

## 2.1 Initialize Cosmos Client

* Create Cosmos DB connection
* Initialize required clients

## 2.2 Create Text and Image Vector Containers

* Create text vector container
* Create image vector container
* Configure indexing/vector policies

## 2.3 Download and Process Blob Files

### Responsibilities

* Download files from Azure Blob Storage
* Convert `DOC/DOCX → PDF`
* Extract auxiliary text files
* Preserve local copies

## 2.4 Build PDF Path List

* Collect all normalized PDF paths
* Prepare ingestion-ready document list

## 2.5 Extract CIS/Schematic Information

* Extract CIS metadata
* Detect engineering/schematic pages

## 2.6 Remove Editable PDFs

* Remove unsupported/editable PDFs
* Keep ingestion-safe artifacts

## 2.7 Copy Extracted Images

* Copy extracted diagrams/images
* Organize into image pipeline directory

## 2.8 Clean Extracted Text

### Responsibilities (2)

* Remove noise
* Normalize formatting
* Clean malformed content

## 2.9 Merge CIS Data

* Merge extracted CIS metadata
* Prepare unified ingestion structure

---

## 3. Load & Split PDF Text

## Objective (2)

Chunk all extracted content into embedding-ready documents.

---

## Responsibilities (3)

* Load PDFs
* Extract text
* Split into chunks
* Detect CAD/schematic pages

---

## Parameters (2)

| Parameter        | Purpose                |
| ---------------- | ---------------------- |
| `CHUNK_SIZE`     | Chunk length           |
| `CHUNK_OVERLAP`  | Overlap between chunks |
| `cad_schematics` | Enable CAD extraction  |

---

## Outputs

| Output                | Description                  |
| --------------------- | ---------------------------- |
| `chunks`              | Final text chunks            |
| `image_page_metadata` | CAD/schematic image metadata |

---

## Append CIS Images

### Function

```python
append_cis_images_to_image_metadata(...)
```

### Purpose (2)

Inject extracted CIS images into the image OCR pipeline.

---

## 4. Create Text Vector Store

## 4.1 Clear Existing Container

* Delete old vector entries
* Ensure fresh ingestion

## 4.2 Build Text Vector Store

* Initialize vector store
* Configure embeddings

## 4.3 Add UUIDs to Chunks

* Generate unique identifiers
* Attach metadata

## 4.4 Parallel Text Ingestion

* Generate embeddings
* Upload chunks into Cosmos DB

---

## 5. Upload CAD/Schematic Images

## Objective (3)

Upload all extracted page images to Azure Blob Storage.

---

## 5.1 Deduplicate Images

* Remove duplicate images
* Prevent redundant OCR

## 5.2 Upload Images

* Upload extracted images to Blob Storage
* Generate public/internal URLs

## 5.3 Extract Flat URL List

* Create normalized image URL list
* Prepare OCR input payload

---

## 6. OCR Using Vision Agent Pipeline

## Responsibilities (4)

* Run Vision LLM/OCR
* Extract image text
* Interpret diagrams/schematics
* Generate image documents

---

## 7. Create Image Vector Store

## 7.1 Clear Existing Image Container

* Delete old image embeddings

## 7.2 Build Image Vector Store

* Initialize image vector DB

## 7.3 Add UUIDs to Image Docs

* Attach unique identifiers
* Preserve traceability

## 7.4 Parallel Image Ingestion

* Generate embeddings
* Upload image documents into Cosmos DB

---

## End-to-End `run_full_ingestion()` Flow

```text
Azure Blob Files
    ↓
Download + Normalize
    ↓
PDF Extraction
    ↓
CAD/Schematic Detection
    ↓
Text Cleaning
    ↓
Chunking
    ↓
Text Embeddings
    ↓
Cosmos Text Vector Store
    ↓
Image Upload
    ↓
Vision OCR Pipeline
    ↓
Image Embeddings
    ↓
Cosmos Image Vector Store
```

## Files created by process letter direct

Explains the files and structure created during the letter generation process.

| Variable                  | Path / Value                                                           | Purpose                                        |
| ------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------- |
| `BASE_DIR`                | `Path(__file__).resolve().parents[1]`                                  | Root/base directory of the project             |
| `DATA_DIR`                | `BASE_DIR / "data"`                                                    | Central data storage directory                 |
| `project_dir`             | `DATA_DIR / projectId`                                                 | Project-specific working directory             |
| `letter_json1`            | `project_dir / f"letter_body_iec_output_{projectId}.json"`             | Generated letter body JSON output              |
| `letter_json2`            | `project_dir / f"letter_header_iec_output_{projectId}.json"`           | Generated letter header JSON output            |
| `letter_docx_file`        | `project_dir / f"letter_iec_output_{projectId}.docx"`                  | Final generated DOCX letter                    |
| `letter_json_path`        | `BASE_DIR / "utility/letter_report/deploymentV1/letter.json"`          | Static/input letter body JSON template         |
| `letter_header_json_path` | `BASE_DIR / "utility/letter_report/deploymentV1/letter_header.json"`   | Static/input letter header JSON template       |
| `letter_template_docx`    | `BASE_DIR / "utility/letter_report/deploymentV1/Letter_Template.docx"` | DOCX template used for final letter generation |
| `letter_src_files`        | `BASE                                                                  |                                                |

# `main()` Ingestion Workflow Documentation

## Purpose

`main()` is the core ingestion orchestration pipeline responsible for:

- Downloading source documents from Azure Blob Storage
- Extracting and processing PDF/text content
- Creating vector embeddings for text and image OCR data
- Uploading CAD/schematic images
- Running Vision OCR using Azure OpenAI
- Building searchable text and image vector stores in Cosmos DB

The pipeline prepares all searchable RAG context required for downstream Letter/TRF generation.

---

# Function Signature

```python
def main(project_id, blob_urls, text_container, image_container):
```

---

# Parameters

| Parameter | Type | Purpose |
|---|---|---|
| `project_id` | `str` | Unique project identifier |
| `blob_urls` | `list[str]` | Azure Blob URLs containing source documents |
| `text_container` | `str` | Cosmos DB vector container for text embeddings |
| `image_container` | `str` | Cosmos DB vector container for image embeddings |

---

# High-Level Workflow

```text
main()
    │
    ├── Initialize Cosmos Client
    │
    ├── Download + Extract Blob Files
    │
    ├── Build Text Embedding Vector Store
    │
    ├── Load PDFs + Create Text Chunks
    │
    ├── Upload CAD/Schematic Images
    │
    ├── Ingest Text Chunks into Cosmos DB
    │
    ├── Build Image Embedding Vector Store
    │
    ├── Extract Image URLs
    │
    ├── Run Azure Vision OCR Pipeline
    │
    ├── Ingest OCR Chunks into Cosmos DB
    │
    └── Complete Pipeline
```

---

# STEP 1 — Initialize Cosmos Client

## Purpose

Initialize Cosmos DB connection for vector store operations.

---

## Operation

```python
cosmos_client = CosmosClient(
    COSMOS_URL,
    credential=COSMOS_KEY,
    consistency_level=ConsistencyLevel.Eventual
)
```

---

## Responsibilities

- Connect to Cosmos DB
- Configure consistency level
- Enable DB/container operations

---

# STEP 2 — Download + Extract Blob Files

## Purpose

Download source documents from Azure Blob Storage and normalize them into ingestion-ready files.

---

## Function

```python
process_blob_urls_2(...)
```

---

## Responsibilities

- Download source documents
- Extract text files
- Convert documents to PDF if required
- Preserve local copies
- Extract image metadata

---

## Inputs

| Input | Purpose |
|---|---|
| `blob_urls` | Source Azure Blob URLs |
| `AZURE_CONN_STRING` | Azure Storage connection |
| `container_blob` | Blob container name |
| `DOWNLOAD_DIR` | Local storage directory |

---

## Outputs

| Output | Description |
|---|---|
| `extracted_texts` | Extracted auxiliary text |
| `image_urls` | Extracted image metadata |
| `downloaded_pdf_paths` | Downloaded PDF files |
| `converted_pdf_paths` | Converted PDF files |

---

# STEP 3 — Create Vector DB for TEXT

## Purpose

Create the text embedding vector store used for RAG retrieval.

---

## Build Embeddings

### Function

```python
build_embeddings(...)
```

### Responsibilities

- Initialize Azure OpenAI embedding model
- Configure embedding deployment

---

## Build Vector Store

### Function

```python
build_vectorstore(...)
```

### Responsibilities

- Create Cosmos vector store
- Configure vector indexing
- Prepare text ingestion pipeline

---

# STEP 4 — Load PDFs and Create Text Chunks

## Purpose

Extract and chunk PDF content into embedding-ready documents.

---

## Function

```python
load_and_split_pdfs_text(...)
```

---

## Responsibilities

- Load PDF documents
- Extract text
- Split text into chunks
- Extract schematic metadata
- Prepare chunked documents

---

## Parameters

| Parameter | Purpose |
|---|---|
| `CHUNK_SIZE` | Chunk size for embeddings |
| `CHUNK_OVERLAP` | Overlap between chunks |
| `cad_schematics=False` | Disable CAD extraction |

---

## Outputs

| Output | Description |
|---|---|
| `chunks` | Text embedding chunks |
| `image_page_metadata` | Schematic/image metadata |

---

# STEP 5 — Upload CAD/Schematic Images

## Purpose

Upload extracted CAD/schematic images into Azure Blob Storage.

---

## Function

```python
upload_pdf_images_and_append_urls(...)
```

---

## Responsibilities

- Upload page images
- Store schematic images
- Append blob URLs
- Generate accessible image references

---

# STEP 6 — Ingest TEXT Chunks into Vector DB

## Purpose

Store text embeddings into Cosmos DB vector store.

---

## Function

```python
ingest_to_cosmos_parallel(...)
```

---

## Responsibilities

- Generate embeddings
- Batch ingestion
- Parallel uploads
- Optimize ingestion performance

---

## Parameters

| Parameter | Value |
|---|---|
| `batch_size` | `10` |
| `max_workers` | `10` |

---

# STEP 7 — Create Vector DB for IMAGE OCR

## Purpose

Initialize image OCR vector store for image-based retrieval.

---

## Build Image Embeddings

### Function

```python
build_embeddings(...)
```

---

## Build Image Vector Store

### Function

```python
build_vectorstore2(...)
```

---

## Responsibilities

- Create image embedding store
- Configure Cosmos image vectors
- Prepare OCR ingestion pipeline

---

# STEP 8 — Extract Image URLs

## Purpose

Flatten uploaded image metadata into usable URL list.

---

## Function

```python
extract_urls(...)
```

---

## Responsibilities

- Extract image links
- Normalize URL structure
- Prepare OCR inputs

---

# STEP 9 — OCR Images using Azure Vision GPT

## Purpose

Run Vision OCR pipeline on uploaded images using Azure OpenAI.

---

## Function

```python
load_and_process_images(...)
```

---

## Responsibilities

- OCR image content
- Interpret diagrams/schematics
- Extract embedded text
- Generate image documents

---

## Azure OpenAI Client

```python
AzureOpenAI(
    api_key=AOAI_KEY,
    api_version=API_VERSION,
    azure_endpoint=AOAI_ENDPOINT,
)
```

---

## OCR Pipeline Inputs

| Input | Purpose |
|---|---|
| `img_links` | Uploaded image URLs |
| `MAX_THREADS` | Parallel OCR workers |
| `MAX_RETRIES` | Retry handling |
| `INITIAL_BACKOFF` | Retry backoff |
| `CHAT_DEPLOY` | Vision GPT deployment |

---

## Output

| Output | Description |
|---|---|
| `t` | OCR-generated image documents |

---

# STEP 10 — Ingest IMAGE OCR Chunks

## Purpose

Store OCR-generated image embeddings into Cosmos DB.

---

## Function

```python
ingest_to_cosmos_parallel(...)
```

---

## Responsibilities

- Generate image embeddings
- Batch upload OCR documents
- Enable image-based RAG retrieval

---

## Parameters

| Parameter | Value |
|---|---|
| `batch_size` | `10` |
| `max_workers` | `10` |

---

# Final Pipeline Completion

## Output

```python
return True
```

---

# End-to-End Workflow

```text
Azure Blob Files
      ↓
Download Documents
      ↓
Extract PDFs/Text
      ↓
Create Text Embeddings
      ↓
Cosmos Text Vector Store
      ↓
Extract CAD/Schematic Images
      ↓
Upload Images to Blob Storage
      ↓
Azure Vision OCR Pipeline
      ↓
Create Image Embeddings
      ↓
Cosmos Image Vector Store
      ↓
RAG Context Ready
```

## `letter_gen()` Workflow Documentation

## Purpose (3)

`letter_gen()` is the final orchestration layer responsible for:

* Running the LLM/RAG-based letter generation pipeline
* Enhancing generated content using TRF/source documents
* Injecting blob URL references for traceability
* Updating metadata such as project ID and system date
* Populating the final DOCX template
* Cleaning up temporary Cosmos vector containers

The function acts as the post-processing + finalization pipeline after ingestion and vector generation are complete.

---

## Function (2)

```python
def letter_gen(
    blob_urls,
    container_name,
    src_files_dir,
    src_files_trf,
    letter_json_path,
    letter_header_json_path,
    letter_template_docx,
    output_letter_docx,
    letter_json_path_output,
    letter_header_json_path_output,
    project_Id,
    blob_urls_trf,
    text_container,
    image_container
)
```

---

## Parameters (3)

| Parameter                        | Type / Example | Purpose                                                                       |
| -------------------------------- | -------------- | ----------------------------------------------------------------------------- |
| `blob_urls`                      | `list[str]`    | Azure Blob URLs for source documents used in letter generation                |
| `container_name`                 | `str`          | Blob/Cosmos container associated with the project workflow                    |
| `src_files_dir`                  | `Path / str`   | Local directory containing downloaded source files for letter generation      |
| `src_files_trf`                  | `Path / str`   | Local directory containing TRF/quote-related source files                     |
| `letter_json_path`               | `Path / str`   | Base/template JSON file for letter body generation                            |
| `letter_header_json_path`        | `Path / str`   | Base/template JSON file for letter header generation                          |
| `letter_template_docx`           | `Path / str`   | DOCX template used to generate the final formatted letter                     |
| `output_letter_docx`             | `Path / str`   | Output path for the generated final DOCX letter                               |
| `letter_json_path_output`        | `Path / str`   | Output path for generated/enriched letter body JSON                           |
| `letter_header_json_path_output` | `Path / str`   | Output path for generated/enriched letter header JSON                         |
| `project_Id`                     | `str`          | Unique project identifier used for metadata and traceability                  |
| `blob_urls_trf`                  | `list[str]`    | Blob URLs corresponding to TRF/supporting documents used for evidence mapping |
| `text_container`                 | `str`          | Cosmos DB vector container storing text embeddings                            |
| `image_container`                | `str`          | Cosmos DB vector container storing image embeddings                           |

---

## High-Level Workflow (2)

```text
letter_gen()
    │
    ├── Generate Base Letter using RAG/LLM Pipeline
    │
    ├── Extract Scope of Work from TRF Files
    │
    ├── Update Generated Letter JSON
    │
    ├── Add Blob/Text Support References
    │
    ├── Attach Image/Text/Table Blob URLs
    │
    ├── Update Metadata
    │     ├── System Date
    │     └── Project ID
    │
    ├── Update Header JSON
    │
    ├── Populate DOCX Template
    │
    └── Cleanup Cosmos Vector Containers
```

---

## STEP 1 — Generate Base Letter Pipeline

## Function (3)

```python
generate_letter_pipeline(...)
```

## Purpose (4)

Runs the primary LLM + RAG-based letter generation workflow.

### Responsibilities (5)

* Retrieve contextual data from vector DB
* Use text/image embeddings
* Query source documents
* Generate:
  * Letter body JSON
  * Letter header JSON
  * DOCX draft output

---

## Inputs Used

| Input                     | Purpose                     |
| ------------------------- | --------------------------- |
| `blob_urls`               | Source document blob URLs   |
| `src_files_dir`           | Local source file directory |
| `letter_json_path`        | Base body JSON template     |
| `letter_header_json_path` | Base header JSON template   |
| `letter_template_docx`    | DOCX template               |
| `text_container`          | Text vector store           |
| `image_container`         | Image vector store          |

---

## STEP 2 — Extract Scope of Work Data

## Function (4)

```python
process_quote_from_folder(src_files_trf)
```

## Purpose (5)

Extract structured quotation/TRF data from source TRF documents.

### Responsibilities (6)

* Parse quote files
* Extract:
  * Scope of work
  * Quoted items
  * Technical details
  * Services/components

---

## STEP 3 — Update Scope of Work in Letter JSON

## Function (5)

```python
update_scope_of_work_in_json(...)
```

## Purpose (6)

Inject extracted scope-of-work content into the generated letter JSON.

---

## STEP 4 — Add Blob/Text Support References

## Function (6)

```python
add_text_support_with_blob_url_and_filename(...)
```

## Purpose (7)

Enhance generated JSON with:

* Supporting blob URLs
* Source filenames
* Reference traceability

### Responsibilities (7)

* Link generated statements to source documents
* Add audit/debug trace support
* Improve explainability of generated content

---

## Output

Updated JSON structure containing:

* Source file references
* Blob URL references
* Supporting metadata

---

## STEP 5 — Load Generated Letter JSON

## Operation

```python
with open(letter_json_path_output, "r") as f:
    data_final = json.load(f)
```

## Purpose (8)

Load the updated/generated letter JSON into memory for enrichment.

---

## STEP 6 — Attach Blob URL References

The pipeline enhances generated content by attaching source blob URLs.

---

## 6.1 Attach Image Support URLs

### Function (7)

```python
attach_blob_urls_to_image_support_letter(...)
```

### Purpose (9)

Attach blob URLs for:

* Images
* Schematics
* Visual evidence

---

## 6.2 Attach Text Support URLs

### Function (8)

```python
attach_blob_urls_to_text_support_letter(...)
```

### Purpose (10)

Attach supporting text/document references.

---

## 6.3 Attach Table Support URLs

### Function (9)

```python
attach_blob_urls_to_table_text_support(...)
```

### Purpose (11)

Attach blob references to:

* Tables
* Structured technical content
* Tabular evidence

---

## STEP 7 — Update Metadata

## Function (10)

```python
update_system_date_and_project_id(...)
```

## Purpose (12)

Inject runtime metadata into the final output.

---

## Updates

| Metadata      | Purpose                          |
| ------------- | -------------------------------- |
| `System Date` | Generation timestamp             |
| `Project ID`  | Traceability and project mapping |

---

## STEP 8 — Save Final Updated JSON

## Operation (2)

```python
json.dump(data_final, ...)
```

## Purpose (13)

Persist fully enriched final JSON output.

---

## STEP 9 — Process Header JSON

## Purpose (14)

Apply the same blob URL enrichment process to the header JSON.

---

## Steps

### Load Header JSON

```python
json.load(...)
```

### Attach Image URLs

```python
attach_blob_urls_to_image_support_letter(...)
```

### Attach Text URLs

```python
attach_blob_urls_to_text_support_letter(...)
```

### Save Updated Header JSON

```python
json.dump(...)
```

---

## STEP 10 — Populate Final DOCX

## Function (11)

```python
replace_keys_with_values_no_format_change_all(...)
```

## Purpose (15)

Replace placeholders inside the DOCX template with generated values.

---

## Responsibilities (8)

* Preserve formatting
* Preserve styles/layout
* Replace dynamic placeholders
* Generate final client-ready letter

---

## Inputs

| Input         | Purpose                 |
| ------------- | ----------------------- |
| `input_docx`  | Generated DOCX template |
| `data_final`  | Final enriched JSON     |
| `output_docx` | Final output DOCX       |

---

## STEP 11 — Cleanup Cosmos Vector Containers

After generation completes, temporary vector containers are deleted.

---

## Delete Text Vector Container

### Function (12)

```python
delete_cosmos_container(...)
```

### Purpose (16)

Remove temporary text embeddings/vector store.

---

## Delete Image Vector Container

### Function (13)

```python
delete_cosmos_container(...)
```

### Purpose (17)

Remove temporary image embeddings/vector store.

---

## Why Cleanup is Important

Benefits:

* Reduce Cosmos DB storage cost
* Prevent stale embeddings
* Avoid duplicate project vectors
* Keep ingestion isolated per project

---

## End-to-End Workflow

```text
Source Documents
      ↓
RAG + LLM Letter Generation
      ↓
Generate JSON + DOCX Draft
      ↓
Extract Scope of Work
      ↓
Inject Scope Data
      ↓
Attach Blob URL References
      ↓
Attach Image/Text/Table Support
      ↓
Update Metadata
      ↓
Update Header JSON
      ↓
Populate Final DOCX
      ↓
Save Final Outputs
      ↓
Delete Temporary Vector Stores
```
