"""
test_pipeline_progress_tracker.py

Simple REAL Cosmos DB integration test.

Runs:
TRF pipeline with 4 stages

No assertions.
Only performs live Cosmos DB updates.
"""

import time
from pprint import pprint

from progress_tracker import (
    update_pipeline_progress,
    PipelineType,
)

# ------------------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------------------

PROJECT_ID = "G106231678forCollin"

TRF_STAGES = [
    "download_blob_files",
    "setup_vector_container",
    "generate_trf",
    "upload_outputs",
]

# ------------------------------------------------------------------------------
# TEST
# ------------------------------------------------------------------------------


def run_test():
    print("\n" + "=" * 80)
    print("STARTING REAL COSMOS DB TEST")
    print("=" * 80)

    total_steps = len(TRF_STAGES)

    for index, stage in enumerate(TRF_STAGES, start=1):
        print(f"\n[{index}/{total_steps}] Running stage: {stage}")

        response = update_pipeline_progress(
            project_id=PROJECT_ID,
            stages=TRF_STAGES,
            current_stage=stage,
            pipeline_type=PipelineType.TRF,
            message=f"Executing {stage}",
        )

        pprint(response)

        # small delay so timestamps differ clearly
        time.sleep(1)

    print("\n" + "=" * 80)
    print("COSMOS DB TEST COMPLETED")
    print("=" * 80)


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    run_test()
