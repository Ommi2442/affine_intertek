from utility.cdr_report.CDR_Pipelines.switch import find_bom_blob_url
import utility.cdr_report.CDR_Pipelines.components_case_1 as case_1
import utility.cdr_report.CDR_Pipelines.components_case_2 as case_2

def run_sheet_3_and_4_main(*, vs):
    """
    Authoritative decision + execution wrapper.
    Exactly one pipeline runs.
    """
    bom_files = find_bom_blob_url(vs=vs)

    if bom_files:
        case_1.run_case1_pipeline(vs=vs)
        return {
            "case": "c1",
            "pipeline": "case1",
            "bom_files": bom_files,
        }
    else:
        case_2.run_case2_pipeline()
        return {
            "case": "c2",
            "pipeline": "case2",
            "bom_files": [],
        }


from langchain_core.tools import tool
import json, copy

def build_sheet34_tools(*, vs):
    """
    Build agent tools with vector store captured in closure.
    """

    @tool(
        "planner_agent",
        description="Deterministic execution plan for Sheet 3 & 4 pipeline."
    )
    def planner_agent():
        return json.dumps({
            "plan": [
                "Detect BOM files",
                "Run exactly one pipeline (c1 OR c2)",
                "Never mix pipelines",
                "Do not mutate outputs",
            ]
        })

    @tool(
        "compiler_agent",
        return_direct=True,
        description="Runs the authoritative Sheet 3 & 4 pipeline."
    )
    def compiler_agent():
        out = run_sheet_3_and_4_main(vs=vs)
        return json.dumps(out)

    @tool(
        "audit_agent",
        description="Post-run validation only (non-mutating)."
    )
    def audit_agent(run_metadata: dict):
        warnings = []

        if run_metadata.get("case") not in ("c1", "c2"):
            warnings.append("Unknown execution case.")

        if run_metadata.get("case") == "c1" and not run_metadata.get("bom_files"):
            warnings.append("c1 selected but no BOM files found.")

        return json.dumps({"warnings": warnings})

    return {
        "planner_agent": planner_agent,
        "compiler_agent": compiler_agent,
        "audit_agent": audit_agent,
    }


def run_sheet_3_and_4_agentic(
    *,
    vs,
    run_audit: bool = True,
    audit_path: str = "sheet34_audit.json",
):
    """
    Agentic wrapper. VS must be provided by caller (main.py).
    """
    if vs is None:
        raise RuntimeError("Vector store (vs) must be provided")

    tools = build_sheet34_tools(vs=vs)

    # 1) Run authoritative pipeline
    run_meta = json.loads(
        tools["compiler_agent"].invoke({})
    )

    if not run_audit:
        return run_meta

    # 2) Audit on COPY
    safe_copy = copy.deepcopy(run_meta)

    audit = {
        "plan": json.loads(tools["planner_agent"].invoke({})),
        "audit": json.loads(
            tools["audit_agent"].invoke({"run_metadata": safe_copy})
        ),
    }

    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)

    return run_meta
