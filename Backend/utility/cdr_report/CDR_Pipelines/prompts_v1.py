from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json

ref_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an assistant that extracts Applicant and Manufacturer details for Intertek TRF/CDR drafting.
Use ONLY the provided context. Do NOT guess or use external knowledge.

Extract the Applicant and ALL Manufacturers in STRICT JSON with EXACTLY this schema:

{{
  "applicant": {{
    "name": string | null,
    "address": string | null,
    "country": string | null,
    "contacts": [
      {{
        "role": "primary" | "secondary" | "other",
        "name": string | null,
        "phone": string | null,
        "fax": string | null,
        "email": string | null
      }}
    ],
    "phone": string | null,
    "fax": string | null,
    "email": string | null
  }},
  "manufacturers": [
    {{
      "label": string,         
      "name": string | null,
      "address": string | null,
      "country": string | null,
      "contacts": [
        {{
          "role": "primary" | "secondary" | "other",
          "name": string | null,
          "phone": string | null,
          "fax": string | null,
          "email": string | null
        }}
      ],
      "phone": string | null,
      "fax": string | null,
      "email": string | null
    }}
  ]
}}

Rules:
- If a field is missing, set it to null. For missing lists, return [].
- Output ONLY the JSON object. Do NOT add extra keys or any text.
- Prefer CIS/Client_Information_Sheet if present, but still work if CIS is missing (use TRF/emails/POs/etc.).
- Address should be a single string (street + city/state/postal if present).
- Country must match the text shown in context exactly, else null.
- Contacts:
  - Create a contact entry ONLY if you can find at least one of: name, email, phone, fax.
  - Map role based on explicit labels in context:
      * "Primary" / "Primary Contact" => role="primary"
      * "Secondary" / "Alternate" / "Alternate Contact" => role="secondary"
      * otherwise => role="other"
  - If multiple contacts exist but no labels, do NOT assume primary/secondary; use role="other".
- Do NOT mix Applicant and Manufacturer info. If ambiguous, set to null.
""",
        ),
        (
            "human",
            "Context:\n{context}\n\nQuestion: {question}",
        ),
    ]
)


score_prompt = ChatPromptTemplate.from_messages([
("system", """
You are a scoring assistant.
Given:
1) the same context used for extraction
2) the extracted JSON

Return ONLY JSON in this exact shape:

{{
  "confidence": {{
    "applicant": {{
      "name": 0,
      "address": 0,
      "country": 0,
      "contacts": 0,
      "phone": 0,
      "fax": 0,
      "email": 0
    }},
    "manufacturers": [
      {{
        "label": "",
        "name": 0,
        "address": 0,
        "country": 0,
        "contacts": 0,
        "phone": 0,
        "fax": 0,
        "email": 0
      }}
    ]
  }}
}}

Rules:
- Score each field 0-100 (INTEGER) based ONLY on how directly it is supported by the context.
- 0 = not supported at all, 100 = explicitly supported and unambiguous.
- Do NOT change extracted_json; only score it.
- Output ONLY the JSON object.
"""),
("human", "Context:\n{context}\n\nExtracted JSON:\n{extracted_json}")
])






spacing_instruction = """
Fill spacing values ONLY if they are visible in the text evidence or can be clearly read from the images.
If a specific dimension is not visible in either text or images, set that field to "unknown".
Also generate one concise CDR-style sentence summarizing the spacing.
""".strip()

spacing_template = """
Spacing - In primary circuits, ___ mm minimum spacing are maintained through air and over surfaces
of insulating material between current-carrying parts of opposite polarity and ___ mm minimum between
such current-carrying parts and dead-metal parts or low voltage isolated circuits. Refer to Illustration ___
for areas to verify.
""".strip()

# This schema is what the model MUST follow (keys + nesting)
spacing_json_schema = """
{
  "section_name": "Spacing",
  "source_used": "text | images | both",
  "filled_text": "Single CDR-style sentence with placeholders replaced by actual values or '__'.",
  "Spacing": {
    "In primary circuits": {
      "minimum_spacing_through_air": "number in mm as string (e.g. '3.0') or '__'",
      "minimum_spacing_over_surfaces_of_insulating_material_between_current_carrying_parts_of_opposite_polarity": "number in mm as string or '__'",
      "minimum_spacing_between_current_carrying_parts_and_dead_metal_parts_or_low_voltage_isolated_circuits": "number in mm as string or '__'"
    },
    "Refer_to_Illustration": "e.g. 'Illustration 3-2' or 'unknown'"
  }
}
""".strip()

mechanical_instruction = """
If mounting hardware (lockwashers, starwashers, brackets, etc.) is visible in the images or clearly
described in the text, keep the full statement (or adjust wording to match actual hardware seen).

If there is clear evidence that components are NOT mechanically secured (i.e., they can shift or rotate),
state that explicitly.

If this topic is not applicable to this product, or there is no evidence at all (text or images),
set both 'filled_text' and 'mechanical_assembly_status' to "Null" and explain why in 'reason'.
""".strip()

mechanical_template = """
Mechanical Assembly - Components such as switches, fuseholders, connectors, wiring terminals 
and display lamps are mounted and prevented from shifting or rotating by the use of lockwashers, 
starwashers, or other mounting format that prevents turning of the component.
<Remove if this is not applicable to this report>
""".strip()

# JSON schema for this section
mechanical_json_schema = """
{
  "section_name": "Mechanical Assembly",
  "source_used": "text | images | both | none",
  "applicable": "true or false",
  "filled_text": "If applicable: final CDR-style sentence based on the template and evidence. If not applicable: 'Null'.",
  "mechanical_assembly_status": "If applicable: a concise status sentence (may be same as filled_text). If not applicable: 'Null'.",
  "reason": "Short explanation of how you arrived at the status, e.g. which images/pages showed mounting hardware or why it is 'Null'."
}
""".strip()

corrosion_instruction = """
Use both the text evidence and all images to determine whether ferrous metal parts
are protected against corrosion.

- If ferrous metal parts appear painted, plated, galvanized, or otherwise coated,
  keep the statement (adjust wording if needed to match what is actually observed).
- If there are clearly unprotected ferrous parts that are susceptible to corrosion,
  state that explicitly.
- If this topic is not applicable to this product (no ferrous parts, or not evaluable),
  set both 'filled_text' and 'corrosion_protection_status' to "N/A" and explain why in 'reason'.
""".strip()

corrosion_template = """
Corrosion Protection - All ferrous metal parts are protected against corrosion by painting,
plating or the equivalent. <Remove if this is not applicable to this report>
""".strip()

# JSON schema for this section
corrosion_json_schema = """
{
  "section_name": "Corrosion Protection",
  "source_used": "text | images | both | none",
  "applicable": "true or false",
  "filled_text": "If applicable: final CDR-style sentence based on the template and evidence. If not applicable: 'N/A'.",
  "corrosion_protection_status": "If applicable: concise status (e.g. 'All ferrous parts painted/plated.') or similar. If not applicable: 'N/A'.",
  "reason": "Short explanation of how you arrived at the status, including which images/pages showed coatings or why it is 'N/A'."
}
""".strip()
access_instruction = """
Use both the text evidence and all images to evaluate accessibility of primary live parts.

1) First decide if primary live parts exist in the product.
   - If there are no primary live parts, set:
       - 'applicable' = false
       - 'primary_live_parts_exist' = false
       - 'filled_text' = "N/A"
       - 'accessibility_status' = "N/A"
       - and explain why in 'reason'.

2) If primary live parts DO exist:
   - Determine whether the enclosure for these parts is:
       - metal,
       - non-metallic,
       - mixed (combination), or
       - unknown (if you truly cannot tell from the evidence).
   - Adjust the template sentence to use the correct enclosure type.
   - State clearly whether uninsulated live parts are fully housed with no openings
     other than those allowed in the standard.

Do NOT invent details that are not supported by text or images.
If a detail cannot be determined, use 'unknown' (not '___').
""".strip()

access_template = """
Accessibility of Live Parts - All uninsulated live parts in primary circuitry are housed 
within a <metal or non-metallic> enclosure constructed with no openings other than those 
specifically described in Sections 4 and 5. 
<Remove if this product has no primary live parts>
""".strip()

access_json_schema = """
{
  "section_name": "Accessibility of Live Parts",
  "source_used": "text | images | both | none",
  "applicable": "true or false",
  "primary_live_parts_exist": "true or false",
  "enclosure_type": "one of: 'metal', 'non-metallic', 'mixed', 'unknown'",
  "filled_text": "If applicable: final CDR-style sentence based on the template and evidence, with <metal or non-metallic> resolved. If not applicable: 'N/A'.",
  "accessibility_status": "Short status summary, e.g. 'All primary live parts housed in metal enclosure with no accessible openings.' or 'N/A'.",
  "reason": "Short explanation of how you arrived at these conclusions, including which images/pages were used or why it is 'N/A' or 'unknown'."
}
""".strip()
grounding_instruction = """
You are filling ONLY the GROUNDING section of a Construction Data Report (CDR).

You must produce ONE JSON object that follows grounding_json_schema.
The key field is `filled_text`, which MUST follow one of the two fixed patterns below.

--------------------------------------------------
TARGET SENTENCE PATTERNS (NO EXTRA SENTENCES)
--------------------------------------------------

A) If the product is **NOT grounded** (grounded = false)

filled_text MUST be exactly:

  "Grounding – This product is not provided with a means of grounding as it is
   not required to be grounded since <reason_text>"

Rules for this branch:
- `reason_text` is the ONLY free part of the sentence.
- `reason_text` MUST start directly with the reason, WITHOUT repeating
  “not required to be grounded since”.
- Example valid reason_text values:
    • "the device is battery operated."
    • "it is Class III equipment powered from an external Class I power supply providing only a SELV output; no protective earth conductor enters the device and accessible metal parts are separated from hazardous live parts by reinforced insulation."
- Choose `case` from:
    • "none_class_II"
    • "none_class_III"
    • "none_other"
- In `grounding_path`, briefly describe how accessible metal is separated from hazardous live parts (e.g. reinforced insulation, SELV, etc.).

B) If the product **IS grounded** (grounded = true)

filled_text MUST be exactly:

  "Grounding – All exposed dead-metal parts and all dead-metal parts within
   the enclosure that are exposed are connected to <grounding_path>"

Rules for this branch:
- `grounding_path` MUST begin as follows depending on `case`:
    • case = "grounded_via_psu_pe":
        grounding_path starts with "the grounding lead of the power supply cord"
    • case = "grounded_direct_pe_terminal":
        grounding_path starts with "the equipment grounding terminal"
    • case = "grounded_other":
        grounding_path starts with some other short phrase that accurately
          describes how the parts are bonded (e.g. "a protective earth stud on
          the chassis via a green/yellow conductor").
- After that opening phrase, you may add brief construction detail
  (e.g. “… via a green/yellow PE conductor bonded to the chassis.”).

--------------------------------------------------
GENERAL STYLE / SAFETY RULES
--------------------------------------------------

- NEVER mention any standard name or clause (no “IEC 61010-1”, “UL”, etc.).
- Use neutral, technical, third-person style.
- Do NOT add any extra sentences before or after the required pattern.
- Decide grounded vs not grounded based ONLY on construction:
  presence of PE terminal, PE in mains cord, Class II / III, SELV, etc.

--------------------------------------------------
EVIDENCE FIELDS
--------------------------------------------------

You MUST also populate:
- `source_used`: "text", "images", or "both"
- `text_evidence`: short quotes or paraphrases that support your decision.
- `image_evidence`: list of objects with:
    • file_name  – original image file name
    • blob_url   – full blob URL (not just the file name)
    • comment    – what in the image supports your conclusion

Prefer "both" when images clearly show the PE / no-PE situation.

OUTPUT
- Return ONLY a JSON object that matches grounding_json_schema.
- Do NOT include explanations outside the JSON.
"""
grounding_template = """
{% if not grounded %}
Grounding – This product is not provided with a means of grounding as it is not required to be grounded since {{ reason_text }}
{% else %}
Grounding – All exposed dead-metal parts and all dead-metal parts within the enclosure that are exposed are connected to {{ grounding_path }}
{% endif %}
""".strip()
grounding_json_schema = {
    "name": "grounding_section",
    "description": "Structured output for the Grounding section of the CDR.",
    "type": "object",
    "properties": {
        "filled_text": {
            "type": "string",
            "description": (
                "Final Grounding paragraph. "
                "MUST exactly follow one of the two target patterns described "
                "in the instructions."
            )
        },
        "grounded": {
            "type": "boolean",
            "description": (
                "True if the product itself has a protective earth connection; "
                "false if there is no means of grounding (Class II/III, SELV, etc.)."
            )
        },
        "case": {
            "type": "string",
            "description": "Label for the construction case chosen for this product.",
            "enum": [
                "none_class_II",              # double-insulated / Class II, no PE
                "none_class_III",             # Class III / SELV/PELV powered, no PE
                "none_other",                 # ungrounded for any other reason
                "grounded_via_psu_pe",        # bonded to PE conductor of power cord
                "grounded_direct_pe_terminal",# bonded to dedicated PE terminal
                "grounded_other"              # any other grounding arrangement
            ]
        },
        "grounding_path": {
            "type": "string",
            "description": (
                "For grounded cases: phrase that begins with the correct opening, "
                "e.g. 'the grounding lead of the power supply cord', "
                "'the equipment grounding terminal', etc., optionally followed by "
                "brief construction detail. For ungrounded cases, describe how "
                "metal parts are kept safe (e.g. SELV, reinforced insulation)."
            )
        },
        "reason_text": {
            "type": "string",
            "description": (
                "ONLY the reason part that comes after 'since' in the non-grounded "
                "pattern, e.g. 'the device is battery operated.' "
                "Do NOT repeat the fixed phrase 'not required to be grounded since'."
            )
        },
        "source_used": {
            "type": "string",
            "description": "Which evidence types were used.",
            "enum": ["text", "images", "both"]
        },
        "text_evidence": {
            "type": "array",
            "description": (
                "Short supporting snippets or paraphrases from TRF / documentation."
            ),
            "items": {"type": "string"}
        },
        "image_evidence": {
            "type": "array",
            "description": (
                "Images that clearly support the grounding decision "
                "(e.g. external PSU, PE terminal, or absence of PE)."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "file_name": {
                        "type": "string",
                        "description": "Original image file name, e.g. 'IMG_4667.jpg'."
                    },
                    "blob_url": {
                        "type": "string",
                        "description": "Full blob URL for the image."
                    },
                    "comment": {
                        "type": "string",
                        "description": (
                            "Very short description of what in the image supports "
                            "the conclusion."
                        )
                    }
                },
                "required": ["file_name", "blob_url"]
            }
        }
    },
    "required": [
        "filled_text",
        "grounded",
        "case",
        "grounding_path",
        "reason_text",
        "source_used",
        "text_evidence",
        "image_evidence"
    ]
}
polarized_instruction = """
Use text + images to determine whether the product is provided with a polarized power supply connection.

Rules:
1) If there IS a polarized power connection and the evidence supports the entire statement:
   - Set 'polarized' = true.
   - For 'filled_text', keep the main statement EXACT as in the template (do not change wording),
     but you may append an additional sentence describing specific construction details
     (e.g., keyed connector shape, blade size difference, keyed IEC inlet) if clearly visible in evidence.

2) If the product does NOT have a polarized connection:
   - Set 'polarized' = false.
   - Set 'filled_text' = "Polarized Connection-Null".
   - Explain briefly in 'reason'.

3) If you cannot determine from the evidence:
   - Set 'polarized' = "unknown".
   - Set 'filled_text' = "Polarized Connection-Null".
   - Explain uncertainty in 'reason'.

Do NOT partially rewrite or paraphrase the core template text.
Either use it verbatim (plus optional extra sentence) or return 'Null' as described.
""".strip()

polarized_template = """
Polarized Connection - This product is provided with a polarized power supply connection. 
All single pole switches and fuses are connected only to the ungrounded supply circuit conductor. 
(You must include specific construction details used by the manufacturer to maintain the polarity.)
""".strip()

polarized_json_schema = """
{
  "section_name": "Polarized Connection",
  "source_used": "text | images | both | none",
  "polarized": "true | false | unknown",
  "filled_text": "If polarized = true: the EXACT template text plus optionally one extra sentence with construction details. If polarized = false or unknown: 'Null'.",
  "reason": "Short explanation based on evidence: how you concluded polarized vs not polarized vs unknown, and any details about construction if known."
}
""".strip()
internal_wiring_instruction = """
Use both the text evidence and all images to describe internal wiring routing and protection.

1) For routing and protective measures:
   - Describe only what is clearly visible or explicitly stated (e.g. 'wiring routed away from sharp edges',
     'wiring tied with lacing', 'grommets used at panel penetrations').
   - If some aspects cannot be confirmed, you may omit them rather than speculate.

2) For AWG, voltage rating, and temperature rating:
   - Extract these ONLY if clearly visible on wire marking, documentation, or in the text evidence.
   - If visible:
       - 'awg_min' → smallest AWG actually seen (e.g. "18")
       - 'voltage_rating' → e.g. "300V"
       - 'temperature_rating' → e.g. "105°C"
   - If NOT visible:
       - Keep placeholders EXACTLY as:
           awg_min = "++"
           voltage_rating = "++V"
           temperature_rating = "++°C"
     Do NOT invent values.

3) For 'filled_text':
   - Start from the template sentence and:
       - Keep the generic routing/protection clauses if consistent with evidence.
       - Replace "++", "++V", "++°C" with actual values if known.
       - If unknown, leave the placeholders "++", "++V", "++°C" in place (as per your policy).

4) Do NOT hallucinate AWG, voltage, or temperature if not supported.
""".strip()

internal_wiring_template = """
Internal Wiring - Internal wiring is routed away from sharp or moving parts. 
Internal wiring leads terminating in soldered connections are made mechanically secure prior to soldering. 
Recognized Component separable connectors are acceptable. 
Wiring passing through metal walls is protected by bushings or grommets. 
All wiring is minimum ++ AWG, with a minimum rating of ++V, ++°C.
""".strip()

internal_wiring_json_schema = """
{
  "section_name": "Internal Wiring",
  "source_used": "text | images | both | none",
  "filled_text": "Template-based internal wiring statement, with '++', '++V', '++°C' replaced by actual values if known, otherwise kept as placeholders.",
  "routing_description": "Short free-text description of routing and protective measures actually observed (e.g. positioning, bundling, grommets).",
  "awg_min": "Actual minimum AWG seen (e.g. '18') or '++' if not visible.",
  "voltage_rating": "Actual voltage rating (e.g. '300V') or '++V' if not visible.",
  "temperature_rating": "Actual temperature rating (e.g. '105°C') or '++°C' if not visible.",
  "reason": "Short explanation pointing to the kind of evidence (wire legend, datasheet text, photos) used for these conclusions."
}
""".strip()
markings_template = r"""
{% if markings_status == "unknown" %}
Null
{% else %}
Markings - The product is marked on as follows: {{ markings_summary }}.

The following markings in French are required: {{ french_clause }}.{% if packaging_clause %}
{{ packaging_clause | replace("unknown", "__") }}{% endif %}
{% endif %}
""".strip()


markings_instruction = """
You are filling ONLY the MARKINGS section of a Construction Data Report (CDR).

Your job has TWO outputs:
1) A single CDR-style block of text (filled_text) that follows the EXACT sentence pattern below.
2) A small JSON object with structured fields you will use to build that text.

GENERAL RULES
- DO NOT copy the label text verbatim (no raw part numbers, serial numbers, etc.).
- Summarize what is on the label in generic terms such as:
  "Applicant's name", "brand name", "model number", "date of manufacture",
  "electrical ratings", "warning symbol", etc.

REQUIRED TEXT PATTERN (WHEN INFORMATION IS KNOWN)

If you can determine the markings and whether French markings are required,
you MUST produce filled_text in this 2–3 sentence form:

1st sentence (mandatory):
  "Markings - The product is marked on as follows: <generic summary of markings>."

    Examples of the <generic summary>:
      - "Applicant's name, brand name, model number, date of manufacture, electrical ratings."
      - "Applicant's name, model number, serial number, and electrical ratings."

2nd sentence (mandatory):
  "The following markings in French are required: <None or short description>."

    Examples:
      - "None"
      - "Equivalent safety wording for hazard warnings."

3rd sentence (optional – only if clearly supported by evidence):
  "Refer to Illustration no. <N> for remaining markings that are on the packaging."

    Only include this sentence if an illustration number for packaging markings is known.
    If you cannot see any packaging markings or illustration number, omit this sentence.

FALLBACK / UNKNOWN CASE

If you truly cannot determine the markings situation:
  - Set "markings_status" = "unknown".
  - Set filled_text EXACTLY to the literal string: "Null".

Do NOT invent markings or pretend you know them.

JSON FIELDS TO RETURN

Return a JSON object with at least these fields:
- filled_text: final CDR paragraph, exactly as above, or "Null" if unknown.
- markings_status: "present", "none_required", or "unknown".
- markings_summary: short generic list used inside the first sentence.
- french_clause: short text used after "The following markings in French are required:" 
                 (e.g. "None").
- packaging_clause: either empty string or the sentence
                    "Refer to Illustration no. <N> for remaining markings that are on the packaging."
- source_used: "text", "images", or "both".
- text_evidence: array of short snippets from documents that support your conclusion.
- image_evidence: array of {file_name, blob_url, comment} for images that show labels/markings.

ALWAYS consider both text chunks and images when they are available.
If the product clearly has no French requirements, set french_clause to "None".
"""

markings_json_schema = {
    "name": "markings_section",
    "description": "Compact structured output for the Markings section of the CDR.",
    "type": "object",
    "properties": {
        "filled_text": {
            "type": "string",
            "description": (
                "Final Markings paragraph. Either follows the required pattern:\n"
                "  'Markings - The product is marked on as follows: ...\n"
                "   The following markings in French are required: ...'\n"
                "optionally with the packaging sentence, OR is the literal string 'Null' if unknown."
            )
        },
        "markings_status": {
            "type": "string",
            "enum": ["present", "none_required", "unknown"],
            "description": "High-level status of markings on the product."
        },
        "source_used": {
            "type": "string",
            "enum": ["text", "images", "both"],
            "description": "Which evidence types were used to reach the conclusion."
        },
        "text_evidence": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Short supporting snippets from TRF / documentation."
        },
        "image_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_name": {"type": "string"},
                    "blob_url": {"type": "string"},
                    "comment":  {"type": "string"}
                },
                "required": ["file_name", "blob_url"]
            },
            "description": "Images that show the label/markings used as evidence."
        },
    },
    "required": [
        "filled_text",
        "markings_status",
        "source_used",
        "text_evidence",
        "image_evidence",
    ],
}
cautionary_template = """
{% if cautionary_status == "unknown" %}
Null
{% elif cautionary_status == "none_required" %}
Cautionary Markings - None required.
{% else %}
Cautionary Markings - The following cautionary statements are provided: {{ cautionary_summary }}{% if french_note %} {{ french_note }}{% endif %}.
{% endif %}
""".strip()
cautionary_instruction = """
You are filling ONLY the CAUTIONARY MARKINGS row of a Construction Data Report (CDR).

Outputs:
1) A short CDR-style sentence/paragraph for the Cautionary Markings row.
2) A compact JSON object with status, reasoning, and evidence.

STYLE / SAFETY RULES
- Do NOT name any standards or clauses.
- Only describe cautionary markings that are explicitly present in text or images
  (e.g. “Risk of electric shock – Do not open”, “Refer servicing to qualified personnel”, etc.).
- If you cannot see or read the text, you must treat it as UNKNOWN and not guess.
- Neutral, technical, third-person description only.

MANDATORY SENTENCE PATTERN

You must pick exactly ONE case:

(1) CAUTIONARY MARKINGS PRESENT  (cautionary_status = "present")
    Conditions:
      - You have evidence of specific cautionary wording or symbols intended as safety warnings.

    Final text MUST start with:
      "Cautionary Markings - ..."
    Recommended pattern:
      "Cautionary Markings - The following cautionary statements are provided on the product
       and/or in the accompanying documentation: <short list or summary of the main warnings>.
       {Optional French note if clearly required and present.}"

    - Summarise, do not quote very long blocks; focus on key warnings.
    - If French cautionary text is clearly present, append a short note.

(2) NONE REQUIRED / NONE PROVIDED  (cautionary_status = "none_required")
    Conditions:
      - Evidence clearly indicates no cautionary markings are required or present, OR
      - Template explicitly says to indicate "none required" when no cautionary markings exist.

    Final text MUST be:
      "Cautionary Markings - None required."

(3) CANNOT BE DETERMINED  (cautionary_status = "unknown")
    Conditions:
      - You cannot confidently determine presence or content of cautionary markings
        from the available text and images.

    Then:
      - Set cautionary_status = "unknown".
      - Set filled_text = "Null".
      - Use reason_text to explain why (e.g. "no specific cautionary markings described in TRF",
        "label images too small to read", etc.).

EVIDENCE LOGIC
- Always consider both text and images.
- If any specific cautionary text is mentioned in documentation and visible on labels/manuals,
  source_used = "both".
- text_evidence: short sentences or phrases describing or quoting the cautionary text.
- image_evidence: label/manual photos where the cautionary text appears.

Your JSON must follow cautionary_json_schema.
"""
cautionary_json_schema = {
    "name": "cautionary_markings_section",
    "description": "Structured output for the Cautionary Markings row of the CDR.",
    "type": "object",
    "properties": {
        "filled_text": {
            "type": "string",
            "description": (
                "Final narrative for Cautionary Markings starting with "
                "'Cautionary Markings - ...', or 'Null' when status is unknown, "
                "or exactly 'Cautionary Markings - None required.' when none are required."
            )
        },
        "cautionary_status": {
            "type": "string",
            "description": "Overall conclusion for cautionary markings.",
            "enum": ["present", "none_required", "unknown"]
        },
        "cautionary_summary": {
            "type": "string",
            "description": "Short summary of the key cautionary markings, if present."
        },
        "french_note": {
            "type": "string",
            "description": "Note about French versions of the cautionary markings, if applicable."
        },
        "reason_text": {
            "type": "string",
            "description": "Explanation of how the conclusion was reached."
        },
        "source_used": {
            "type": "string",
            "description": "Which evidence sources were used.",
            "enum": ["text", "images", "both"]
        },
        "text_evidence": {
            "type": "array",
            "description": "Supporting text snippets or paraphrases.",
            "items": {"type": "string"}
        },
        "image_evidence": {
            "type": "array",
            "description": "Supporting images (labels, manual pages, etc.).",
            "items": {
                "type": "object",
                "properties": {
                    "file_name": {"type": "string"},
                    "blob_url": {"type": "string"},
                    "comment": {"type": "string"}
                },
                "required": ["file_name", "blob_url"]
            }
        }
    },
    "required": [
        "filled_text",
        "cautionary_status",
        "reason_text",
        "source_used",
        "text_evidence",
        "image_evidence"
    ]
}

instructions_template = """
{% if instructions_status == "unknown" %}
Null
{% elif instructions_status == "none_required" %}
Installation, Operating and Safety Instructions - None required.
{% else %}
Installation, Operating and Safety Instructions - Instructions for installation and use of this product are provided {{ instructions_form }} and cover {{ instructions_scope }}.
{% endif %}
""".strip()
# -------------------------
# INSTALLATION / OPERATING / SAFETY INSTRUCTIONS
# -------------------------
instructions_instruction = """
You are filling ONLY the INSTALLATION, OPERATING AND SAFETY INSTRUCTIONS row of a CDR.

Outputs:
1) A concise CDR-style sentence/paragraph for this row.
2) A JSON object describing status, reasoning, and evidence.

STYLE / SAFETY RULES
- Do NOT name standards or clauses.
- Only describe instructions that are actually supplied (printed manual, leaflet, on-product sheet, PDF, etc.).
- If you cannot see or confirm the content, treat as UNKNOWN and do not speculate.
- Neutral, technical, third-person language.

MANDATORY SENTENCE PATTERN

Choose ONE of these cases:

(1) INSTRUCTIONS PROVIDED  (instructions_status = "provided")
    Conditions:
      - Evidence shows installation/operating/safety instructions are supplied with the product.

    Final text MUST start with:
      "Installation, Operating and Safety Instructions - ..."
    Recommended pattern:
      "Installation, Operating and Safety Instructions - Instructions for installation and use of this product
       are provided by the manufacturer in the form of <brief description: printed manual / leaflet / on-product sheet>.
       The instructions include <very short summary of key safety/installation topics>."

    - Keep the scope summary short (e.g. “basic installation, operating steps, maintenance precautions, and safety warnings”).
    - If clearly applicable, you may mention that French versions are provided.

(2) NONE REQUIRED / NOT PROVIDED  (instructions_status = "none_required")
    Conditions:
      - Evidence clearly indicates no installation/operating instructions are required for compliance,
        or that none are supplied and template says to indicate "none required".

    Then the final text MUST be:
      "Installation, Operating and Safety Instructions - None required."

(3) CANNOT BE DETERMINED  (instructions_status = "unknown")
    Conditions:
      - You cannot confirm whether instructions are supplied or what they contain
        from the available text and images.

    Then:
      - Set instructions_status = "unknown".
      - Set filled_text = "Null".
      - Use reason_text to explain (e.g. "no instruction manual referenced or shown in images").

EVIDENCE
- Text sources: TRF sections that describe manuals, user guides, quick start guides, etc.
- Images: photos of manuals, leaflets, or on-product instruction labels.
- source_used: "text", "images", or "both".
- text_evidence: a few short quotes/paraphrases describing the instructions.
- image_evidence: manual/leaflet photos with short comments.

Your JSON must follow instructions_json_schema.
"""
instructions_json_schema = {
    "name": "installation_operating_safety_instructions_section",
    "description": "Structured output for the Installation, Operating and Safety Instructions row.",
    "type": "object",
    "properties": {
        "filled_text": {
            "type": "string",
            "description": (
                "Final narrative for this row starting with "
                "'Installation, Operating and Safety Instructions - ...', "
                "or 'Null' when status is unknown, or exactly "
                "'Installation, Operating and Safety Instructions - None required.' when appropriate."
            )
        },
        "instructions_status": {
            "type": "string",
            "description": "Overall conclusion for instructions.",
            "enum": ["provided", "none_required", "unknown"]
        },
        "instructions_form": {
            "type": "string",
            "description": "Short description of how the instructions are provided (manual, leaflet, label, etc.), if known."
        },
        "instructions_scope": {
            "type": "string",
            "description": "Very short summary of the topics covered by the instructions, if known."
        },
        "reason_text": {
            "type": "string",
            "description": "Explanation of how the conclusion was reached."
        },
        "source_used": {
            "type": "string",
            "description": "Which evidence sources were used.",
            "enum": ["text", "images", "both"]
        },
        "text_evidence": {
            "type": "array",
            "description": "Supporting text snippets or paraphrases.",
            "items": {"type": "string"}
        },
        "image_evidence": {
            "type": "array",
            "description": "Supporting images (manual photos, etc.).",
            "items": {
                "type": "object",
                "properties": {
                    "file_name": {"type": "string"},
                    "blob_url": {"type": "string"},
                    "comment": {"type": "string"}
                },
                "required": ["file_name", "blob_url"]
            }
        }
    },
    "required": [
        "filled_text",
        "instructions_status",
        "reason_text",
        "source_used",
        "text_evidence",
        "image_evidence"
    ]
}
