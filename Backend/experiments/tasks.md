## LLM Processing Tasks Checklist

### Image & Vision Analysis

* [ ] Image understanding and caption generation — `utils.py` (`analyze_image` - line 971)
* [ ] Multimodal feature extraction — `features_agent.py` (`llm_generate_multimodal` - lines 186–187)
* [ ] Multimodal section processing — `features_agent.py` (`run_multimodal_section` - line 240)
* [ ] PDF page content extraction — `editable_processing.py` (`extract_page_with_llm` - line 239)
* [ ] PDF image processing workflow — `editable_processing.py` (`process_pdfs` - line 338)
* [ ] BOM extraction from images — `components_case_1.py` (`extract_bom_from_image` - line 351)
* [ ] Image description generation — `components_case_1.py` (`describe_image` - line 932)
* [ ] Single image processing — `components_case_2.py` (`_process_single_image` - line 243)
* [ ] Guide/document chunk analysis — `components_case_2.py` (`_process_guide_chunk` - line 348)

---

### Reference & Data Extraction

* [ ] Applicant and manufacturer extraction — `references.py` (`references_main` - line 397)
* [ ] Retrieval and reference chain execution — `references.py` (`references_main` - line 410)
* [ ] Reference validation and confidence scoring — `references.py` (`references_main` - line 423)
* [ ] Product description refinement — `description.py` (`description_main` - line 132)

---

### Classification & Decision Tasks

* [ ] Criticality classification — `components_case_1.py` (`classify_in_batches` - line 792)
* [ ] Batch classification processing — `components_case_2.py` (`classify_batch_llm` - line 626)

---

### Retry & Request Handling

* [ ] API retry and rate-limit handling — `utils.py` (`invoke_with_rate_limit_retry` - line 1220)

---

### Embedding & Search Preparation

* [ ] Text embedding generation — `utils.py` (`add_text_support_to_result_json` - line 1691)
* [ ] Search/query embedding generation — `utils.py` (`add_text_support_to_result_json` - line 1709)
* [ ] Reference embedding support — `references.py` (`references_main` - line 459)
* [ ] Text embedding creation — `components_case_1.py` (`embed_text` - line 897)

---

### Phototagging & Component Analysis

* [ ] Visible text embedding for phototagging — `components_case_1.py` (`run_phototagging` - line 1111)
* [ ] Component text embedding — `components_case_1.py` (`run_phototagging` - line 1135)

---

### Overall Processing Pipelines

* [ ] Features processing pipeline — `features_agent.py` (`run_multimodal_section` - line 240)
* [ ] PDF processing workflow — `editable_processing.py` (`process_pdfs` - line 338)
* [ ] Phototagging workflow — `components_case_1.py` (`run_phototagging` - lines 1111–1135)
* [ ] Component analysis workflow — `components_case_1.py` (`_parse_bom_with_vs` - line 495)
* [ ] Image classification workflow — `components_case_2.py` (`classify_batch_llm` - line 626)
