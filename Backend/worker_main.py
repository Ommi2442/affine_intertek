from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor
from projects.trf_processor import process_trf_direct
from projects.letter_processor import process_letter_direct
from typing import Optional


app = FastAPI(title="Worker Service")

EXECUTOR = ThreadPoolExecutor(max_workers=4)

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



# -------------------------
# LETTER JOB
# -------------------------

class LetterJob(BaseModel):
    projectId: str
    trf_urls: Optional[str] = None
    cdr_urls: Optional[str] = None



@app.post("/run-letter", status_code=202)
async def run_letter(job: LetterJob):
    print('**** run_letter *****', job.trf_urls)
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(
            EXECUTOR,
            process_letter_direct,
            job.projectId,
            job.trf_urls,
            job.cdr_urls
        )

        return {
            "projectId": job.projectId,
            "status": "started",
            "worker_port": 9000
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

