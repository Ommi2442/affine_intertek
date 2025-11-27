# import os
# from jose import jwt
# from datetime import datetime, timedelta,timezone
# from fastapi import Depends, HTTPException
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from jose import jwt, JWTError
# from dotenv import load_dotenv

# load_dotenv()

# # Auth dependency
# security = HTTPBearer()

# # Load secrets and constants
# SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
# ALGORITHM = os.getenv("ALGORITHM", "HS256")
# ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 120))

# # Create access token
# def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
#     to_encode = data.copy()
#     expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# # Dependency for protected routes
# def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
#     token = credentials.credentials
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) 
#         return payload
#     except JWTError as e:
#        raise HTTPException(status_code=401, detail="Invalid or expired token")

from datetime import datetime, timedelta, timezone
from jose import jwt
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Generate JWT access token with optional custom expiration."""
    
    to_encode = data.copy()

    # If custom expiry passed, use it. Otherwise use default.
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
