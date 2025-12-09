# import logging
# import random
# import string
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from fastapi import HTTPException
# import os
# from dotenv import load_dotenv
# from cryptography.fernet import Fernet

# load_dotenv()

# # SMTP Configuration
# SMTP_SERVER = os.getenv("SMTP_SERVER")  
# SMTP_PORT = int(os.getenv("SMTP_PORT", 587)) 
# SMTP_USERNAME = os.getenv("SMTP_USERNAME")  
# SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") 

# # OTP Encryption Configuration
# OTP_LOGIN_SECRET_KEY = os.getenv("OTP_SECRET_KEY")  
# cipher = Fernet(OTP_LOGIN_SECRET_KEY.encode())

# def generate_otp():
    
#     #Generates a 6-digit OTP (One Time Password) using random digits.
#     return ''.join(random.choices(string.digits, k=6))  # Randomly selects 6 digits from the string of digits

# def encrypt_otp(otp: str) -> str:

#     #Encrypts the OTP string using the Fernet encryption method.
#     try:
#        return cipher.encrypt(otp.encode()).decode()
#     except Exception as e:
#         logging.error(f"OTP encryption failed: {str(e)}") 
#         raise HTTPException(status_code=500, detail="OTP encryption error")

# def decrypt_otp(encrypted_otp: str) -> str:

#     # Decrypts the encrypted OTP back into its original value.
#     try:
#        return cipher.decrypt(encrypted_otp.encode()).decode()
#     except Exception as e:
#         logging.error(f"OTP decryption failed: {str(e)}") 
#         raise HTTPException(status_code=500, detail="OTP decryption error")

# async def send_email(recipient: str, otp: str):
    
#     #Sends an email with the OTP code to the specified recipient using SMTP.
#     try:
#         # Create a MIME Multipart message object
#         msg = MIMEMultipart()
#         msg["From"] = SMTP_USERNAME  # Sender's email
#         msg["To"] = recipient  # Recipient's email
#         msg["Subject"] = "Your OTP Code"  # Email subject

#         # HTML body with OTP included in a bold format
#         body = f"""
# <html>
#     <head>
#         <style>
#             body {{
#                 font-family: Arial, sans-serif;
#                 color: #333333;
#                 background-color: #f9f9f9;
#                 margin: 0;
#                 padding: 20px;
#             }}
#             .container {{
#                 max-width: 600px;
#                 margin: 0 auto;
#                 background-color: #ffffff;
#                 padding: 20px;
#                 border-radius: 8px;
#                 box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
#             }}
#             .header {{
#                 background-color: #00386E ;
#                 color: white;
#                 padding: 10px 0;
#                 text-align: center;
#                 border-radius: 8px 8px 0 0;
#             }}
#             .otp {{
#                 font-size: 36px;
#                 font-weight: bold;
#                 color: #00386E ;
#                 text-align: center;
#                 padding: 20px 0;
#             }}
#             .footer {{
#                 margin-top: 20px;
#                 font-size: 12px;
#                 color: #888888;
#                 text-align: center;
#             }}
#             .button {{
#                 background-color: #00386E ;
#                 color: white;
#                 padding: 10px 20px;
#                 text-align: center;
#                 text-decoration: none;
#                 border-radius: 5px;
#                 display: inline-block;
#                 margin-top: 20px;
#             }}
#         </style>
#     </head>
#     <body>
#         <div class="container">
#             <div class="header">
#                 <h2>Your OTP Code</h2>
#             </div>
#             <p>Dear User,</p>
#             <p>We received a request to verify your email address. Please use the following OTP to complete the process:</p>
#             <div class="otp">{otp}</div>
#             <p>The OTP will expire in 5 minutes.</p>
#             <p>If you did not request this, please ignore this message.</p>
#             <div class="footer">
#                 <p>Thank you for using our service!</p>
#             </div>
#         </div>
#     </body>
# </html>
# """
#         msg.attach(MIMEText(body, "html"))  # Attach the HTML body to the email message

#         # Set up the SMTP server and send the email
#         server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
#         server.starttls()  
#         server.login(SMTP_USERNAME, SMTP_PASSWORD)  
#         server.sendmail(SMTP_USERNAME, recipient, msg.as_string())  
#         server.quit()  

#         logging.info(f"OTP email sent successfully to {recipient}") 

#     except smtplib.SMTPException as smtp_err:
#         logging.error(f"SMTP error while sending email: {smtp_err}")  
#         raise HTTPException(status_code=500, detail="Failed to send OTP email")

#     except Exception as e:
#         logging.error(f"Unexpected error in send_email: {str(e)}") 
#         raise HTTPException(status_code=500, detail="Error sending OTP email")

import random
from cryptography.fernet import Fernet
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# You can store this securely
SECRET_KEY = os.getenv("SECRET_KEY")
cipher = Fernet(Fernet.generate_key())

def generate_otp() -> str:
    """Generate a random 6-digit OTP."""
    return str(random.randint(100000, 999999))

def encrypt_otp(otp: str) -> str:
    """Encrypt OTP before storing."""
    return cipher.encrypt(otp.encode()).decode()

def decrypt_otp(encrypted_otp: str) -> str:
    """Decrypt OTP."""
    return cipher.decrypt(encrypted_otp.encode()).decode()

async def send_email(recipient: str, otp: str):
    """Send OTP email."""
    subject = "Your OTP Code"
    body = f"Your OTP code is: {otp}\nThis code will expire in 5 minutes."

    msg = MIMEText(body)
    msg["From"] = SMTP_USERNAME
    msg["To"] = recipient
    msg["Subject"] = subject

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        print(f" OTP email sent to {recipient}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        raise
