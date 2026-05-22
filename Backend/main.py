from fastapi import FastAPI
from api.auth.login.routes import router as login_router
import os
from projects.routes import router as projects_router
from api.v1.routes import router as v1_router
from api.v1.config import is_mock_mode
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Intertek")

if is_mock_mode():
    print("API v1 MOCK MODE enabled — /v1/* will NOT write to Cosmos DB or blob storage")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login_router, tags=["Authentication"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])
app.include_router(v1_router, prefix="/v1", tags=["API v1"])