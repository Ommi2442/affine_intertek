from pydantic import BaseModel
from typing import Optional,List 

class User(BaseModel):
    email: str
    user_role: int
    firstname: str
    lastname: str

class UpdateUserStatus(BaseModel):
    email: str
    is_active: int 
    user_role:int
