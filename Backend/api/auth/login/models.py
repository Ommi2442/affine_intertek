from pydantic import BaseModel

class EmailRequest(BaseModel):
    email: str
    name: str
    accessToken: str

class OTPVerifyRequest(BaseModel):
    email: str
    otp: str
