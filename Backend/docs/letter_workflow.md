# `letter_gen()` Workflow Documentation

## Purpose

`letter_gen()` is the final orchestration layer responsible for:

- Running the LLM/RAG-based letter generation pipeline
- Enhancing generated content using TRF/source documents
- Injecting blob URL references for traceability
- Updating metadata such as project ID and system date
- Populating the final DOCX template
- Cleaning up temporary Cosmos vector containers

The function acts as the post-processing + finalization pipeline after ingestion and vector generation are complete.

---

# Function

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

# Parameters

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

# High-Level Workflow

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

# STEP 1 — Generate Base Letter Pipeline

## Function

```python
generate_letter_pipeline(...)
```

## Purpose

Runs the primary LLM + RAG-based letter generation workflow.

### Responsibilities

- Retrieve contextual data from vector DB
- Use text/image embeddings
- Query source documents
- Generate:
  - Letter body JSON
  - Letter header JSON
  - DOCX draft output

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

# STEP 2 — Extract Scope of Work Data

## Function

```python
process_quote_from_folder(src_files_trf)
```

## Purpose

Extract structured quotation/TRF data from source TRF documents.

### Responsibilities

- Parse quote files
- Extract:
  - Scope of work
  - Quoted items
  - Technical details
  - Services/components

---

# STEP 3 — Update Scope of Work in Letter JSON

## Function

```python
update_scope_of_work_in_json(...)
```

## Purpose

Inject extracted scope-of-work content into the generated letter JSON.

---

# STEP 4 — Add Blob/Text Support References

## Function

```python
add_text_support_with_blob_url_and_filename(...)
```

## Purpose

Enhance generated JSON with:

- Supporting blob URLs
- Source filenames
- Reference traceability

### Responsibilities

- Link generated statements to source documents
- Add audit/debug trace support
- Improve explainability of generated content

---

## Output

Updated JSON structure containing:

- Source file references
- Blob URL references
- Supporting metadata

---

# STEP 5 — Load Generated Letter JSON

## Operation

```python
with open(letter_json_path_output, "r") as f:
    data_final = json.load(f)
```

## Purpose

Load the updated/generated letter JSON into memory for enrichment.

---

# STEP 6 — Attach Blob URL References

The pipeline enhances generated content by attaching source blob URLs.

---

## 6.1 Attach Image Support URLs

### Function

```python
attach_blob_urls_to_image_support_letter(...)
```

### Purpose

Attach blob URLs for:

- Images
- Schematics
- Visual evidence

---

## 6.2 Attach Text Support URLs

### Function

```python
attach_blob_urls_to_text_support_letter(...)
```

### Purpose

Attach supporting text/document references.

---

## 6.3 Attach Table Support URLs

### Function

```python
attach_blob_urls_to_table_text_support(...)
```

### Purpose

Attach blob references to:

- Tables
- Structured technical content
- Tabular evidence

---

# STEP 7 — Update Metadata

## Function

```python
update_system_date_and_project_id(...)
```

## Purpose

Inject runtime metadata into the final output.

---

## Updates

| Metadata      | Purpose                          |
| ------------- | -------------------------------- |
| `System Date` | Generation timestamp             |
| `Project ID`  | Traceability and project mapping |

---

# STEP 8 — Save Final Updated JSON

## Operation

```python
json.dump(data_final, ...)
```

## Purpose

Persist fully enriched final JSON output.

---

# STEP 9 — Process Header JSON

## Purpose

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

# STEP 10 — Populate Final DOCX

## Function

```python
replace_keys_with_values_no_format_change_all(...)
```

## Purpose

Replace placeholders inside the DOCX template with generated values.

---

## Responsibilities

- Preserve formatting
- Preserve styles/layout
- Replace dynamic placeholders
- Generate final client-ready letter

---

## Inputs

| Input         | Purpose                 |
| ------------- | ----------------------- |
| `input_docx`  | Generated DOCX template |
| `data_final`  | Final enriched JSON     |
| `output_docx` | Final output DOCX       |

---

# STEP 11 — Cleanup Cosmos Vector Containers

After generation completes, temporary vector containers are deleted.

---

## Delete Text Vector Container

### Function

```python
delete_cosmos_container(...)
```

### Purpose

Remove temporary text embeddings/vector store.

---

## Delete Image Vector Container

### Function

```python
delete_cosmos_container(...)
```

### Purpose

Remove temporary image embeddings/vector store.

---

# Why Cleanup is Important

Benefits:

- Reduce Cosmos DB storage cost
- Prevent stale embeddings
- Avoid duplicate project vectors
- Keep ingestion isolated per project

---

# End-to-End Workflow

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
        delete_cosmos_container(
        endpoint=COSMOS_URL,
        key=COSMOS_KEY,
        database_name=DB_NAME_IMG,
        container_name=image_container
        )
