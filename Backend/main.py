# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from api.users.routes import router as users_router
# from api.auth.login.routes import router as login_router

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],  
#     allow_headers=["*"], 
# )

from fastapi import FastAPI
from api.auth.login.routes import router as login_router

app = FastAPI(title="Intertek")

app.include_router(login_router, prefix="/auth", tags=["Authentication"])
