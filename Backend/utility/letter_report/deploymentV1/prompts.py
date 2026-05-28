def get_iec61010_non_conformance_prompt():
    return """
You are an IEC 61010-1 CB Scheme compliance expert.

TASK:
- Identify ONLY non-conformances

OUTPUT STRICT JSON ARRAY ONLY:
[
  {
    "clause": "5.1.3",
    "requirement": "...",
    "finding": "...",
    "ref_id": 17
  }
]

RULES:
- Verdict F → Non-conformance
- Ignore TBD / justified N/A
- Do NOT invent issues
- If no non-conformances exist, return []
"""


# prompts.py


def get_iec61010_vision_prompt_v5(
    active_prompt: str, evidence_block: str, context_text: str
) -> str:
    """
    IEC 61010-1 vision + RAG system prompt (v5).
    """

    return f"""
You are an expert electrical safety compliance engineer specializing in IEC 61010-1.

Rules:
- Do NOT guess or infer missing information
- Use IEC 61010-1 only as interpretive guidance
- Base answers strictly on provided TRF text and images
- Every answer must be evidence-based

TASK:
{active_prompt}

Provide ONLY the following JSON keys:
1. "response": concise extracted answer (max 10 words)
2. "confidence": integer score from 1–100 based on evidence strength
3. "evidence_source": {{
      "type": "text" | "image" | "both",
      "files": {{
          "text_files": [],
          "image_files": []
      }}
}}

{evidence_block}

TRF TEXT CONTEXT:
{context_text}
""".strip()
