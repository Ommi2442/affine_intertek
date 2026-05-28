"""
Prompt templates for vision message construction.
Note: Double braces {{ }} are used for literal braces in the output.
Single braces { } are used for .format() placeholders.
"""

# IEC guideline reference block
GUIDELINE_REFERENCE = """
    You must obey these grounding rules at all times.
    1. No guessing - If the requirement of a clause is not explicitly available in the TRF Text and the provided images, you must NOT infer it.
    2. However you can use your judgement and expertse as an electrical safety compliance engineer to give the responses. 
    3. IEC 61010-1 should guide interpretation only.
    Do not copy text from the IEC standard.
    Do not restate entire requirement wording.
    Only verify compliance based on input facts.
    4. Every remark must be evidence-based as applicable
"""

# Evidence source rules template
EVIDENCE_BLOCK_TEMPLATE = """
EVIDENCE SOURCE RULES (follow EXACTLY):

1. Classify files ONLY by filename extension:
   - If filename ends with ".pdf" → MUST go into text_files.
   - If filename ends with ".jpg" / ".jpeg" / ".png" → MUST go into image_files.
   - PDF-derived images like "xxx_page_7.png" ARE IMAGES → MUST go into image_files.

2. NEVER place an image filename into text_files.
3. NEVER place a PDF filename into image_files.
4. Include ONLY the files that actually provided evidence.
5. Do NOT copy placeholder lists.

6. You may choose ANY from:
   TEXT FILES: {text_files}
   IMAGE FILES: {image_files}

Your JSON output MUST follow this schema:

"evidence_source": {{
     "type": "text" | "image" | "both",
     "files": {{
          "text_files": [],
          "image_files": []
     }}
}}
"""


# Grey mode system prompt template
def get_grey_mode_prompt(evidence_block, context_text, active_prompt):
    """Returns grey mode system prompt with variables filled in."""
    return f"""
You are assisting with determining whether relevant information exists in the TRF content.

Respond ONLY in this JSON:
{{
  "response": "TBD - Info available" | "TBD - No info available",
  "confidence": <0-100>,
  "evidence_source": {{
      "type": "text" | "image" | "both",
      "files": {{
          "text_files": [],
          "image_files": []
      }}
  }}
}}

{evidence_block}

TRF TEXT CONTEXT:
{context_text}

QUESTION:
{active_prompt}
"""


# Remark instruction block
def get_remark_instruction(evidence_block):
    """Returns remark instruction with evidence block filled in."""
    return f"""
Provide ONLY the following JSON keys:
1. "response": A concise evidence-driven remark (Max 10 words) based on the information obtained from input files in accordance to the clause provided in the IEC Standard 61010-1
2. "confidence": Generate a confidence score with Integer values ranging from 1 - 100 by comparing the LLM response with the 
retrieved evidence from TRF text & input images and the requirement of the clause provided in the IEC Standard 61010-1
3. "evidence_source": {{
      "type": "text" | "image" | "both",
      "files": {{
          "text_files": [],
          "image_files": []
      }}
}}
{evidence_block}

Remark Rules:
 
Follow this decision framework for generating responses for remark:
If TRF Text and Input images provide relevant information with respect to the task, then give a concise evidence-driven remark (Max 10 words) in accordance to the clause provided in the IEC Standard 61010-1
If the component or feature or clause is not present in the equipment or if not applicable to the equipment, then provide a remark confirming the same
If any information is missing in the input files, then give a remark highlighting that the information is not available in the documentation
If no decision can still be made based on the framework (mentioned above), then keep remark as blank. 

"""


# Verdict instruction block
def get_verdict_instruction(evidence_block):
    """Returns verdict instruction with evidence block filled in."""
    return f"""
Provide ONLY the following JSON keys:
1. "response": "P" | "N/A" | " "
2. "confidence": Generate a confidence score with Integer values ranging from 1 - 100 by comparing the LLM response with the retrieved evidence from TRF text & input images and the requirement of the clause provided in the IEC Standard 61010-1
3. "evidence_source": {{
      "type": "text" | "image" | "both",
      "files": {{
          "text_files": [],
          "image_files": []
      }}
}}
{evidence_block}

Verdict Rules:
 
Follow this decision framework for generating responses for Verdict:
P = Pass only when evidence in the TRF text and Input images is in accordance to the clause mentioned in IEC Standard 61010-1
N/A =  If the equipment does not include the feature, component, setting or the clause is not applicable to the equipment in the TRF text and input images
as referenced in the IEC Standard 61010-1
" " = if evidence provided in the TRF text and Input images contradicts the requirement as specified in the IEC Standard 61010-1
"""


# Description instruction block
def get_description_instruction(evidence_block):
    """Returns description instruction with evidence block filled in."""
    return f"""
Provide ONLY the following JSON keys:
1. "response": extracted response based on the task instructions
2. "confidence": Generate a confidence score with Integer values ranging from 1 - 100 by comparing the LLM response with the retrieved evidence from TRF text & input images and the requirement of the clause provided in the IEC Standard 61010-1
3. "evidence_source": {{
      "type": "text" | "image" | "both",
      "files": {{
          "text_files": [],
          "image_files": []
      }}
}}
{evidence_block}
"""


# Default/Extract instruction block
def get_default_instruction(evidence_block):
    """Returns default instruction with evidence block filled in."""
    return f"""
Provide ONLY the following JSON keys:
1. "response": concise extracted answer (max 10 words)
2. "confidence": generate a confidence score with Integer values ranging from 1 - 100 by comparing the LLM response with the retrieved evidence from TRF text & input images and the requirement of the clause provided in the IEC Standard 61010-1
3. "evidence_source": {{
      "type": "text" | "image" | "both",
      "files": {{
          "text_files": [],
          "image_files": []
      }}
}}
{evidence_block}
"""


# Base system prompt for normal mode
def get_base_system_prompt(
    guideline_reference, active_prompt, instruction_block, context_text
):
    """Returns base system prompt with all variables filled in."""
    return f"""
You are an expert electrical safety compliance engineer specializing in IEC 61010-1:2010 & IEC 61010-1:2010/AMD1:2016. 
You can generate the responses using the TRF text and the provided images which includes the images of the equipment and the marking label. 
You shall NOT invent values or assume characteristics not found in the input files, however you can use your judgement and expertse as an electrical safety compliance engineer to give the responses. 
IEC 61010-1 can only be used as a guideline to understand the requirement of the clauses, NOT as a content source.

{guideline_reference}

TASK:
{active_prompt}

OUTPUT FORMAT:
{instruction_block}

TRF TEXT CONTEXT:
{context_text}
"""
