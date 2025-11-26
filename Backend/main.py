from fastapi import FastAPI
from api.auth.login.routes import router as login_router
import os
from projects.routes import router as projects_router

app = FastAPI(title="Intertek")
print("CONN:", repr(os.getenv("AZURE_CONNECTION_STRING")))

app.include_router(login_router, tags=["Authentication"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])