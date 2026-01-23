from fastapi import APIRouter, HTTPException
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException
import os
from dotenv import load_dotenv

router = APIRouter()

load_dotenv()

# SMTP Configuration
# SMTP_SERVER = os.getenv("SMTP_SERVER")  
# SMTP_PORT = int(os.getenv("SMTP_PORT", 587)) 
# SMTP_USERNAME = os.getenv("SMTP_USERNAME")  
# SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") 
# LOGIN_URL = os.getenv("LOGIN_URL") 


# async def send_welcome_email(recipient: str, login_url: str):
#     try:
#         msg = MIMEMultipart()
#         msg["From"] = SMTP_USERNAME
#         msg["To"] = recipient
#         msg["Subject"] = "Welcome! Please login to your account"

#         body = f"""
# <html>
#     <head>
#         <style>
#             body {{
#                 font-family: Arial, sans-serif;
#                 color: #333;
#                 background-color: #f4f4f4;
#                 padding: 20px;
#             }}
#             .container {{
#                 max-width: 600px;
#                 background-color: #fff;
#                 padding: 30px;
#                 margin: auto;
#                 border-radius: 10px;
#                 box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
#             }}
#             .header {{
#                 background-color: #00386E;
#                 color: white;
#                 padding: 15px;
#                 text-align: center;
#                 border-radius: 10px 10px 0 0;
#             }}
#             .content {{
#                 text-align: center;
#                 padding: 20px;
#             }}
#             .button {{
#                 display: inline-block;
#                 padding: 10px 20px;
#                 margin-top: 20px;
#                 background-color: #00386E;
#                 color: white;
#                 text-decoration: none;
#                 border-radius: 5px;
#                 font-weight: bold;
#             }}
#             .footer {{
#                 text-align: center;
#                 font-size: 12px;
#                 color: #999;
#                 margin-top: 30px;
#             }}
#         </style>
#     </head>
#     <body>
#         <div class="container">
#             <div class="header">
#                 <h2>Welcome to Our Platform!</h2>
#             </div>
#             <div class="content">
#                 <p>Hello,</p>
#                 <p>Your account has been successfully created.</p>
#                 <p>Please click the button below to log in to your account:</p>
#                 <a href="{login_url}" class="button">Login Now</a>
#             </div>
#             <div class="footer">
#                 <p>If you have any questions, please contact support.</p>
#             </div>
#         </div>
#     </body>
# </html>
# """
#         msg.attach(MIMEText(body, "html"))

#         server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
#         server.starttls()
#         server.login(SMTP_USERNAME, SMTP_PASSWORD)
#         server.sendmail(SMTP_USERNAME, recipient, msg.as_string())
#         server.quit()

#         logging.info(f"Welcome email sent successfully to {recipient}")

#     except smtplib.SMTPException as smtp_err:
#         logging.error(f"SMTP error while sending welcome email: {smtp_err}")
#         raise HTTPException(status_code=500, detail="Failed to send welcome email")

#     except Exception as e:
#         logging.error(f"Unexpected error in send_welcome_email: {str(e)}")
#         raise HTTPException(status_code=500, detail="Error sending welcome email")