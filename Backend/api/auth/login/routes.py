from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta, timezone
from .models import EmailRequest, OTPVerifyRequest
from .utils import generate_otp, encrypt_otp, decrypt_otp, send_email
from db.database import COSMOS_DB_users_Container,COSMOS_DB_users_registration
from api.auth.jwt_auth.utils import create_access_token 
import hmac
import logging
from .email_utils import send_welcome_email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from azure.cosmos import CosmosClient
from utility.trf_utils import ensure_cosmos_database
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")  
SMTP_PORT = int(os.getenv("SMTP_PORT", 587)) 
SMTP_USERNAME = os.getenv("SMTP_USERNAME")  
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") 
LOGIN_URL = os.getenv("LOGIN_URL") 


COSMOS_URL = os.getenv("COSMOS_URL")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DB_TEXT     = os.getenv("COSMOS_DB_TEXT")
COSMOS_CONT_TEXT   = os.getenv("COSMOS_CONT_TEXT")
COSMOS_DB_IMAGE   = os.getenv("COSMOS_DB_IMAGE")
COSMOS_CONT_IMAGE   = os.getenv("COSMOS_CONT_IMAGE")
EMBED_DIM = 1536

client = CosmosClient(COSMOS_URL, credential=COSMOS_KEY)

ensure_cosmos_database(client, COSMOS_DB_TEXT)
ensure_cosmos_database(client, COSMOS_DB_IMAGE)

router = APIRouter()

from api.users.models import User
@router.post("/welcome")
async def welcome_application(data: EmailRequest):
    try:
        query = "SELECT * FROM users u WHERE u.email = @email"
        existing_user = list(COSMOS_DB_users_Container.query_items(
            query=query,
            parameters=[{"name": "@email", "value": data.email}],
            enable_cross_partition_query=True
        ))
        if existing_user:
            return {"status": "success", "message": "User has already been created"}
            
        new_user = {
            "id": data.email,
            "email": data.email,
            "is_active": True,
            "user_role": ["Creator","Reviewer"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        
        COSMOS_DB_users_Container.create_item(body=new_user)
        msg = MIMEMultipart()
        msg["From"] = SMTP_USERNAME
        msg["To"] = data.email
        msg["Subject"] = "Welcome! Please login to your account"
        print("---------User has been created inside the cosmos DB -------------")
        await send_welcome_email(data.email,"intertek")
        logging.info(f"Welcome email sent successfully to {data.email}")
        return {"status": "success", "message": "User created and welcome email sent"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in welcome_application: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/request-otp")
async def request_otp(data: EmailRequest):
    try:
        query = "SELECT * FROM users u WHERE u.email = @email" 
        user_query = list(COSMOS_DB_users_Container.query_items(
            query=query,
            parameters=[{"name": "@email", "value": data.email}],
            enable_cross_partition_query=True
        ))

        if not user_query:
            raise HTTPException(status_code=404, detail="Email not registered") 

        user = user_query[0] 

        if not user.get("is_active", False):
            raise HTTPException(status_code=401, detail="User is not active") 

        otp = generate_otp() 
        encrypted_otp = encrypt_otp(otp) 
        expiry_time = datetime.now(timezone.utc) + timedelta(minutes=5) 

        user["otp"] = encrypted_otp 
        user["otp_expiry"] = expiry_time.isoformat() 

        COSMOS_DB_users_Container.replace_item(item=user["id"], body=user) 

        await send_email(user["email"], otp) 

        return {"status": "success", "message": "OTP sent successfully"}

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logging.error(f"Error in request_otp: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/verify-otp")
def verify_otp(data: OTPVerifyRequest):
    try:
        query = """
        SELECT u.otp, u.otp_expiry, u.email, u.user_role, u.is_active
        FROM users u WHERE u.email = @email
        """
        user_data = list(COSMOS_DB_users_Container.query_items(
            query=query,
            parameters=[{"name": "@email", "value": data.email}],
            enable_cross_partition_query=True
        ))

        if not user_data:
            raise HTTPException(status_code=404, detail="Email not registered")
        
        user = user_data[0]
        
        if not user.get("is_active", False):
            raise HTTPException(status_code=401, detail="User is inactive.")

        encrypted_otp = user.get("otp")
        expires_at = datetime.fromisoformat(user["otp_expiry"]).replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=401, detail="OTP expired")

        decrypted_otp = decrypt_otp(encrypted_otp)

        if not hmac.compare_digest(decrypted_otp, data.otp):
            raise HTTPException(status_code=401, detail="Invalid OTP")

        access_token = create_access_token(data={
            "sub": user["email"],
            "role": user.get("user_role", "user")
        })

        return {
            "status": "success",
            "message": "Login successful",
            "access_token": access_token
        }

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logging.error(f"Error verifying OTP: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sso-login")
async def sso_login(data: EmailRequest):
    try:
        
        COSMOS_DB_user_registration_Container = COSMOS_DB_users_registration
        registration_query = "SELECT u.email FROM user_registration u"
        registered_emails = [item["email"] for item in COSMOS_DB_user_registration_Container.query_items(
            query=registration_query,
            enable_cross_partition_query=True
        )]
        print("All registered emails:\n", registered_emails)

        query = "SELECT * FROM users u WHERE u.email = @email"
        existing_user = list(COSMOS_DB_users_Container.query_items(
            query=query,
            parameters=[{"name": "@email", "value": data.email}],
            enable_cross_partition_query=True
        ))

        if not existing_user:
            if data.email in registered_emails:
                user_role = 2
                expiry = timedelta(minutes=5)
                access_token = create_access_token(
                    data={"sub": data.email, "role": user_role},
                    expires_delta=expiry
                )

                new_user = {
                    "id": data.email,
                    "email": data.email,
                    "name": data.name,
                    "user_role": user_role,
                    "accessToken": access_token,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                COSMOS_DB_users_Container.create_item(body=new_user)
                
                return {
                    "status": "success",
                    "message": "Login successful",
                    "access_token": access_token,
                    "role": user_role,
                    "email": data.email,
                    "name": data.name
                }
            else:
                return {
                    "status": "Failed",
                    "message": "Login Failed",
                    "access_token": "NA",
                    "role": None,
                    "email": data.email,
                    "name": data.name
                }
        else:
            user_role = existing_user[0].get("user_role", 2)
            if data.email in registered_emails:
                expiry = timedelta(minutes=5)
                access_token = create_access_token(
                    data={"sub": data.email, "role": user_role},
                    expires_delta=expiry
                )
                return {
                    "status": "success",
                    "message": "Login successful",
                    "access_token": access_token,
                    "role": user_role,
                    "email": data.email,
                    "name": data.name
                }
            else:
                return {
                    "status": "Failed",
                    "message": "Login Failed",
                    "access_token": "NA",
                    "role": user_role,
                    "email": data.email,
                    "name": data.name
                }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in sso_login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

