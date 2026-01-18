from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor

from projects.trf_processor import process_trf_direct

app = FastAPI(title="TRF Worker")

EXECUTOR = ThreadPoolExecutor(max_workers=2)

class TRFJob(BaseModel):
    projectId: str


@app.post("/run-trf", status_code=202)
async def run_trf(job: TRFJob):
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(
            EXECUTOR,
            process_trf_direct,
            job.projectId
        )

        return {
            "projectId": job.projectId,
            "status": "started",
            "worker_port": 9000
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
