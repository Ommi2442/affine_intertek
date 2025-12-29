
# spacing_instruction = """
# Fill spacing values ONLY if they are visible in the text evidence or can be clearly read from the images.
# If a specific dimension is not visible in either text or images, set that field to "unknown".
# Also generate one concise CDR-style sentence summarizing the spacing.
# """.strip()

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

From the provided image_urls, return ONLY the URLs that directly support the extracted spacing values
or the referenced Illustration. If none are relevant, return an empty list.
""".strip()

spacing_template = """
Spacing - In primary circuits, ___ mm minimum spacing are maintained through air and over surfaces
of insulating material between current-carrying parts of opposite polarity and ___ mm minimum between
such current-carrying parts and dead-metal parts or low voltage isolated circuits. Refer to Illustration ___
for areas to verify.
""".strip()
spacing_json_schema = """
{
  "section_name": "Spacing",
  "source_used": "text | images | both",
  "filled_text": "Single CDR-style sentence with placeholders replaced by actual values or '__'.",
  "relevant_image_urls": ["list of URLs (strings). Only include images that directly support extracted values or the illustration; else []"],
  "overall_confidence": "number 0.0 to 100.0",
  "field_confidence": {
    "minimum_spacing_through_air": "number 0.0 to 1.0",
    "minimum_spacing_over_surfaces_of_insulating_material_between_current_carrying_parts_of_opposite_polarity": "number 0.0 to 1.0",
    "minimum_spacing_between_current_carrying_parts_and_dead_metal_parts_or_low_voltage_isolated_circuits": "number 0.0 to 1.0",
    "Refer_to_Illustration": "number 0.0 to 1.0"
  },
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
Decide if the 'Mechanical Assembly' section is applicable to this product based ONLY on evidence.

EVIDENCE RULES:
- Use text evidence and/or images only. Do not guess.
- If mounting hardware (lockwashers, starwashers, brackets, staking, adhesive, screws, clips, etc.)
  is visible in images OR explicitly described in text, treat as evidence of mechanical securing.
- If evidence clearly shows components are NOT secured (can shift/rotate/float), state that explicitly.
- If there is no evidence at all (neither text nor images), mark as not applicable.

OUTPUT RULES:
- Return ONLY a single valid JSON object matching the schema exactly.
- If not applicable: set 'applicable' = false and set both 'filled_text' and 'mechanical_assembly_status' to "N/A".
- 'relevant_image_urls' must include ONLY the URLs that directly support your conclusion.
  If none support it, return [].

CONFIDENCE RULES:
- overall_confidence and field_confidence must be numbers between 0.0 and 100.0.
""".strip()

mechanical_template = """
Mechanical Assembly - Components such as switches, fuseholders, connectors, wiring terminals 
and display lamps are mounted and prevented from shifting or rotating by the use of lockwashers, 
starwashers, or other mounting format that prevents turning of the component.
<Remove if this is not applicable to this report>
""".strip()

mechanical_json_schema = """
{
  "section_name": "Mechanical Assembly",
  "source_used": "text | images | both | none",
  "applicable": true,
  "filled_text": "If applicable: final CDR-style sentence based on the template and evidence. If not applicable: 'N/A'.",
  "mechanical_assembly_status": "If applicable: concise status sentence (may be same as filled_text). If not applicable: 'N/A'.",
  "relevant_image_urls": [
    "URLs only. MUST be a subset of the provided image_urls. Copy-paste exactly. Do not invent/modify. If none, return []"
  ],
  "overall_confidence": 0.0,
  "reason": "Short explanation: cite what in text/images supports the conclusion (file/page if from text chunks), or say 'No evidence found'."
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
- Provide confidence score based on the evidence
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
  "overall_confidence": "number 0 to 100"
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
Also include an 'overall_confidence' score (0.0 to 100.0) based on the strength and completeness of the evidence used.
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
  "reason": "Short explanation of how you arrived at these conclusions, including which images/pages were used or why it is 'N/A' or 'unknown'.",
  "overall_confidence": "number from 0.0 to 100.0 indicating confidence based on evidence quality/coverage"
}
""".strip()


grounding_instruction = """
Fill ONLY the CDR section: GROUNDING. Return ONE JSON object matching grounding_json_schema.

filled_text MUST be EXACTLY one of these (no extra sentences):

A) If grounded=false:
"Grounding – This product is not provided with a means of grounding as it is not required to be grounded since <reason_text>"
- <reason_text> is the only free part (start directly with the reason; do NOT repeat 'not required...').
- case must be one of: none_class_II, none_class_III, none_other
- grounding_path: briefly state how accessible metal is kept safe (SELV, reinforced insulation, etc.)

B) If grounded=true:
"Grounding – All exposed dead-metal parts and all dead-metal parts within the enclosure that are exposed are connected to <grounding_path>"
- case must be one of: grounded_via_psu_pe, grounded_direct_pe_terminal, grounded_other
- grounding_path must start with:
  • grounded_via_psu_pe: "the grounding lead of the power supply cord"
  • grounded_direct_pe_terminal: "the equipment grounding terminal"
  • grounded_other: another accurate bonding phrase
- You may append brief construction detail after the required start.

Rules:
- Do NOT mention any standard/clause.
- Decide grounded vs not grounded ONLY from evidence (PE terminal/cord, Class II/III, SELV, etc.).
- Populate evidence fields: source_used (text/images/both), text_evidence[], image_evidence[{file_name, blob_url, comment}].
Return ONLY JSON.
- Provide 'overall_confidence' based on the evidence and the result
""".strip()

grounding_template = """
{% if not grounded %}
Grounding – This product is not provided with a means of grounding as it is not required to be grounded since {{ reason_text }}
{% else %}
Grounding – All exposed dead-metal parts and all dead-metal parts within the enclosure that are exposed are connected to {{ grounding_path }}
{% endif %}
""".strip()

grounding_json_schema = {
  "type": "object",
  "properties": {
    "filled_text": {"type": "string"},
    "grounded": {"type": "boolean"},
    "case": {
      "type": "string",
      "enum": [
        "none_class_II",
        "none_class_III",
        "none_other",
        "grounded_via_psu_pe",
        "grounded_direct_pe_terminal",
        "grounded_other"
      ]
    },
    "grounding_path": {"type": "string"},
    "reason_text": {"type": "string"},
    "source_used": {"type": "string", "enum": ["text", "images", "both"]},
    "text_evidence": {"type": "array", "items": {"type": "string"}},
    "image_evidence": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "file_name": {"type": "string"},
          "blob_url": {"type": "string"},
          "comment": {"type": "string"}
        },
        "required": ["file_name", "blob_url"]
      }
    },
      "overall_confidence" : "number 0 to 100"
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
   - For 'filled_text', keep the main statement EXACT as in the template (do not change wording),
     but you may append an additional sentence describing specific construction details
     (e.g., keyed connector shape, blade size difference, keyed IEC inlet) if clearly visible in evidence.

2) If the product does NOT have a polarized connection:
   - Set 'polarized' = false.
   - Set 'filled_text' = "N/A".
   - Explain briefly in 'reason'.

3) If you cannot determine from the evidence:
   - Set 'polarized' = "unknown".
   - Set 'filled_text' = "N/A".
   - Explain uncertainty in 'reason'.

Do NOT partially rewrite or paraphrase the core template text.
Either use it verbatim (plus optional extra sentence) or return 'N/A' as described.
provide an 'overall_confidence' score based on the text and image evidence
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
  "filled_text": "If polarized = true: the EXACT template text plus optionally one extra sentence with construction details. If polarized = false or unknown: 'N/A'.",
  "reason": "Short explanation based on evidence: how you concluded polarized vs not polarized vs unknown, and any details about construction if known.",
  "overall_confidence" : number 0 to 100
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
       - 'awg_min' 
       - 'voltage_rating' 
       - 'temperature_rating' 
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
provide 'overall_confidence'
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
  "overall_confidence": number 0 to 100
}
""".strip()


markings_template = """
{% if markings_status == "unknown" %}
Null
{% else %}
Markings - The product is marked on as follows: {{ markings_summary }}.

The following markings in French are required:
{% endif %}
""".strip()


markings_instruction = """
Fill ONLY the MARKINGS section of a CDR. Use text + images.

Output: ONE JSON object matching markings_json_schema. Return ONLY JSON.

Rules:
- Do NOT copy label text verbatim (no raw part/serial numbers). Summarize generically:
  "Applicant's name", "brand name", "model number", "date of manufacture",
  "electrical ratings", "symbols", "warnings", etc.
- NEVER write the French markings content. Do NOT add any sentence about packaging/illustrations.

filled_text format:
- If you cannot determine markings from evidence: set markings_status="unknown" and filled_text="Null".
- Otherwise filled_text MUST be EXACTLY this 2-line block (with a blank line between):

Line 1: "Markings - The product is marked on as follows: <markings_summary>."
Line 2: (blank line)
Line 3: "The following markings in French are required:"

Also include overall_confidence (0.0 to 100.0) based on evidence quality/coverage.
""".strip()


markings_json_schema = {
  "type": "object",
  "properties": {
    "filled_text": {"type": "string"},
    "markings_status": {"type": "string", "enum": ["present", "none_required", "unknown"]},
    "markings_summary": {"type": "string"},
    "source_used": {"type": "string", "enum": ["text", "images", "both"]},
    "text_evidence": {"type": "array", "items": {"type": "string"}},
    "image_evidence": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "file_name": {"type": "string"},
          "blob_url": {"type": "string"},
          "comment": {"type": "string"}
        },
        "required": ["file_name", "blob_url"]
      }
    },
    "overall_confidence": {"type": "number"}
  },
  "required": [
    "filled_text",
    "markings_status",
    "markings_summary",
    "source_used",
    "text_evidence",
    "image_evidence",
    "overall_confidence"
  ]
}


instructions_template = """
{% if instructions_status == "unknown" %}
'N/A'
{% elif instructions_status == "none_required" %}
Installation, Operating and Safety Instructions - None required.
{% else %}
Installation, Operating and Safety Instructions - Instructions for installation and use of this product are provided by the manufacturer.
{% endif %}
""".strip()

instructions_instruction = """
Fill ONLY the CDR row: INSTALLATION, OPERATING AND SAFETY INSTRUCTIONS.

Return ONE JSON object matching instructions_json_schema. Return ONLY JSON.
Do NOT mention any standard/clause. Use only evidence from text/images.

Set instructions_status:
- "provided" if evidence shows instructions are supplied (manual/leaflet/PDF/etc.)
- "none_required" if evidence clearly indicates none required/supplied
- "unknown" if you cannot determine from evidence

filled_text MUST be:
- provided: "Installation, Operating and Safety Instructions - Instructions for installation and use of this product are provided by the manufacturer."
- none_required: "Installation, Operating and Safety Instructions - None required."
- unknown: "Null"

Also include overall_confidence (0.0 to 100.0) based on evidence quality/coverage.
Populate: source_used (text/images/both), text_evidence[], image_evidence[{file_name, blob_url, comment}], and reason_text.
""".strip()

instructions_json_schema = {
  "type": "object",
  "properties": {
    "filled_text": {"type": "string"},
    "instructions_status": {"type": "string", "enum": ["provided", "none_required", "unknown"]},
    "reason_text": {"type": "string"},
    "source_used": {"type": "string", "enum": ["text", "images", "both"]},
    "text_evidence": {"type": "array", "items": {"type": "string"}},
    "image_evidence": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "file_name": {"type": "string"},
          "blob_url": {"type": "string"},
          "comment": {"type": "string"}
        },
        "required": ["file_name", "blob_url"]
      }
    },
    "overall_confidence": {"type": "number"}
  },
  "required": [
    "filled_text",
    "instructions_status",
    "reason_text",
    "source_used",
    "text_evidence",
    "image_evidence",
    "overall_confidence"
  ]
}
