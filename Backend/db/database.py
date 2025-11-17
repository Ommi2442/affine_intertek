from dotenv import load_dotenv
import os
from azure.cosmos import CosmosClient, exceptions

load_dotenv()

OTP_LOGIN_SECRET_KEY = os.getenv("OTP_SECRET_KEY")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
COSMOS_DB_URI = os.getenv("COSMOS_DB_URI")
COSMOS_DB_KEY = os.getenv("COSMOS_DB_KEY")
COSMOS_DB_DATABASE = os.getenv("COSMOS_DB_DATABASE")


COSMOS_DB_TestContainer_NAME = os.getenv("COSMOS_DB_TestContainer")
print("++++++++ ",COSMOS_DB_TestContainer_NAME)
try:
    
    client = CosmosClient(COSMOS_DB_URI, credential=COSMOS_DB_KEY)
    database = client.get_database_client(COSMOS_DB_DATABASE)
    COSMOS_DB_TestContainer = database.get_container_client(COSMOS_DB_TestContainer_NAME)
    
except Exception as e:
    raise Exception(f"Error connecting to Cosmos DB: {e}")
