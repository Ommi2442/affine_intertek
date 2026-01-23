from dotenv import load_dotenv
import os
from azure.cosmos import CosmosClient

load_dotenv()

COSMOS_DB_URI = os.getenv("cosmos-db-url")
COSMOS_DB_KEY = os.getenv("cosmos-db-key")
COSMOS_DB_DATABASE = os.getenv("cosmos-db-database")
COSMOS_DB_users_Container = os.getenv("cosmos-db-users-container")
COSMOS_DB_users_registration=os.getenv("cosmos-db-users-registration")
COSMOS_DB_project_Container_name = os.getenv("cosmos-db-project-container")
COSMOS_DB_project_TRF_Container = os.getenv("cosmos-db-project-trf-container")
COSMOS_DB_project_CDR_Container = os.getenv("cosmos-db-project-cdr-container")
COSMOS_DB_project_LETTER_Container = os.getenv("cosmos-db-project-letter-container")

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
    COSMOS_DB_project_LETTER_Container = COSMOS_DB_project_LETTER_Container

    print(" Connected to Cosmos DB successfully.")

except Exception as e:
    raise Exception(f" Error connecting to Cosmos DB: {e}")

