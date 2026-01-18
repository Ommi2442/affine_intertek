from dotenv import load_dotenv
import os
from azure.cosmos import CosmosClient

load_dotenv()

COSMOS_DB_URI = os.getenv("COSMOS_DB_URI")
COSMOS_DB_KEY = os.getenv("COSMOS_DB_KEY")
COSMOS_DB_DATABASE = os.getenv("COSMOS_DB_DATABASE")
COSMOS_DB_users_Container = os.getenv("COSMOS_DB_users_Container")
COSMOS_DB_users_registration=os.getenv("COSMOS_DB_users_registration")
COSMOS_DB_project_Container_name = os.getenv("COSMOS_DB_project_Container")
COSMOS_DB_project_TRF_Container = os.getenv("COSMOS_DB_project_TRF_Container")
COSMOS_DB_project_CDR_Container = os.getenv("COSMOS_DB_project_CDR_Container")
COSMOS_DB_project_LETTER_Container = os.getenv("COSMOS_DB_project_Letter_Container")

try:
    print(" Connecting to Cosmos DB...")
    client = CosmosClient(COSMOS_DB_URI, COSMOS_DB_KEY)
    database = client.get_database_client(COSMOS_DB_DATABASE)
    users_container = database.get_container_client(COSMOS_DB_users_Container)
    users_reg = database.get_container_client(COSMOS_DB_users_registration)
    projects_container = database.get_container_client(COSMOS_DB_project_Container_name)
    COSMOS_DB_project_TRF_Container = database.get_container_client(COSMOS_DB_project_TRF_Container)
    COSMOS_DB_project_CDR_Container = database.get_container_client(COSMOS_DB_project_CDR_Container)
    COSMOS_DB_project_LETTER_Container = database.get_container_client(COSMOS_DB_project_LETTER_Container)
    COSMOS_DB_users_Container = users_container
    COSMOS_DB_users_registration=users_reg
    COSMOS_DB_project_Container = projects_container
    COSMOS_DB_project_trf_Container = COSMOS_DB_project_TRF_Container
    COSMOS_DB_project_cdr_Container = COSMOS_DB_project_CDR_Container
    print(" Connected to Cosmos DB successfully.")

except Exception as e:
    raise Exception(f" Error connecting to Cosmos DB: {e}")

