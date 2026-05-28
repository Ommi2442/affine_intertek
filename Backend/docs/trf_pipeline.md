# Ingestion Pipeline — `ingest_files_from_blob_urls_create_embeddings`

**Call site:** `Backend/projects/trf_processor.py`  
**Definition:** `Backend/utility/embeddings.py`

---

```
ingest_files_from_blob_urls_create_embeddings
│
├─ get_or_create_vector_container_serverless
│     Cosmos DB vector container setup (serverless-safe)
│     Creates container only if missing — no throughput set
│
├─ process_blob_urls_2
│     Download & convert blobs from Azure Blob Storage
│     ├─ Download blob files to local src_files/ directory
│     ├─ Convert Office/MSG/EML files → PDF or extracted text
│     └─ Collect raw image URLs (PNG/JPG) into image_urls_raw
│
├─ extract_cis
│     CIS (Client Information Sheet) form detection & extraction
│     └─ process_pdfs
│           Editable PDF handler (≤10 pages gate)
│           ├─ is_editable_form_pdf
│           │     Detect editable PDFs via PyPDF2
│           │     ├─ _has_freetext_annotations   ← /Annots → /FreeText check
│           │     ├─ AcroForm /Fields check
│           │     └─ XFA form check
│           │
│           ├─ save_pixmaps_to_images
│           │     Render each PDF page to PNG at 200 DPI via PyMuPDF
│           │
│           └─ extract_page_with_llm  ⚡ LLM
│                 Send page image to GPT-4.1 vision
│                 Extracts structured JSON (Applicant / Bill-To / Manufacturer fields)
│
├─ copy_extracted_images_to_src
│     Copy CIS page images into src_files/ so they enter the
│     standard image pipeline alongside uploaded images
│
├─ clean_extracted_texts
│     Sanitise extracted text before chunking
│     ├─ .eml / .msg  → aggressive clean (URLs, headers, disclaimers)
│     ├─ .xlsx / .csv → light whitespace normalisation only
│     └─ everything else → moderate clean
│
├─ load_and_split_pdfs_text
│     Load non-editable PDFs + extracted texts → chunk
│     ├─ PyPDFLoader
│     │     Extract text page-by-page; attach source_file / page / citation metadata
│     │
│     ├─ extract_relevant_pdf_page_images  [if enable-cad-schematics=true]
│     │     Identify PDF pages containing CAD / schematic diagrams
│     │     Heuristics: raster_area > 750K px² · vector_ops > 150
│     │                 text_len < 30 · blocks > 30 with text < 150
│     │                 filename keywords: schematic, cad, drawing, wiring
│     │     Matching pages rendered to PNG → image_page_metadata
│     │
│     └─ RecursiveCharacterTextSplitter
│           chunk_size=1000 · chunk_overlap=150
│           separators: \n\n · \n · '. ' · ' '
│
├─ append_cis_images_to_image_metadata
│     Merge CIS extracted page images into image_page_metadata
│     so they follow the same upload → OCR → embed path
│
├─ clear_cosmos_container  (TEXT DB)
│     Delete all existing vector documents from the text container
│     Hard reset — ensures store reflects latest upload set
│
├─ build_vectorstore_text
│     AzureCosmosDBNoSqlVectorSearch wrapper
│     embedding: AzureOpenAIEmbeddings (1536-dim float32, cosine, quantizedFlat)
│     fields: text · vector · metadata
│
├─ add_ids_to_chunks
│     Assign UUID to each text chunk (required by Cosmos partition key /id)
│
├─ ingest_to_cosmos_parallel  (TEXT)
│     Parallel text ingestion — batch=10 · workers=10
│     Calls vectorstore.add_documents() → embeds + writes to Cosmos
│
├─ upload_pdf_images_and_append_urls
│     Upload extracted page images to Azure Blob Storage (8 workers)
│     Blob path: Documents/{project_id}/pdf_images/{pdf_name}/page_N.png
│     Appends {url, image_file, pdf_file, page} to image_urls list
│
├─ load_and_process_images
│     OCR + image description pipeline (parallel, 10 threads)
│     └─ process_single_image  [per image, up to 5 retries w/ exponential backoff]
│           ├─ Validate URL (HTTP GET)
│           └─ image_desc_agent  ⚡ LLM
│                 Agent routes to GPT-4.1 vision via function-calling
│                 Performs OCR + detailed description in one pass
│                 Returns normalised LangChain Document
│
├─ clear_cosmos_container  (IMAGE DB)
│     Delete all existing vector documents from the image container
│
├─ build_vectorstore_image
│     Same config as text store, targeting cosmos-db-image container
│
├─ add_ids_to_chunks
│     UUID assignment for image documents
│
├─ ingest_to_cosmos_parallel  (IMAGE)
│     Parallel image document ingestion — batch=10 · workers=10
│
└─ Return summary dict
      {project_id, image_urls, pdf_paths, chunks_count,
       downloaded_pdfs, converted_pdfs, image_page_metadata}
```

---

## Summarised flow

```
Blob URLs  (PDF / DOC / Image)
            ↓
Cosmos Vector Container Setup
            ↓
Blob Download & Normalisation
            ↓
CIS Form Detection & Extraction  ⚡ GPT-4.1 vision
            ↓
Text Cleaning
            ↓
PDF Text Extraction + CAD/Schematic Image Identification
            ↓
Text Chunking  (RecursiveCharacterTextSplitter)
            ↓
Image Consolidation  (CAD pages + CIS pages + raw uploads)
            ↓
Vector Reset — wipe text Cosmos container
            ↓
Text Embedding & Ingestion  → Cosmos (text DB)
            ↓
Image Upload → Azure Blob Storage
            ↓
Image OCR & Description  ⚡ GPT-4.1 vision  (parallel)
            ↓
Vector Reset — wipe image Cosmos container
            ↓
Image Embedding & Ingestion  → Cosmos (image DB)
            ↓
Return ingestion summary
```

---

## Key constants

| Constant          | Value     | Purpose                                 |
| ----------------- | --------- | --------------------------------------- |
| `CHUNK_SIZE`      | 1 000     | Max chars per text chunk                |
| `CHUNK_OVERLAP`   | 150       | Overlap between adjacent chunks         |
| `EMBED_DIM`       | 1 536     | Embedding vector dimensions             |
| `VECTOR_PATH`     | `/vector` | Cosmos DB vector field path             |
| `TOP_K`           | 5         | Similarity search neighbours            |
| `MAX_THREADS`     | 10        | OCR parallelism                         |
| `MAX_RETRIES`     | 5         | Per-image retry limit                   |
| `INITIAL_BACKOFF` | 3 s       | First retry wait (doubles each attempt) |
| Max CIS pages     | 10        | Editable PDFs above this skip CIS path  |

---

> ⚡ **LLM calls** occur at two points:
> 1. **CIS extraction** — `extract_page_with_llm` → GPT-4.1 vision, structured JSON output
> 2. **Image OCR/description** — `image_desc_agent` → GPT-4.1 vision, free-text + OCR combined
