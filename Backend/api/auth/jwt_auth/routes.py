from fastapi import APIRouter, Depends, HTTPException
from azure.cosmos import exceptions
from db.database import container_2,container_8
from .models import User,UpdateUserStatus
from api.auth.jwt_auth.utils import get_current_user
from datetime import datetime, timezone
import uuid
from fastapi import HTTPException
import os
from dotenv import load_dotenv
from .utils import send_welcome_email
from api.auth.login.models import EmailRequest

router = APIRouter()

load_dotenv()

# LOGIN_URL = os.getenv("app-url") 

@router.post("/add_user")
async def add_user(user: User, current_user: dict = Depends(get_current_user)):
    try:
        # Check if user already exists
        normalized_email = user.email.strip().lower()
        query = "SELECT * FROM c WHERE c.email = @email"
        params = [{"name": "@normalized_email", "value": normalized_email}]
        items = list(container_2.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        ))

        if items:
            raise HTTPException(status_code=400, detail="User with this email already exists")

        # Prepare new user item
        user_item = {
            "id": str(uuid.uuid4()),
            "email": user.email,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "user_role": user.user_role,
            "otp": "",
            "otp_expiry": "",
            "is_terms_accepted": False,
            "terms_accepted_timestamp": "",
            "terms_version": 0,
            "terms_id": "",
            "terms_history_array": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": current_user.get("sub", "system"),
            "updated_at": "",
            "updated_by": ""
        }

        # Add user to DB
        container_2.create_item(body=user_item)

    except exceptions.CosmosHttpResponseError as db_err:
        raise HTTPException(status_code=500, detail="Database error occurred while adding user")

    try:
        # Send welcome email
        # await send_welcome_email(user.email, LOGIN_URL)

    except HTTPException as email_err:
        # Log but do not fail the whole user creation due to email issue
        return {
            "status": "partial_success",
            "message": "User added successfully, but failed to send welcome email"
        }
    return {"status": "success", "message": "User added successfully"}

@router.post("/update_user")
async def update_user(user: User, current_user: dict = Depends(get_current_user)):
    try:
        # Query Cosmos DB for the user by email
        query = f"SELECT * FROM c WHERE c.email = @email"
        users = list(container_2.query_items(
            query=query,
            parameters=[{"name": "@email", "value": user.email}],
            enable_cross_partition_query=True
        ))

        if not users:
            raise HTTPException(status_code=404, detail="User not found")

        user_item = users[0]

        # Update relevant fields
        user_item["user_role"] = user.user_role
        user_item["firstname"] = user.firstname
        user_item["lastname"] = user.lastname
        user_item["phone"] = user.phone

        # Add metadata for tracking updates
        user_item["updated_at"] = datetime.now(timezone.utc).isoformat()
        user_item["updated_by"] = current_user.get("sub", "system")

        # Replace the existing item with the updated one
        container_2.replace_item(item=user_item["id"], body=user_item)
        
        return {"status": "success", "message": "User updated successfully"}

    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code=500, detail="Database error during user update")

    except HTTPException as http_ex:
        raise http_ex  # Pass through explicit HTTP errors

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error during user update")

    
@router.post("/delete_user")
async def update_user_status(user: UpdateUserStatus, current_user: dict = Depends(get_current_user)):
    try:
        # Use parameterized query to safely get user by email
        query = "SELECT * FROM c WHERE c.email = @email"
        users = list(container_2.query_items(
            query=query,
            parameters=[{"name": "@email", "value": user.email}],
            enable_cross_partition_query=True
        ))

        if not users:
            raise HTTPException(status_code=404, detail="User not found")

        user_item = users[0]

        # Update active status
        user_item["is_active"] = user.is_active

        # Add metadata for auditing
        user_item["updated_at"] = datetime.now(timezone.utc).isoformat()
        user_item["updated_by"] = current_user.get("sub", "system")

        # Save the updated user record
        container_2.replace_item(item=user_item["id"], body=user_item)

        return {
            "status": "success",
            "message": f"User status updated",
            "email": user.email
        }

    except exceptions.CosmosHttpResponseError as e:
        raise HTTPException(status_code=500, detail="Database error during status update")

    except HTTPException as http_ex:
        raise http_ex

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error while updating user status")


@router.get("/get_users") 
async def get_users():
    try:
        # Construct query to fetch all users from the database, sorted by creation date in descending order
        query = "SELECT * FROM c ORDER BY c.created_at DESC"
        
        # Execute the query on the container with cross-partition enabled to support distributed data
        items = list(container_2.query_items(query=query, enable_cross_partition_query=True))

        # Return success response with fetched user data (or empty list if none found)
        return {"status": "success", "data": items or []}

    except exceptions.CosmosHttpResponseError as e:
        # Handle and raise database-specific errors with a 500 status code
        raise HTTPException(status_code=500, detail="Error fetching users from database")

    except Exception as e:
        # Handle and raise generic internal errors with a 500 status code
        raise HTTPException(status_code=500, detail="Internal server error while fetching users")
    
@router.get("/get_user/{email}")
async def get_user_by_email(email: str):
    try:
        query = "SELECT * FROM c WHERE c.email = @email"
        parameters = [{"name": "@email", "value": email}]
        
        items = list(container_2.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        if not items:
            return {
                "status": "success",
                "Message": f"No data found for username {email}",
                "Data": []
            }
        return {
            "status": "success",
            "Message": f"All the Data fetched for username {email}",
            "Data": items
        }
    except exceptions.CosmosHttpResponseError:
        raise HTTPException(status_code=500, detail="Error fetching data from database")

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error while fetching data")
