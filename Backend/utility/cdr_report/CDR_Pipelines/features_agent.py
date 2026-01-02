from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

# Your existing pipeline entrypoint
from utility.cdr_report.CDR_Pipelines.features import features_main, rag_multimodal_retrieve


import json
import copy
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
import os, threading


def build_tools(vs, image_urls: List[str]):
    """
    Creates "bound" tools via closure so we DON'T pass non-JSON objects (vs) as tool args.
    These tools are safe: they won't mutate pipeline outputs.
    """

    @tool("planner_agent", description="Returns a deterministic plan for running the features pipeline.")
    def planner_agent_tool() -> str:
        plan = [
            "1) Run existing features_main(vs, image_urls) exactly once",
            "2) (Optional) Run audit tools that DO NOT affect output: citations, validation",
            "3) Return the features_main output unchanged",
        ]
        return json.dumps({"plan": plan}, ensure_ascii=False)

    @tool("retriever_agent", description="Runs rag_multimodal_retrieve for inspection only (does not feed generation).")
    def retriever_agent_tool(section_name: str, custom_queries: Optional[List[str]] = None, k: int = 12) -> str:
        ev = rag_multimodal_retrieve(
            section_name=section_name,
            custom_queries=custom_queries or [],
            vs=vs,
            image_urls=image_urls,
            k=k,
        )
        # Return a small preview only (avoid huge context_text)
        preview = {
            "section_name": section_name,
            "num_text_chunks": len(ev.get("text_chunks", [])),
            "text_chunk_sources": [
                {"filename": x.get("filename"), "page": x.get("page"), "score": x.get("similarity_score")}
                for x in (ev.get("text_chunks") or [])[:5]
            ],
            "num_images": len(ev.get("image_urls", [])),
            "image_candidates": ev.get("image_candidates", [])[:10],
        }
        return json.dumps(preview, ensure_ascii=False)

#     @tool("citation_agent", description="Builds citations from evidence+final output without modifying final output.")
    @tool("citation_agent", description="Builds citations if text_support exists; otherwise returns empty for that key.")
    def citation_agent_tool(final_sections_json: Any) -> str:
        citations = {}
        warnings = []

        # If the whole thing isn't a dict, we can't iterate keys
        if not isinstance(final_sections_json, dict):
            return json.dumps(
                {"citations": {}, "warnings": ["Input is not a dict; cannot extract citations."]},
                ensure_ascii=False
            )

        for section_key, sec in final_sections_json.items():
            # Only sections that are dicts can have text_support
            if isinstance(sec, dict):
                chunks = sec.get("text_support") or []
                if isinstance(chunks, list):
                    citations[section_key] = [
                        {
                            "filename": c.get("filename"),
                            "page": c.get("page"),
                            "similarity_score": c.get("similarity_score"),
                        }
                        for c in chunks
                        if isinstance(c, dict)
                    ]
                else:
                    citations[section_key] = []
                    warnings.append(f"{section_key}: text_support is not a list.")
            else:
                # It's a list/string/int/etc (normal in filled payload)
                citations[section_key] = []
                # keep warnings minimal (optional)
                # warnings.append(f"{section_key}: section value is {type(sec).__name__}, no text_support.")

        return json.dumps({"citations": citations, "warnings": warnings}, ensure_ascii=False)

    @tool("generator_evaluator_agent", description="Validates final output shape/policy and returns warnings only.")
    def generator_evaluator_agent_tool(final_sections_json: Dict[str, Any]) -> str:
        warnings: List[str] = []

        if not isinstance(final_sections_json, dict):
            warnings.append("final_sections_json is not a dict.")
            return json.dumps({"warnings": warnings}, ensure_ascii=False)

        # Example checks (non-destructive):
        # - missing filled_text
        # - markings policy quick check
        for key, sec in final_sections_json.items():
            if not isinstance(sec, dict):
                warnings.append(f"{key}: section is not an object.")
                continue

            if "filled_text" not in sec:
                warnings.append(f"{key}: missing filled_text.")

            if key == "markings":
                # Your pipeline sets filled_text="Null" if markings_status unknown
                ft = (sec.get("filled_text") or "")
                if ft == "" or ft is None:
                    warnings.append("markings: filled_text empty (unexpected).")

        return json.dumps({"warnings": warnings}, ensure_ascii=False)


    @tool("pid_check", description="Debug tool to print PID/TID.")
    def pid_check_tool() -> str:
        return f"PID={os.getpid()} TID={threading.get_ident()}"
    
    @tool("compiler_agent", return_direct=True, description="Runs the existing features_main(vs, image_urls) pipeline and returns JSON.")
    def compiler_agent_tool() -> str:
        out = features_main(vs, image_urls)  # ✅ EXACT same call
        return json.dumps(out, ensure_ascii=False)

    return {
        "planner_agent_tool": planner_agent_tool,
        "retriever_agent_tool": retriever_agent_tool,
        "citation_agent_tool": citation_agent_tool,
        "generator_evaluator_agent_tool": generator_evaluator_agent_tool,
        "pid_check_tool": pid_check_tool,
        "compiler_agent_tool": compiler_agent_tool,
    }


def features_tools_main(
    vs,
    image_urls: List[str],
    *,
    run_audit: bool = True,
    audit_path: str = "features_audit.json",
) -> Dict[str, Any]:
    """
    Guaranteed output stability:
    - returns EXACT dict from features_main(vs, image_urls)
    - audit results are saved separately and never fed back
    """
    tools = build_tools(vs, image_urls)
    
    import os, threading
    print("MAIN:", os.getpid(), threading.get_ident())

    print("TOOL:", tools["pid_check_tool"].invoke({}))

    # 1) Run compiler tool (same output as features_main)
    features_out_text = tools["compiler_agent_tool"].invoke({})
#     features_out = features_out_text if isinstance(features_out_text, dict) else json.loads(features_out_text)
    features_out = json.loads(features_out_text)

    if not run_audit:
        return features_out

    # 2) Run post-hoc tools on a COPY (never mutate original)
    safe_copy = copy.deepcopy(features_out)
    citations_text = tools["citation_agent_tool"].invoke({"final_sections_json": safe_copy})
    eval_text = tools["generator_evaluator_agent_tool"].invoke({"final_sections_json": safe_copy})

    audit = {
        "planner": json.loads(tools["planner_agent_tool"].invoke({})),
        "citations": json.loads(citations_text),
        "evaluator": json.loads(eval_text),
    }

    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)

    # 3) Return unchanged pipeline output
    return features_out
